import time
import json
import socket
import os
import subprocess
import cv2
from datetime import datetime
from picamera2 import Picamera2
from ultralytics import YOLO

# --- CONFIG ---
LASER_GPIO = 12               # Pi GPIO12 -> Nano D2 -> Nano D6 -> laser
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
TARGET_CLASS = "person"
CONFIDENCE_THRESHOLD = 0.5
LASER_OFF_DELAY = 3.0         # Seconds to keep laser on after last detection
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
VIDEO_FPS = 60

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


def main():
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

    # Live preview needs a display (X11/Wayland). Over a headless SSH session
    # there isn't one -- Qt hard-aborts the process (not a catchable exception)
    # if imshow/namedWindow is called with no DISPLAY, so check env vars up
    # front and never touch a cv2 GUI function at all when headless.
    headless = not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    if headless:
        print("No display available -- running headless (no live preview). Use Ctrl+C to stop.")

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

            if not headless:
                cv2.imshow("BirdGuard - Live Detection", video_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("\n\n'q' pressed, stopping.")
                    break

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
