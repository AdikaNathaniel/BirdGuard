import time
import json
import socket
import os
import subprocess
import cv2
import numpy as np
from datetime import datetime
from picamera2 import Picamera2
from ultralytics import YOLO

UDP_IP = "127.0.0.1"
UDP_PORT = 5005
SAVE_ANNOTATED = True
RECORD_SECONDS = 10  # How many seconds to record video

# Auto-transfer to PC after each session
PC_IP = "192.168.43.116"
PC_USER = "23324"
PC_DEST_PATH = "/C/Users/23324/Desktop/Projects/BirdGuard/picam-test/detections"

# Session folder named with current date and time
session_name = datetime.now().strftime("session_%Y-%m-%d_%H-%M-%S")
SESSION_DIR = f"/home/pi/birdguard-test/{session_name}"
VIDEO_PATH = f"{SESSION_DIR}/recording.mp4"
DETECTIONS_DIR = f"{SESSION_DIR}/detections"

KNOWN_BIRD_WIDTH_MM = 150
FOCAL_LENGTH_PIXELS = 500
CX, CY = 320, 240

os.makedirs(SESSION_DIR, exist_ok=True)
os.makedirs(DETECTIONS_DIR, exist_ok=True)
print(f"Session folder: {SESSION_DIR}")


def record_video():
    """Step 1: Record video from Pi camera."""
    print(f"\n--- STEP 1: Recording {RECORD_SECONDS} seconds of video ---")
    picam2 = Picamera2()
    config = picam2.create_video_configuration(main={"size": (640, 480), "format": "RGB888"})
    picam2.configure(config)

    # Use OpenCV to write video frames
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(VIDEO_PATH, fourcc, 30, (640, 480))

    picam2.start()
    time.sleep(1)
    print(f"Recording... (press Ctrl+C to stop early)")

    start_time = time.time()
    frame_count = 0
    try:
        while (time.time() - start_time) < RECORD_SECONDS:
            frame = picam2.capture_array()
            bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            out.write(bgr_frame)
            frame_count += 1
            elapsed = time.time() - start_time
            print(f"  Recording: {elapsed:.1f}s / {RECORD_SECONDS}s | frames: {frame_count}", end="\r")
    except KeyboardInterrupt:
        print("\nRecording stopped early.")
    finally:
        picam2.stop()
        out.release()

    print(f"\nVideo saved: {VIDEO_PATH} ({frame_count} frames)")
    return frame_count


def process_video():
    """Step 2: Run YOLO on recorded video and save annotated images."""
    print(f"\n--- STEP 2: Processing video with YOLO ---")
    print("Loading YOLO model...")
    model = YOLO("yolov8n.pt")
    print("Model loaded.")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print("Error: Could not open video file.")
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_count = 0
    detection_count = 0

    print(f"Processing {total_frames} frames...\n")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

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

                print(f"DETECTED: {label.upper()} | confidence: {conf:.2f} | X:{x_mm}mm Y:{y_mm}mm Z:{z_mm}mm")

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
                annotated = frame.copy()
                for x1, y1, x2, y2, label, conf in detections:
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(annotated, f"{label} {conf:.2f}", (x1, y1 - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                filename = f"{DETECTIONS_DIR}/frame_{frame_count:05d}.jpg"
                cv2.imwrite(filename, annotated)
                print(f"  -> Saved: {filename}")
                detection_count += 1

            frame_count += 1
            print(f"  Progress: {frame_count}/{total_frames} frames", end="\r")

    except KeyboardInterrupt:
        print("\nProcessing stopped early.")
    finally:
        cap.release()
        sock.close()

    print(f"\n--- DONE ---")
    print(f"Processed {frame_count} frames")
    print(f"Saved {detection_count} annotated images to: {DETECTIONS_DIR}")


def transfer_to_pc():
    """Step 3: Transfer session folder to PC via SCP."""
    print(f"\n--- STEP 3: Transferring session to PC ---")
    dest = f"{PC_USER}@{PC_IP}:{PC_DEST_PATH}"
    result = subprocess.run(["scp", "-r", SESSION_DIR, dest], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Transfer complete -> {dest}")
    else:
        print(f"Transfer failed: {result.stderr}")
        print("Tip: Enable OpenSSH Server on your PC and set up SSH keys for passwordless transfer.")


if __name__ == "__main__":
    record_video()
    process_video()
    transfer_to_pc()
