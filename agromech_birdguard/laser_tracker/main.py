import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import time
import cv2
from config.settings import (CAMERA_RESOLUTION, FRAME_RATE, MODEL_PATH,
                             CONFIDENCE, TARGET_CLASS, INFERENCE_SIZE,
                             PCA9685_I2C_ADDRESS, PWM_FREQUENCY_HZ,
                             SERVO_MIN_US, SERVO_MAX_US,
                             PAN_CHANNEL, TILT_CHANNEL,
                             PAN_MIN_DEG, PAN_MAX_DEG,
                             TILT_MIN_DEG, TILT_MAX_DEG,
                             PAN_START_DEG, TILT_START_DEG,
                             LASER_GPIO_PIN, LASER_ACTIVE_HIGH,
                             TRACK_GAIN, DEAD_ZONE)
from src.hardware.camera import Camera
from src.detection.detector import PersonDetector
from src.hardware.pwm import PWMController
from src.hardware.laser import Laser
from src.tracking.tracker import LaserTracker


def run():
    cam = Camera(CAMERA_RESOLUTION, FRAME_RATE)
    detector = PersonDetector(MODEL_PATH, CONFIDENCE, TARGET_CLASS, INFERENCE_SIZE)
    pwm = PWMController(PCA9685_I2C_ADDRESS, frequency_hz=PWM_FREQUENCY_HZ,
                        servo_min_us=SERVO_MIN_US, servo_max_us=SERVO_MAX_US)
    laser = Laser(LASER_GPIO_PIN, LASER_ACTIVE_HIGH)
    tracker = LaserTracker(pwm, PAN_CHANNEL, TILT_CHANNEL,
                           pan_start=PAN_START_DEG, tilt_start=TILT_START_DEG,
                           pan_limits=(PAN_MIN_DEG, PAN_MAX_DEG),
                           tilt_limits=(TILT_MIN_DEG, TILT_MAX_DEG),
                           gain=TRACK_GAIN, dead_zone=DEAD_ZONE)
    prev = time.time()
    try:
        while True:
            ok, frame = cam.read()
            if not ok:
                break
            detections = detector.detect(frame)
            if detections:
                det = max(detections, key=lambda d: d["confidence"])
                x1, y1, x2, y2 = det["bbox"]
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                tracker.update(det["bbox"], frame.shape[1], frame.shape[0])
                laser.on()
            else:
                laser.off()
            fps = 1.0 / max(time.time() - prev, 1e-6)
            prev = time.time()
            cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.imshow("Laser tracker - q to quit", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        laser.off()
        pwm.release()
        cam.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    run()