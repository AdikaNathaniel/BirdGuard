import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import time
import cv2
from config.settings import (CAMERA_RESOLUTION, FRAME_RATE, MODEL_PATH,
                             CONFIDENCE, TARGET_CLASS, INFERENCE_SIZE)
from src.hardware.camera import Camera
from src.detection.detector import PersonDetector

cam = Camera(CAMERA_RESOLUTION, FRAME_RATE)
detector = PersonDetector(MODEL_PATH, CONFIDENCE, TARGET_CLASS, INFERENCE_SIZE)
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
            cv2.putText(frame, f'person {det["confidence"]:.2f}', (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        fps = 1.0 / max(time.time() - prev, 1e-6)
        prev = time.time()
        cv2.putText(frame, f"FPS: {fps:.1f}  detections: {len(detections)}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.imshow("test_02 detection - q to quit", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
finally:
    cam.release()
    cv2.destroyAllWindows()
print("Detection test done.")
