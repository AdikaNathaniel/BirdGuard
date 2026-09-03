import time
import json
import socket
import os
import signal
import subprocess
import threading
import cv2
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from picamera2 import Picamera2
from ultralytics import YOLO
from pymongo import MongoClient
from adafruit_servokit import ServoKit

# Python only auto-converts SIGINT (Ctrl+C) into a catchable KeyboardInterrupt
# -- SIGTERM (what `pkill`/the backend's STOP_DETECTOR command sends) kills
# the process immediately by default, skipping every try/finally cleanup
# below. Route it through the same KeyboardInterrupt path so the laser
# always gets switched off and the servos always get re-centered/released
# on stop, not just on Ctrl+C.
def _handle_sigterm(signum, frame):
    raise KeyboardInterrupt


signal.signal(signal.SIGTERM, _handle_sigterm)

# --- CONFIG ---
# Same base tunables as the non-tracking detector variant -- see
# pi_person_detector_cpu.py for the rationale behind each of these.
LASER_GPIO = 12               # Pi GPIO12 -> Nano D2 -> Nano D6 -> laser
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
TARGET_CLASS = "person"
CONFIDENCE_THRESHOLD = 0.5
LASER_OFF_DELAY = 3.0         # Seconds to keep laser on after last detection
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
VIDEO_FPS = 30
PREVIEW_PORT = 8080           # browse http://<pi-ip>:8080/ for a live MJPEG preview

# --- PAN/TILT TRACKING (PCA9685 over I2C) ---
# Same board/channels as pi-driver-motor/pi_driver_motor.py -- pan on
# channel 0, tilt on channel 4.
PAN_CHANNEL = 0
TILT_CHANNEL = 4
SERVO_CENTER_ANGLE = 90
SERVO_MIN_ANGLE = 60          # conservative safe range, same convention used
SERVO_MAX_ANGLE = 120         # elsewhere in this codebase (pi_servo.py, pi_driver_motor.py)
TRACK_DEAD_ZONE_PX = 40       # no correction while the person's center is within
                               # this many pixels of frame center -- prevents
                               # constant jitter from frame-to-frame bbox noise
TRACK_NUDGE_DEGREES = 2       # degrees moved per correction step -- small and
                               # frequent beats large and jerky

# Same Atlas cluster/database the NestJS backend uses -- the Pi writes
# detection events directly, the backend's detection-service only reads.
# Standard (non-SRV) connection string -- the mongodb+srv:// form needs a
# DNS TXT record lookup that this network's DNS doesn't handle correctly
# (SRV lookups work fine, TXT lookups time out even against 8.8.8.8),
# so the host list is spelled out explicitly to avoid that lookup entirely.
MONGODB_URI = os.environ.get(
    "MONGODB_URI",
    "mongodb://adikanathaniel4_db_user:oLAjlIr1kRY31LZQ@"
    "ac-w0spglj-shard-00-00.u4du6ig.mongodb.net:27017,"
    "ac-w0spglj-shard-00-01.u4du6ig.mongodb.net:27017,"
    "ac-w0spglj-shard-00-02.u4du6ig.mongodb.net:27017/"
    "birdguard?ssl=true&replicaSet=atlas-8gkcz2-shard-0&authSource=admin&appName=Cluster0",
)

# Session folder -- every run gets its own timestamped directory so
# recordings/snapshots from different runs never overwrite each other.
session_name = datetime.now().strftime("session_%Y-%m-%d_%H-%M-%S")
SESSION_DIR = f"/home/pi/birdguard-test/{session_name}"
DETECTIONS_DIR = f"{SESSION_DIR}/detections"
VIDEO_PATH = f"{SESSION_DIR}/recording.avi"
os.makedirs(DETECTIONS_DIR, exist_ok=True)


def set_laser_gpio(high: bool):
    # Drives GPIO12 via the `pinctrl` CLI tool rather than a Python GPIO
    # library -- this signal is read by the Arduino Nano (D2), not used
    # to power the laser directly from the Pi.
    state = "dh" if high else "dl"
    try:
        subprocess.run(["pinctrl", "set", str(LASER_GPIO), "op", state], check=True)
    except Exception as e:
        print(f"pinctrl call failed: {e}")


