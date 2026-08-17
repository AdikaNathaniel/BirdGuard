import time
import json
import serial
import socket
import os
import cv2
from datetime import datetime
from picamera2 import Picamera2
from rfdetr import RFDETRNano
from rfdetr.assets.coco_classes import COCO_CLASSES

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

    # Init camera
    picam2 = Picamera2()
    config = picam2.create_video_configuration(
        main={"size": (FRAME_WIDTH, FRAME_HEIGHT), "format": "RGB888"},
        # Allow the sensor to slow down (longer exposure) in dim light instead
        # of forcing a fixed 30fps that caps exposure at ~33ms regardless of
        # lighting. Range = 33.3ms (30fps) to 66.6ms (15fps) -- a 200ms (5fps)
        # ceiling brightened the image but caused visible motion blur from the
        # long exposure window; 66.6ms is a middle ground.
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

    laser_on = False
    last_detection_time = 0
    frame_count = 0
    detection_count = 0
    last_write_time = time.time()

    print(f"\nWatching for {TARGET_CLASS.upper()}... (Ctrl+C to stop)\n")

    try:
        while True:
            frame = picam2.capture_array()
            # TEST: skip RGB->BGR conversion, use raw frame as-is (revert after testing)
            bgr = frame
            # bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            if frame_count < 5:
                print(f"DEBUG frame {frame_count}: R={frame[:,:,0].mean():.1f} G={frame[:,:,1].mean():.1f} B={frame[:,:,2].mean():.1f}")

            results = model.predict(frame, threshold=CONFIDENCE_THRESHOLD)
            target_found = False
            detections = []

            for xyxy, conf, class_id in zip(results.xyxy, results.confidence, results.class_id):
                label = COCO_CLASSES.get(int(class_id), str(class_id))

                if label == TARGET_CLASS:
                    target_found = True
                    last_detection_time = time.time()

                    x1, y1, x2, y2 = map(int, xyxy)
                    conf = float(conf)
                    detections.append((x1, y1, x2, y2, label, conf))

                    print(f"[{datetime.now().strftime('%H:%M:%S')}] DETECTED: {label.upper()} | conf: {conf:.2f}")

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

            # --- VIDEO RECORDING ---
            # Draw bounding boxes on the frame if person detected
            video_frame = bgr.copy()
            if detections:
                for x1, y1, x2, y2, label, conf in detections:
                    cv2.rectangle(video_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(video_frame, f"{label} {conf:.2f}", (x1, y1 - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                # Save detection snapshot as well
                cv2.imwrite(f"{DETECTIONS_DIR}/frame_{frame_count:05d}.jpg", video_frame)
                detection_count += 1

            # Write frame to video (always). Capture rate varies with lighting
            # (see FrameDurationLimits above), but the writer is fixed at
            # VIDEO_FPS, so repeat this frame enough times to cover the real
            # time that actually elapsed -- keeps playback speed matching
            # real time instead of speeding up during slow/dim captures.
            now = time.time()
            repeats = max(1, round((now - last_write_time) * VIDEO_FPS))
            last_write_time = now
            for _ in range(repeats):
                writer.write(video_frame)
            frame_count += 1

            # --- LIVE PREVIEW ---
            cv2.imshow("BirdGuard - Live Detection", video_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n\n'q' pressed, stopping.")
                break

    except KeyboardInterrupt:
        print(f"\n\nStopped. {frame_count} frames | {detection_count} detections")
        print(f"Video saved: {VIDEO_PATH}")
    finally:
        if laser_on and ser:
            ser.write(b'F')
            print("Laser OFF (cleanup)")
        writer.release()
        picam2.stop()
        cv2.destroyAllWindows()
        if ser:
            ser.close()
        sock.close()


if __name__ == "__main__":
    main()
