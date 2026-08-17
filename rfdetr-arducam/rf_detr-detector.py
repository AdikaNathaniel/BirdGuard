import time
import json
import serial
import socket
import os
import cv2
from datetime import datetime
from picamera2 import Picamera2
from libcamera import controls
from rfdetr import RFDETRNano
from rfdetr.util.coco_classes import COCO_CLASSES

# --- CONFIG ---
SERIAL_PORT = '/dev/serial0'
SERIAL_BAUD = 9600
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
TARGET_CLASS = "person"       # Change to "bird" for production
CONFIDENCE_THRESHOLD = 0.5
LASER_OFF_DELAY = 3.0         # Seconds to keep laser on after last detection
FRAME_WIDTH = 640      # Camera capture resolution. RF-DETR inference always
FRAME_HEIGHT = 480     # runs at this same resolution (captured frame is fed
                        # to model.predict() unresized).
VIDEO_FPS = 30
WINDOW_NAME = "BirdGuard - RF-DETR"

# Session folder
session_name = datetime.now().strftime("session_%Y-%m-%d_%H-%M-%S")
SESSION_DIR = f"/home/pi/birdguard-test/{session_name}"
DETECTIONS_DIR = f"{SESSION_DIR}/detections"
VIDEO_PATH = f"{SESSION_DIR}/recording.avi"
os.makedirs(DETECTIONS_DIR, exist_ok=True)


def main():
    print(f"Session: {SESSION_DIR}")
    print(f"Target: {TARGET_CLASS.upper()} | Confidence: {CONFIDENCE_THRESHOLD}")
    print(f"Video: {VIDEO_PATH}")

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

    # Load RF-DETR
    print("Loading RF-DETR (Nano)...")
    model = RFDETRNano()
    print("Model loaded.")

    # Init camera (explicitly load the Arducam tuning file so color
    # reproduction matches rpicam-still, which auto-loads it)
    tuning = Picamera2.load_tuning_file("arducam_64mp.json")
    picam2 = Picamera2(tuning=tuning)
    config = picam2.create_still_configuration(
        main={"size": (FRAME_WIDTH, FRAME_HEIGHT), "format": "RGB888"}
    )
    picam2.configure(config)
    picam2.start()
    picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous, "Saturation": 2.0})
    time.sleep(1)

    # Init video writer — records continuously from the start
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    writer = cv2.VideoWriter(VIDEO_PATH, fourcc, VIDEO_FPS, (FRAME_WIDTH, FRAME_HEIGHT))
    print(f"Recording started -> {VIDEO_PATH}")

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

    laser_on = False
    last_detection_time = 0
    frame_count = 0
    detection_count = 0

    print(f"\nWatching for {TARGET_CLASS.upper()}... (press 'q' or close window to stop)\n")

    try:
        while True:
            frame = picam2.capture_array()  # RGB888
            frame = cv2.flip(frame, -1)  # 180 degree flip (physical camera mount is upside-down)
            bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            if frame_count < 5:
                print(f"DEBUG frame {frame_count}: R={frame[:,:,0].mean():.1f} G={frame[:,:,1].mean():.1f} B={frame[:,:,2].mean():.1f} | "
                      f"pixel[240,320]={frame[240,320].tolist()} dtype={frame.dtype} shape={frame.shape}")

            # RF-DETR expects an RGB array/PIL image
            detections = model.predict(frame, threshold=CONFIDENCE_THRESHOLD)

            target_found = False
            video_frame = bgr.copy()

            for box, class_id, conf in zip(detections.xyxy, detections.class_id, detections.confidence):
                label = COCO_CLASSES[class_id]
                if label != TARGET_CLASS:
                    continue

                target_found = True
                last_detection_time = time.time()

                x1, y1, x2, y2 = map(int, box)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] DETECTED: {label.upper()} | conf: {conf:.2f}")

                payload = {
                    "timestamp": time.time(),
                    "label": label,
                    "confidence": float(conf),
                    "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
                }
                sock.sendto(json.dumps(payload).encode(), (UDP_IP, UDP_PORT))

                cv2.rectangle(video_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(video_frame, f"{label} {conf:.2f}", (x1, y1 - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            if target_found:
                cv2.imwrite(f"{DETECTIONS_DIR}/frame_{frame_count:05d}.jpg", video_frame)
                detection_count += 1

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

            # --- LIVE PREVIEW (shown while running) + RECORDING (saved on close) ---
            cv2.imshow(WINDOW_NAME, video_frame)
            writer.write(video_frame)
            frame_count += 1

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                print("\nWindow closed by user.")
                break

    except KeyboardInterrupt:
        print(f"\n\nStopped via Ctrl+C.")
    finally:
        print(f"{frame_count} frames | {detection_count} detections")
        print(f"Video saved: {VIDEO_PATH}")
        if laser_on and ser:
            ser.write(b'F')
            print("Laser OFF (cleanup)")
        writer.release()
        cv2.destroyAllWindows()
        picam2.stop()
        if ser:
            ser.close()
        sock.close()


if __name__ == "__main__":
    main()
