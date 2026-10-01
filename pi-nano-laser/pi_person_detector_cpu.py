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
# the process immediately by default, skipping the try/finally cleanup below.
# Route it through the same path so the laser always gets switched off and
# the servos always get re-centered/released on stop, not just on Ctrl+C.
def _handle_sigterm(signum, frame):
    raise KeyboardInterrupt


signal.signal(signal.SIGTERM, _handle_sigterm)

# --- CONFIG ---
# Central tunables for the whole script: which GPIO fires the laser, where
# detection events get broadcast, what counts as a "person" detection, and
# the camera/recording settings. Kept together at the top so none of this
# needs hunting through the rest of the file to adjust.
LASER_GPIO = 12               # Pi GPIO12 -> Nano D2 -> Nano D6 -> laser
POWER_RELAY_GPIO = 17         # Pi GPIO17 -> 2-channel relay IN1 -> laser PSU positive wire.
                               # Cuts the laser's power supply entirely (not just the trigger
                               # signal) whenever no person is being detected, for energy
                               # saving and as a true hardware-level off between detections
                               # rather than just holding the Nano's trigger line low. Follows
                               # the exact same on/off timing as LASER_GPIO below -- both are
                               # driven together at every transition, never independently.
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
TARGET_CLASS = "person"
CONFIDENCE_THRESHOLD = 0.5
LASER_OFF_DELAY = 3.0         # Seconds to keep laser on after last detection
FRAME_WIDTH = 1280            # final frame size, after rotation
FRAME_HEIGHT = 720
VIDEO_FPS = 30
PREVIEW_PORT = 8080           # browse http://<pi-ip>:8080/ for a live MJPEG preview

# --- CAMERA ORIENTATION + COLOUR ---
# The camera is mounted on its side. For 90/270 the sensor is read as a tall
# centre strip and then turned upright, so the frame is still a full-quality
# FRAME_WIDTH x FRAME_HEIGHT landscape picture rather than a narrow portrait.
CAMERA_ROTATION = 270         # clockwise degrees: 0, 90, 180 or 270
CAMERA_SATURATION = 1.5       # colour strength: 0 = greyscale, 1 = normal
CAMERA_BRIGHTNESS = 0.2       # -1.0 (dark) .. 1.0 (bright), 0 = normal

# --- PAN/TILT TRACKING (PCA9685 over I2C) ---
# Values from agromech_birdguard/laser_tracker/config/settings.py, verified
# there with the servo sweep / manual servo / tracking tests.
PCA9685_I2C_ADDRESS = 0x40
PAN_CHANNEL = 2
TILT_CHANNEL = 3
SERVO_MIN_US = 500            # pulse width at 0 deg
SERVO_MAX_US = 2500           # pulse width at 180 deg
PAN_MIN_DEG, PAN_MAX_DEG = 0, 180
TILT_MIN_DEG, TILT_MAX_DEG = 40, 140   # keeps laser pointed at backdrop
PAN_START_DEG = 90
TILT_START_DEG = 90
TRACK_GAIN = 30.0             # deg correction per unit normalized error
DEAD_ZONE = 0.05              # ignore error within 5% of frame center

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


def set_gpio(pin: int, high: bool):
    # Drives a pin via the `pinctrl` CLI tool rather than a Python GPIO
    # library. `dh`/`dl` = "digital high" / "digital low" in pinctrl's own
    # syntax. Shared by both LASER_GPIO (read by the Arduino Nano, D2) and
    # POWER_RELAY_GPIO (drives the relay module directly) -- same call,
    # different pin number.
    state = "dh" if high else "dl"
    try:
        subprocess.run(["pinctrl", "set", str(pin), "op", state], check=True)
    except Exception as e:
        print(f"pinctrl call failed (GPIO{pin}): {e}")


def set_laser_power(high: bool):
    # Toggles the laser's trigger signal and its power-relay together --
    # every call site in this file wants both at once, so callers never
    # have to remember to drive both pins themselves.
    set_gpio(LASER_GPIO, high)
    set_gpio(POWER_RELAY_GPIO, high)


# --- CAMERA ROTATION ---
# Clockwise rotation in degrees -> OpenCV rotate code
_ROTATE_CODES = {
    90: cv2.ROTATE_90_CLOCKWISE,
    180: cv2.ROTATE_180,
    270: cv2.ROTATE_90_COUNTERCLOCKWISE,
}


