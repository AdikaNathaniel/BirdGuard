import time
import json
import socket
import os
import numpy as np
from datetime import datetime
from picamera2 import Picamera2
from ultralytics import YOLO

UDP_IP = "127.0.0.1"
UDP_PORT = 5005
SAVE_ANNOTATED = True

# Save folder named with current date and time e.g. detections_2026-05-27_14-30-00
session_name = datetime.now().strftime("detections_%Y-%m-%d_%H-%M-%S")
SAVE_DIR = f"/home/pi/birdguard-test/{session_name}"

KNOWN_BIRD_WIDTH_MM = 150
FOCAL_LENGTH_PIXELS = 500
CX, CY = 320, 240

os.makedirs(SAVE_DIR, exist_ok=True)
print(f"Saving detections to: {SAVE_DIR}")

def main():
    print("Loading YOLO model...")
    model = YOLO("yolov8n.pt")
    print("Model loaded.")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    picam2 = Picamera2()
    config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"})
    picam2.configure(config)
    picam2.start()
    time.sleep(2)
    print("Camera started. Running detection — press Ctrl+C to stop.\n")

    frame_count = 0
    try:
        while True:
            frame = picam2.capture_array()
            results = model(frame, verbose=False)[0]

            detections = []
            for result in results.boxes:
                box = result.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = map(int, box)
                conf = float(result.conf[0])
                cls = int(result.cls[0])
                label = model.names[cls]

                box_w = x2 - x1
                center_x = x1 + box_w // 2
                center_y = y1 + (y2 - y1) // 2
                z_mm = int((KNOWN_BIRD_WIDTH_MM * FOCAL_LENGTH_PIXELS) / box_w) if box_w > 0 else 0
                x_mm = int((center_x - CX) * z_mm / FOCAL_LENGTH_PIXELS)
                y_mm = int((center_y - CY) * z_mm / FOCAL_LENGTH_PIXELS)

                print(f"DETECTED: {label.upper()} | confidence: {conf:.2f} | position X:{x_mm}mm Y:{y_mm}mm Z:{z_mm}mm")

                payload = {
                    "timestamp": time.time(),
                    "id": 0,
                    "label": label,
                    "confidence": conf,
                    "spatial": {"x_mm": x_mm, "y_mm": y_mm, "z_mm": z_mm},
                    "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
                }
                sock.sendto(json.dumps(payload).encode(), (UDP_IP, UDP_PORT))
                detections.append((x1, y1, x2, y2, label, conf))

            if SAVE_ANNOTATED and detections:
                import cv2
                annotated = frame.copy()
                for x1, y1, x2, y2, label, conf in detections:
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(annotated, f"{label} {conf:.2f}", (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                filename = f"{SAVE_DIR}/frame_{frame_count:05d}.jpg"
                cv2.imwrite(filename, cv2.cvtColor(annotated, cv2.COLOR_RGB2BGR))
                print(f"  -> Saved annotated image: {filename}")

            frame_count += 1
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        picam2.stop()
        sock.close()

if __name__ == "__main__":
    main()
