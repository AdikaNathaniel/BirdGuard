import time
import json
import serial
import socket
import os
import cv2
from datetime import datetime
from picamera2 import Picamera2
from ultralytics import YOLO

# --- CONFIG ---
SERIAL_PORT = '/dev/serial0'
SERIAL_BAUD = 9600
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
TARGET_CLASS = "person"       # Change to "bird" for production
CONFIDENCE_THRESHOLD = 0.5
LASER_OFF_DELAY = 3.0         # Seconds to keep laser on after last detection
SAVE_ANNOTATED = True

# Session folder
session_name = datetime.now().strftime("session_%Y-%m-%d_%H-%M-%S")
SESSION_DIR = f"/home/pi/birdguard-test/{session_name}"
DETECTIONS_DIR = f"{SESSION_DIR}/detections"
os.makedirs(DETECTIONS_DIR, exist_ok=True)


def main():
    print(f"Session: {SESSION_DIR}")
    print(f"Target: {TARGET_CLASS.upper()} | Confidence threshold: {CONFIDENCE_THRESHOLD}")

    # Init UART
    try:
        ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
        time.sleep(1)
        print(f"UART ready: {SERIAL_PORT} @ {SERIAL_BAUD} baud")
    except Exception as e:
        print(f"UART not available: {e}")
        ser = None

    # Init UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Load YOLO
    print("Loading YOLOv8n...")
    model = YOLO("yolov8n.pt")
    print("Model loaded.")

    # Init camera
    picam2 = Picamera2()
    config = picam2.create_video_configuration(main={"size": (640, 480), "format": "RGB888"})
    picam2.configure(config)
    picam2.start()
    time.sleep(1)

    laser_on = False
    last_detection_time = 0
    frame_count = 0
    detection_count = 0

    print(f"\nWatching for {TARGET_CLASS.upper()}... (Ctrl+C to stop)\n")

    try:
        while True:
            frame = picam2.capture_array()
            bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            results = model(bgr, verbose=False)[0]
            target_found = False
            detections = []

            for result in results.boxes:
                cls = int(result.cls[0])
                label = model.names[cls]
                conf = float(result.conf[0])

                if label == TARGET_CLASS and conf >= CONFIDENCE_THRESHOLD:
                    target_found = True
                    last_detection_time = time.time()

                    box = result.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = map(int, box)
                    detections.append((x1, y1, x2, y2, label, conf))

                    print(f"[{datetime.now().strftime('%H:%M:%S')}] DETECTED: {label.upper()} | conf: {conf:.2f}")

                    # Send UDP payload for future bridge/logging
                    payload = {
                        "timestamp": time.time(),
                        "label": label,
                        "confidence": conf,
                        "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
                    }
                    sock.sendto(json.dumps(payload).encode(), (UDP_IP, UDP_PORT))

            # --- LASER CONTROL ---
            if target_found and not laser_on:
                if ser:
                    ser.write(b'O')
                laser_on = True
                print(f">>> LASER ON")

            elif not target_found and laser_on:
                if time.time() - last_detection_time > LASER_OFF_DELAY:
                    if ser:
                        ser.write(b'F')
                    laser_on = False
                    print(f">>> LASER OFF")

            # Save annotated frame on detection
            if SAVE_ANNOTATED and detections:
                annotated = bgr.copy()
                for x1, y1, x2, y2, label, conf in detections:
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(annotated, f"{label} {conf:.2f}", (x1, y1 - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                cv2.imwrite(f"{DETECTIONS_DIR}/frame_{frame_count:05d}.jpg", annotated)
                detection_count += 1

            frame_count += 1

    except KeyboardInterrupt:
        print(f"\n\nStopped. {frame_count} frames processed, {detection_count} detections saved.")
    finally:
        if laser_on and ser:
            ser.write(b'F')
            print("Laser OFF (cleanup)")
        picam2.stop()
        if ser:
            ser.close()
        sock.close()


if __name__ == "__main__":
    main()
