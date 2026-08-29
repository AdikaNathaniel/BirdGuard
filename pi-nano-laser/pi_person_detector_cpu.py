import time
import json
import socket
import os
import subprocess
import threading
import cv2
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from picamera2 import Picamera2
from ultralytics import YOLO
from pymongo import MongoClient

# --- CONFIG ---
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

# Session folder
session_name = datetime.now().strftime("session_%Y-%m-%d_%H-%M-%S")
SESSION_DIR = f"/home/pi/birdguard-test/{session_name}"
DETECTIONS_DIR = f"{SESSION_DIR}/detections"
VIDEO_PATH = f"{SESSION_DIR}/recording.avi"
os.makedirs(DETECTIONS_DIR, exist_ok=True)


def set_laser_gpio(high: bool):
    state = "dh" if high else "dl"
    try:
        subprocess.run(["pinctrl", "set", str(LASER_GPIO), "op", state], check=True)
    except Exception as e:
        print(f"pinctrl call failed: {e}")


# --- DETECTION LOGGING (writes directly to MongoDB; the backend's
# detection-service only ever reads this collection, never writes to it) ---
try:
    _mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    _detections_collection = _mongo_client["birdguard"]["detections"]
except Exception as e:
    print(f"MongoDB connection failed (detection logging disabled): {e}")
    _detections_collection = None


def log_detection_event(label, confidence, bbox=None):
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
latest_frame = None
latest_frame_lock = threading.Lock()


class _MJPEGHandler(BaseHTTPRequestHandler):
    def do_GET(self):
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
            pass

    def log_message(self, format, *args):
        pass  # silence per-request access logging


def start_preview_server(port=PREVIEW_PORT):
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

    set_laser_gpio(False)  # laser OFF at startup

    # Init UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Load YOLOv8
    print("Loading YOLOv8 (n)...")
    model = YOLO("yolov8n.pt")
    print("Model loaded.")

    # Init camera
    picam2 = Picamera2()
    config = picam2.create_video_configuration(
        main={"size": (FRAME_WIDTH, FRAME_HEIGHT), "format": "RGB888"},
        controls={"FrameDurationLimits": (33333, 66666)}
    )
    picam2.configure(config)
    picam2.start()
    picam2.set_controls({"AwbEnable": True, "Saturation": 1.5, "Brightness": 0.2})
    time.sleep(2)

    # Init video writer — records continuously from the start
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
            frame = picam2.capture_array()
            bgr = frame

            results = model.predict(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)[0]
            target_found = False
            detections = []

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

                    payload = {
                        "timestamp": time.time(),
                        "label": label,
                        "confidence": conf,
                        "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
                    }
                    sock.sendto(json.dumps(payload).encode(), (UDP_IP, UDP_PORT))

            # --- LASER CONTROL (Pi GPIO12 -> Nano D2 -> Nano D6 -> laser) ---
            if target_found and not laser_on:
                set_laser_gpio(True)
                laser_on = True
                print(">>> LASER ON")

                # Log this as one detection event (not per-frame) -- use
                # the highest-confidence detection in this frame.
                top = max(detections, key=lambda d: d[5])
                x1, y1, x2, y2, top_label, top_conf = top
                log_detection_event(top_label, top_conf, {"x1": x1, "y1": y1, "x2": x2, "y2": y2})

            elif not target_found and laser_on:
                if time.time() - last_detection_time > LASER_OFF_DELAY:
                    set_laser_gpio(False)
                    laser_on = False
                    print(">>> LASER OFF")

            # --- VIDEO RECORDING ---
            video_frame = bgr.copy()
            if detections:
                for x1, y1, x2, y2, label, conf in detections:
                    cv2.rectangle(video_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(video_frame, f"{label} {conf:.2f}", (x1, y1 - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                cv2.imwrite(f"{DETECTIONS_DIR}/frame_{frame_count:05d}.jpg", video_frame)
                detection_count += 1

            now = time.time()
            repeats = max(1, round((now - last_write_time) * VIDEO_FPS))
            last_write_time = now
            for _ in range(repeats):
                writer.write(video_frame)
            frame_count += 1

            with latest_frame_lock:
                latest_frame = video_frame

    except KeyboardInterrupt:
        print(f"\n\nStopped. {frame_count} frames | {detection_count} detections")
        print(f"Video saved: {VIDEO_PATH}")
    finally:
        if laser_on:
            set_laser_gpio(False)
            print("Laser OFF (cleanup)")
        writer.release()
        picam2.stop()
        cv2.destroyAllWindows()
        sock.close()


if __name__ == "__main__":
    main()