def centre_crop(picam2, size):
    # Largest centred sensor area with the same shape as `size`, so the
    # sideways (tall) capture is cropped rather than squashed/stretched.
    max_x, max_y, max_w, max_h = picam2.camera_controls["ScalerCrop"][1]
    aspect = size[0] / size[1]
    crop_w, crop_h = max_w, max_h
    if max_w / max_h > aspect:
        crop_w = int(max_h * aspect)
    else:
        crop_h = int(max_w / aspect)
    return (max_x + (max_w - crop_w) // 2, max_y + (max_h - crop_h) // 2,
            crop_w, crop_h)


def rotate_frame(frame):
    if CAMERA_ROTATION in _ROTATE_CODES:
        return cv2.rotate(frame, _ROTATE_CODES[CAMERA_ROTATION])
    return frame


# --- PAN/TILT TRACKING ---
class PanTiltTracker:
    """Proportional pan/tilt control that steers the target bbox to frame centre.

    The PCA9685 gives no position feedback, so `pan`/`tilt` are the last
    commanded angles -- the only record of where the servos are.
    """

    def __init__(self):
        self.kit = ServoKit(channels=16, address=PCA9685_I2C_ADDRESS)
        for ch in (PAN_CHANNEL, TILT_CHANNEL):
            self.kit.servo[ch].set_pulse_width_range(SERVO_MIN_US, SERVO_MAX_US)
        self.center()

    def center(self):
        self.pan = PAN_START_DEG
        self.tilt = TILT_START_DEG
        self.kit.servo[PAN_CHANNEL].angle = self.pan
        self.kit.servo[TILT_CHANNEL].angle = self.tilt

    def update(self, bbox, frame_w, frame_h):
        x1, y1, x2, y2 = bbox
        err_x = ((x1 + x2) / 2 - frame_w / 2) / (frame_w / 2)   # -1 .. 1
        err_y = ((y1 + y2) / 2 - frame_h / 2) / (frame_h / 2)

        # NOTE: if it tracks AWAY from the person, flip the sign of these two lines
        if abs(err_x) > DEAD_ZONE:
            self.pan -= err_x * TRACK_GAIN
        if abs(err_y) > DEAD_ZONE:
            self.tilt += err_y * TRACK_GAIN

        self.pan = max(PAN_MIN_DEG, min(PAN_MAX_DEG, self.pan))
        self.tilt = max(TILT_MIN_DEG, min(TILT_MAX_DEG, self.tilt))
        self.kit.servo[PAN_CHANNEL].angle = self.pan
        self.kit.servo[TILT_CHANNEL].angle = self.tilt

    def release(self):
        # Re-center, then stop holding torque
        self.center()
        time.sleep(0.5)
        self.kit.servo[PAN_CHANNEL].angle = None
        self.kit.servo[TILT_CHANNEL].angle = None


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
    print(f"Power relay: GPIO{POWER_RELAY_GPIO} -> relay IN1 -> laser PSU")
    print(f"Pan/tilt: PCA9685 0x{PCA9685_I2C_ADDRESS:02X} channel {PAN_CHANNEL} (pan) / "
          f"{TILT_CHANNEL} (tilt) | Camera rotation: {CAMERA_ROTATION} deg")

    set_laser_power(False)  # laser + relay OFF at startup
    tracker = PanTiltTracker()  # servos to start position

    # UDP socket for broadcasting each detection's bounding box to any
    # local listener (e.g. a future pan/tilt tracking process) -- fire
    # and forget, no listener needs to be present for this to work.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Load YOLOv8 -- the "n" (nano) variant, chosen for CPU inference
    # speed on the Pi rather than accuracy, since there's no GPU/NPU here.
    print("Loading YOLOv8 (n)...")
    model = YOLO("yolov8n.pt")
    print("Model loaded.")

    # Init camera at the configured resolution/frame-rate window via
    # picamera2 (libcamera) -- "RGB888" is BGR byte order, which is what
    # OpenCV/YOLO expect. Mounted sideways: ask the sensor for a tall image
    # so the frame is FRAME_WIDTH x FRAME_HEIGHT once rotated upright.
    sideways = CAMERA_ROTATION in (90, 270)
    capture_size = (FRAME_HEIGHT, FRAME_WIDTH) if sideways else (FRAME_WIDTH, FRAME_HEIGHT)
    picam2 = Picamera2()
    config = picam2.create_video_configuration(
        main={"size": capture_size, "format": "RGB888"},
        controls={"FrameDurationLimits": (33333, 66666)}
    )
    picam2.configure(config)
    picam2.start()
    picam2.set_controls({"ScalerCrop": centre_crop(picam2, capture_size),
                         "AwbEnable": True,
                         "Saturation": CAMERA_SATURATION,
                         "Brightness": CAMERA_BRIGHTNESS})
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
            # One frame in, one YOLO pass out -- runs synchronously in the
            # main loop since CPU inference is already the bottleneck here;
            # no benefit to a separate inference thread.
            frame = rotate_frame(picam2.capture_array())
            bgr = frame

            results = model.predict(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)[0]
            target_found = False
            detections = []

            # Walk every detected box this frame and keep only the ones
            # matching TARGET_CLASS ("person") -- YOLO detects many object
            # classes, but only this one drives the laser/logging below.
            for box in results.boxes:
                class_id = int(box.cls[0])
                label = model.names[class_id]

                if label == TARGET_CLASS:
                    target_found = True
                    last_detection_time = time.time()

                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    conf = float(box.conf[0])
                    detections.append((x1, y1, x2, y2, label, conf))

                    print(f"[{datetime.now().strftime('%H:%M:%S')}] DETECTED: {label.upper()} | conf: {conf:.2f}")

                    # Broadcast this detection's box over UDP -- fire and
                    # forget, for any downstream process that wants it
                    # (e.g. pan/tilt tracking), independent of the laser
                    # and MongoDB logic below.
                    payload = {
                        "timestamp": time.time(),
                        "label": label,
                        "confidence": conf,
                        "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
                    }
                    sock.sendto(json.dumps(payload).encode(), (UDP_IP, UDP_PORT))

            # --- PAN/TILT TRACKING (every frame a person is visible) ---
            # Steer toward the highest-confidence person. With no person in
            # view the servos simply hold their last position.
            if detections:
                tx1, ty1, tx2, ty2, _, _ = max(detections, key=lambda d: d[5])
                tracker.update((tx1, ty1, tx2, ty2), frame.shape[1], frame.shape[0])

            # --- LASER + POWER RELAY CONTROL ---
            # (Pi GPIO12 -> Nano D2 -> Nano D6 -> laser trigger,
            #  Pi GPIO17 -> relay IN1 -> laser PSU positive -> laser power)
            # Edge-triggered, not level-triggered: both turn on once when a
            # person first appears, and off only after they've been gone
            # for LASER_OFF_DELAY seconds (debounced so brief gaps in
            # detection between frames don't flicker on/off, which would
            # also chatter the relay's mechanical contacts needlessly).
            if target_found and not laser_on:
                set_laser_power(True)
                laser_on = True
                print(">>> LASER ON (relay powered)")

                # Log this as one detection event (not per-frame) -- use
                # the highest-confidence detection in this frame.
                top = max(detections, key=lambda d: d[5])
                x1, y1, x2, y2, top_label, top_conf = top
                log_detection_event(top_label, top_conf, {"x1": x1, "y1": y1, "x2": x2, "y2": y2})

            elif not target_found and laser_on:
                if time.time() - last_detection_time > LASER_OFF_DELAY:
                    set_laser_power(False)
                    laser_on = False
                    print(">>> LASER OFF (relay unpowered)")

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
            # Crosshair = frame centre (where tracking steers the person to)
            # plus the current commanded servo angles, for checking tracking
            cv2.drawMarker(video_frame, (FRAME_WIDTH // 2, FRAME_HEIGHT // 2),
                           (0, 0, 255), cv2.MARKER_CROSS, 30, 2)
            cv2.putText(video_frame, f"pan {tracker.pan:.0f}  tilt {tracker.tilt:.0f}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

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
        # Always leave the laser and relay off and release hardware/file
        # handles cleanly, however the loop above exited -- including a
        # crash, so the relay can't be left stuck powering the laser.
        if laser_on:
            set_laser_power(False)
            print("Laser + relay OFF (cleanup)")
        tracker.release()
        print("Pan/tilt re-centered and released (cleanup)")
        writer.release()
        picam2.stop()
        cv2.destroyAllWindows()
        sock.close()


if __name__ == "__main__":
    main()