# --- PAN/TILT TRACKING ---
# `pan_angle`/`tilt_angle` track the last angle *commanded* to each servo
# -- the PCA9685 gives no position feedback, so this is the only record
# of "where the servo currently is" the script has, and every future
# nudge is computed relative to it.
kit = ServoKit(channels=16)
pan_angle = SERVO_CENTER_ANGLE
tilt_angle = SERVO_CENTER_ANGLE


def center_servos():
    global pan_angle, tilt_angle
    pan_angle = SERVO_CENTER_ANGLE
    tilt_angle = SERVO_CENTER_ANGLE
    kit.servo[PAN_CHANNEL].angle = pan_angle
    kit.servo[TILT_CHANNEL].angle = tilt_angle


def track_person(bbox):
    """Nudge pan/tilt toward centering the given (x1, y1, x2, y2) bbox in
    frame. Stays put once the person's center is within TRACK_DEAD_ZONE_PX
    of the frame's center -- that's the "stop" condition: no further motor
    commands are sent once centered, so the servo just holds its last
    position rather than hunting for an exact pixel match."""
    global pan_angle, tilt_angle
    x1, y1, x2, y2 = bbox
    person_cx = (x1 + x2) / 2
    person_cy = (y1 + y2) / 2
    frame_cx = FRAME_WIDTH / 2
    frame_cy = FRAME_HEIGHT / 2

    # Positive error_x = person is right of frame-center; positive
    # error_y = person is below frame-center (image y grows downward).
    error_x = person_cx - frame_cx
    error_y = person_cy - frame_cy

    print(f"    [track] bbox center=({person_cx:.0f},{person_cy:.0f}) "
          f"frame center=({frame_cx:.0f},{frame_cy:.0f}) "
          f"error=({error_x:.0f},{error_y:.0f})")

    # Sign convention below is a starting guess -- flip the +/- if the
    # servo visibly moves away from the person instead of toward them on
    # your specific mounting.
    if abs(error_x) > TRACK_DEAD_ZONE_PX:
        pan_angle += -TRACK_NUDGE_DEGREES if error_x > 0 else TRACK_NUDGE_DEGREES
        pan_angle = max(SERVO_MIN_ANGLE, min(SERVO_MAX_ANGLE, pan_angle))
        print(f"    [track] -> PAN command: angle={pan_angle}")
        kit.servo[PAN_CHANNEL].angle = pan_angle
    else:
        print(f"    [track] pan within dead zone, holding at {pan_angle}")

    if abs(error_y) > TRACK_DEAD_ZONE_PX:
        tilt_angle += -TRACK_NUDGE_DEGREES if error_y > 0 else TRACK_NUDGE_DEGREES
        tilt_angle = max(SERVO_MIN_ANGLE, min(SERVO_MAX_ANGLE, tilt_angle))
        print(f"    [track] -> TILT command: angle={tilt_angle}")
        kit.servo[TILT_CHANNEL].angle = tilt_angle
    else:
        print(f"    [track] tilt within dead zone, holding at {tilt_angle}")


# --- DETECTION LOGGING (writes directly to MongoDB; the backend's
# detection-service only ever reads this collection, never writes to it) ---
# Connection is attempted once at import time. If it fails (e.g. no
# internet), the script keeps running with logging silently disabled
# rather than crashing the whole detector over a non-essential feature.
try:
    _mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    _detections_collection = _mongo_client["birdguard"]["detections"]
except Exception as e:
    print(f"MongoDB connection failed (detection logging disabled): {e}")
    _detections_collection = None


def log_detection_event(label, confidence, bbox=None):
    # No-ops if the Mongo connection failed at startup -- logging is
    # best-effort and must never be the reason detection itself breaks.
    if _detections_collection is None:
        return
    try:
        doc = {
            "label": label,
            "confidence": confidence,
            "detectedAt": datetime.now(timezone.utc),
        }
        if bbox:
            doc["bbox"] = bbox
        _detections_collection.insert_one(doc)
    except Exception as e:
        print(f"Failed to log detection to MongoDB: {e}")


# --- MJPEG PREVIEW (no VNC/X server needed -- view at http://<pi-ip>:PORT/ in any browser) ---
# A tiny built-in HTTP server that streams whatever the main loop most
# recently wrote into `latest_frame` as a multipart JPEG stream -- the
# standard "motion JPEG" format most browsers can render natively as a
# live video feed with an <img> tag, no plugins or special player needed.
latest_frame = None
latest_frame_lock = threading.Lock()


