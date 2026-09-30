import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import time
import cv2
from config.settings import (CAMERA_RESOLUTION, FRAME_RATE, CAMERA_ROTATION,
                             CAMERA_SATURATION, CAMERA_BRIGHTNESS, MODEL_PATH,
                             CONFIDENCE, TARGET_CLASS, INFERENCE_SIZE,
                             LASER_GPIO_PIN, LASER_ACTIVE_HIGH,
                             RELAY_GPIO_PIN, RELAY_ACTIVE_HIGH, RELAY_SETTLE_S,
                             LASER_OFF_DELAY_S)
from src.hardware.camera import Camera
from src.detection.detector import PersonDetector
from src.hardware.laser import Laser

# Laser first, so it is held OFF while the camera and model load
laser = Laser(LASER_GPIO_PIN, LASER_ACTIVE_HIGH,
              RELAY_GPIO_PIN, RELAY_ACTIVE_HIGH, RELAY_SETTLE_S)
cam = Camera(CAMERA_RESOLUTION, FRAME_RATE, CAMERA_ROTATION,
                 CAMERA_SATURATION, CAMERA_BRIGHTNESS)
detector = PersonDetector(MODEL_PATH, CONFIDENCE, TARGET_CLASS, INFERENCE_SIZE)
print(f"Watching for {TARGET_CLASS}. Laser: GPIO{LASER_GPIO_PIN} | Relay: GPIO{RELAY_GPIO_PIN}")
print(f"Laser stays on {LASER_OFF_DELAY_S:.0f} s after the {TARGET_CLASS} is last seen. q = quit")

last_seen = 0.0
prev = time.time()
try:
    while True:
        ok, frame = cam.read()
        if not ok:
            break
        detections = detector.detect(frame)
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f'{TARGET_CLASS} {det["confidence"]:.2f}', (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        now = time.time()
        if detections:
            last_seen = now
            if not laser.is_on:
                laser.on()
                print(">>> LASER ON")
        elif laser.is_on and now - last_seen > LASER_OFF_DELAY_S:
            laser.off()
            print(">>> LASER OFF")

        if laser.is_on:
            status, color = "LASER: ON", (0, 0, 255)
            if not detections:
                status += f" (off in {LASER_OFF_DELAY_S - (now - last_seen):.1f}s)"
        else:
            status, color = "LASER: OFF", (0, 255, 0)
        fps = 1.0 / max(now - prev, 1e-6)
        prev = now
        cv2.putText(frame, f"{status}  FPS: {fps:.1f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.imshow("test_05 ai+laser - q to quit", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
finally:
    laser.close()
    cam.release()
    cv2.destroyAllWindows()
print("AI + laser test done. Laser and relay OFF.")
