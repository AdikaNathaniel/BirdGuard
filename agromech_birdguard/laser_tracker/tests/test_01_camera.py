import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import time
import cv2
from config.settings import (CAMERA_RESOLUTION, FRAME_RATE, CAMERA_ROTATION,
                             CAMERA_SATURATION, CAMERA_BRIGHTNESS)
from src.hardware.camera import Camera

cam = Camera(CAMERA_RESOLUTION, FRAME_RATE, CAMERA_ROTATION,
                 CAMERA_SATURATION, CAMERA_BRIGHTNESS)
prev = time.time()
try:
    while True:
        ok, frame = cam.read()
        if not ok:
            break
        fps = 1.0 / max(time.time() - prev, 1e-6)

        prev = time.time()
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        cv2.imshow("test_01 camera - q to quit", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
finally:
    cam.release()
    cv2.destroyAllWindows()
print("Camera test done.")