class _MJPEGHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Every GET request becomes a long-lived stream: send the MJPEG
        # multipart header once, then keep pushing whatever `latest_frame`
        # currently holds until the client disconnects.
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()
        try:
            while True:
                with latest_frame_lock:
                    frame = latest_frame
                if frame is None:
                    time.sleep(0.05)
                    continue
                ok, jpg = cv2.imencode(".jpg", frame)
                if not ok:
                    continue
                self.wfile.write(b"--frame\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                self.wfile.write(jpg.tobytes())
                self.wfile.write(b"\r\n")
                time.sleep(0.05)
        except (BrokenPipeError, ConnectionResetError):
            # Normal when a viewer closes the browser tab / app -- not an
            # actual error, just the stream ending.
            pass

    def log_message(self, format, *args):
        pass  # silence per-request access logging


def start_preview_server(port=PREVIEW_PORT):
    # Runs on its own daemon thread so the HTTP server can serve viewers
    # concurrently with the main detection loop, without blocking it.
    server = ThreadingHTTPServer(("0.0.0.0", port), _MJPEGHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def get_lan_ip():
    # Raspberry Pi OS maps the hostname to 127.0.1.1 in /etc/hosts, so
    # socket.gethostbyname(socket.gethostname()) returns a loopback address
    # instead of the real LAN IP. Opening a UDP "connection" (no packets
    # actually sent) forces the OS to pick the real outbound interface.
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main():
    global latest_frame
    print(f"Session: {SESSION_DIR}")
    print(f"Target: {TARGET_CLASS.upper()} | Confidence: {CONFIDENCE_THRESHOLD}")
    print(f"Video: {VIDEO_PATH}")
    print(f"Laser trigger: GPIO{LASER_GPIO} -> Nano D2 -> Nano D6 -> laser")
    print(f"Pan/tilt tracking: PCA9685 channel {PAN_CHANNEL} (pan) / {TILT_CHANNEL} (tilt)")

    set_laser_gpio(False)  # laser OFF at startup
    center_servos()

    # UDP socket for broadcasting each detection's bounding box to any
    # local listener -- fire and forget, no listener needs to be present.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Load YOLOv8 -- the "n" (nano) variant, chosen for CPU inference
    # speed on the Pi rather than accuracy, since there's no GPU/NPU here.
    print("Loading YOLOv8 (n)...")
    model = YOLO("yolov8n.pt")
    print("Model loaded.")

    # Init camera at the configured resolution/frame-rate window via
    # picamera2 (libcamera) -- RGB888 is what OpenCV/YOLO expect.
    picam2 = Picamera2()
    config = picam2.create_video_configuration(
        main={"size": (FRAME_WIDTH, FRAME_HEIGHT), "format": "RGB888"},
        controls={"FrameDurationLimits": (33333, 66666)}
    )
    picam2.configure(config)
    picam2.start()
    picam2.set_controls({"AwbEnable": True, "Saturation": 1.5, "Brightness": 0.2})
    time.sleep(2)  # let auto-exposure/auto-white-balance settle before recording starts

    # Init video writer — records continuously from the start, not just
    # during detections, so the full session is available for review.
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    writer = cv2.VideoWriter(VIDEO_PATH, fourcc, VIDEO_FPS, (FRAME_WIDTH, FRAME_HEIGHT))
    print(f"Recording started -> {VIDEO_PATH}")

    start_preview_server()
    pi_ip = get_lan_ip()
    print(f"Live preview: http://{pi_ip}:{PREVIEW_PORT}/  (no VNC/X server needed). Use Ctrl+C to stop.")

    laser_on = False
    last_detection_time = 0
    frame_count = 0
    detection_count = 0
    last_write_time = time.time()

    print(f"\nWatching for {TARGET_CLASS.upper()}... (Ctrl+C to stop)\n")

    try:
        while True:
            # --- CAPTURE + INFERENCE ---
            frame = picam2.capture_array()
            bgr = frame

            results = model.predict(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)[0]
            target_found = False
            detections = []

            # Walk every detected box this frame and keep only the ones
            # matching TARGET_CLASS ("person").
            for box in results.boxes:
                class_id = int(box.cls[0])
                label = model.names[class_id]

                if label == TARGET_CLASS:
                    target_found = True
                    last_detection_time = time.time()

                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    conf = float(box.conf[0])
                    detections.append((x1, y1, x2, y2, label, conf))

                    # Debug visibility into the exact numbers driving the
                    # tracking decision below -- printed per-detection so
                    # the raw pixel offset can be sanity-checked against
                    # what the servo actually does.
                    offset_x = ((x1 + x2) / 2) - (FRAME_WIDTH / 2)
                    offset_y = ((y1 + y2) / 2) - (FRAME_HEIGHT / 2)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] DETECTED: {label.upper()} | "
                          f"conf: {conf:.2f} | center=({(x1 + x2) / 2:.0f},{(y1 + y2) / 2:.0f}) | "
                          f"offset=({offset_x:.0f},{offset_y:.0f})")

                    # Broadcast this detection's box over UDP -- fire and
                    # forget, for any downstream process that wants it.
                    payload = {
                        "timestamp": time.time(),
                        "label": label,
                        "confidence": conf,
                        "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
                    }
                    sock.sendto(json.dumps(payload).encode(), (UDP_IP, UDP_PORT))

            # Highest-confidence detection this frame, reused below for both
            # tracking (every frame) and laser/logging (rising edge only).
            top = max(detections, key=lambda d: d[5]) if detections else None

            # --- PAN/TILT TRACKING (every frame a person is visible) ---
            # Runs on every frame the person is in view, independent of
            # the laser's edge-triggered logic below -- tracking should
            # keep following them the whole time they're visible, not
            # just at the moment they first appear.
            if top is not None:
                track_person(top[:4])

            # --- LASER CONTROL (Pi GPIO12 -> Nano D2 -> Nano D6 -> laser) ---
            # Edge-triggered: laser turns on once when a person first
            # appears, off only after LASER_OFF_DELAY seconds with no
            # detection (debounced against brief per-frame misses).
            if target_found and not laser_on:
                set_laser_gpio(True)
                laser_on = True
                print(">>> LASER ON")

                # Log this as one detection event (not per-frame) -- use
                # the highest-confidence detection in this frame.
                x1, y1, x2, y2, top_label, top_conf = top
                log_detection_event(top_label, top_conf, {"x1": x1, "y1": y1, "x2": x2, "y2": y2})

            elif not target_found and laser_on:
                if time.time() - last_detection_time > LASER_OFF_DELAY:
                    set_laser_gpio(False)
                    laser_on = False
                    print(">>> LASER OFF")

            # --- VIDEO RECORDING ---
            # Every frame gets written to the session's video file
            # regardless of detections; frames with a person also get a
            # drawn bounding box + label and a separate annotated snapshot
            # saved to disk for quick review without scrubbing the video.
            video_frame = bgr.copy()
            if detections:
                for x1, y1, x2, y2, label, conf in detections:
                    cv2.rectangle(video_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(video_frame, f"{label} {conf:.2f}", (x1, y1 - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                cv2.imwrite(f"{DETECTIONS_DIR}/frame_{frame_count:05d}.jpg", video_frame)
                detection_count += 1

            # Inference doesn't run at a perfectly steady frame rate, so
            # the frame is written `repeats` times (based on real elapsed
            # time since the last write) to keep the output video's
            # playback speed matching real time rather than drifting.
            now = time.time()
            repeats = max(1, round((now - last_write_time) * VIDEO_FPS))
            last_write_time = now
            for _ in range(repeats):
                writer.write(video_frame)
            frame_count += 1

            # Publish this frame for the MJPEG preview server's handler
            # thread to pick up on its next iteration.
            with latest_frame_lock:
                latest_frame = video_frame

    except KeyboardInterrupt:
        print(f"\n\nStopped. {frame_count} frames | {detection_count} detections")
        print(f"Video saved: {VIDEO_PATH}")
    finally:
        # Always leave the laser off and the servos re-centered/released,
        # and release hardware/file handles cleanly, however the loop
        # above exited (Ctrl+C or the SIGTERM handler above).
        if laser_on:
            set_laser_gpio(False)
            print("Laser OFF (cleanup)")
        center_servos()
        print("Pan/tilt re-centered (cleanup)")
        writer.release()
        picam2.stop()
        cv2.destroyAllWindows()
        sock.close()


if __name__ == "__main__":
    main()
