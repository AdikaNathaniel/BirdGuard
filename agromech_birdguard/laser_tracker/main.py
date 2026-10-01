import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import time
import cv2
from config.settings import (CAMERA_RESOLUTION, FRAME_RATE, CAMERA_ROTATION,
                             CAMERA_SATURATION, CAMERA_BRIGHTNESS, MODEL_PATH,
                             CONFIDENCE, TARGET_CLASS, INFERENCE_SIZE,
                             PCA9685_I2C_ADDRESS, PWM_FREQUENCY_HZ,
                             SERVO_MIN_US, SERVO_MAX_US,
                             PAN_CHANNEL, TILT_CHANNEL,
                             PAN_MIN_DEG, PAN_MAX_DEG,
                             TILT_MIN_DEG, TILT_MAX_DEG,
                             PAN_START_DEG, TILT_START_DEG,
                             LASER_GPIO_PIN, LASER_ACTIVE_HIGH,
                             RELAY_GPIO_PIN, RELAY_ACTIVE_HIGH, RELAY_SETTLE_S,
                             LASER_OFF_DELAY_S, TRACK_GAIN, DEAD_ZONE)
from src.hardware.camera import Camera
from src.detection.detector import PersonDetector
from src.hardware.pwm import PWMController
from src.hardware.laser import Laser
from src.tracking.tracker import LaserTracker


def run(target_class=TARGET_CLASS, confidence=CONFIDENCE, fire_laser=True):
    # Laser first, so it is held OFF while the camera and model load
    laser = Laser(LASER_GPIO_PIN, LASER_ACTIVE_HIGH,
                  RELAY_GPIO_PIN, RELAY_ACTIVE_HIGH, RELAY_SETTLE_S)
    cam = Camera(CAMERA_RESOLUTION, FRAME_RATE, CAMERA_ROTATION,
                 CAMERA_SATURATION, CAMERA_BRIGHTNESS)
    detector = PersonDetector(MODEL_PATH, confidence, target_class, INFERENCE_SIZE)
    pwm = PWMController(PCA9685_I2C_ADDRESS, frequency_hz=PWM_FREQUENCY_HZ,
                        servo_min_us=SERVO_MIN_US, servo_max_us=SERVO_MAX_US)
    tracker = LaserTracker(pwm, PAN_CHANNEL, TILT_CHANNEL,
                           pan_start=PAN_START_DEG, tilt_start=TILT_START_DEG,
                           pan_limits=(PAN_MIN_DEG, PAN_MAX_DEG),
                           tilt_limits=(TILT_MIN_DEG, TILT_MAX_DEG),
                           gain=TRACK_GAIN, dead_zone=DEAD_ZONE)
    print(f"Tracking {target_class} (confidence >= {confidence}). Laser: GPIO{LASER_GPIO_PIN} | Relay: GPIO{RELAY_GPIO_PIN}. q = quit")
    last_seen = 0.0
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
                cv2.putText(frame, f'{target_class} {det["confidence"]:.2f}', (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                tracker.update(det["bbox"], frame.shape[1], frame.shape[0])
                newly_seen = time.time() - last_seen > LASER_OFF_DELAY_S
                last_seen = time.time()
                if not fire_laser:
                    if newly_seen:
                        print(f">>> {target_class} detected (laser disabled, would fire now)")
                elif not laser.is_on:
                    laser.on()
                    print(f">>> LASER ON ({target_class} detected)")
            elif laser.is_on and time.time() - last_seen > LASER_OFF_DELAY_S:
                laser.off()
                print(">>> LASER OFF")

            # Crosshair = frame centre, where the tracker steers the target to
            h, w = frame.shape[:2]
            cv2.drawMarker(frame, (w // 2, h // 2), (0, 0, 255), cv2.MARKER_CROSS, 30, 2)
            if not fire_laser:
                status, color = "LASER: DISABLED", (0, 255, 255)
            elif laser.is_on:
                status, color = "LASER: ON", (0, 0, 255)
            else:
                status, color = "LASER: OFF", (0, 255, 0)
            fps = 1.0 / max(time.time() - prev, 1e-6)
            prev = time.time()
            cv2.putText(frame, f"{status}  FPS: {fps:.1f}  pan {tracker.pan:.0f} tilt {tracker.tilt:.0f}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            cv2.imshow("Laser tracker - q to quit", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        laser.close()
        pwm.release()
        cam.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    run()