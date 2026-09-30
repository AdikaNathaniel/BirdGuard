import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import time
import cv2
from config.settings import (CAMERA_RESOLUTION, FRAME_RATE, MODEL_PATH,
                             CONFIDENCE, TARGET_CLASS, INFERENCE_SIZE,
                             LASER_GPIO_PIN, LASER_ACTIVE_HIGH)
from src.hardware.camera import Camera
from src.detection.detector import PersonDetector
from src.hardware.laser import Laser

cam = Camera(CAMERA_RESOLUTION, FRAME_RATE)
detector = PersonDetector(MODEL_PATH, CONFIDENCE, TARGET_CLASS, INFERENCE_SIZE)
laser = Laser(LASER_GPIO_PIN, LASER_ACTIVE_HIGH)
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
        if detections:
            laser.on()
            status, color = "LASER: ON", (0, 0, 255)
        else:
            laser.off()
            status, color = "LASER: OFF", (0, 255, 0)
        fps = 1.0 / max(time.time() - prev, 1e-6)
        prev = time.time()
        cv2.putText(frame, f"{status}  FPS: {fps:.1f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.imshow("test_05 ai+laser - q to quit", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
finally:
    laser.off()
    laser.close()
    cam.release()
    cv2.destroyAllWindows()
print("AI + laser test done.")