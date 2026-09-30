import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import cv2
import numpy as np
from config.settings import (PCA9685_I2C_ADDRESS, PWM_FREQUENCY_HZ, PAN_CHANNEL,
                             TILT_CHANNEL, SERVO_MIN_US, SERVO_MAX_US,
                             PAN_START_DEG, TILT_START_DEG,
                             PAN_MIN_DEG, PAN_MAX_DEG,
                             TILT_MIN_DEG, TILT_MAX_DEG)
from src.hardware.pwm import PWMController

# Step size in degrees per keypress (smaller = finer control)
STEP_DEG = 2

# Initialize PWM controller
pwm = PWMController(PCA9685_I2C_ADDRESS, frequency_hz=PWM_FREQUENCY_HZ,
                    servo_min_us=SERVO_MIN_US, servo_max_us=SERVO_MAX_US)

current_pan = int(PAN_START_DEG)
current_tilt = int(TILT_START_DEG)

# Move to initial center positions
pwm.set_angle(PAN_CHANNEL, current_pan)
pwm.set_angle(TILT_CHANNEL, current_tilt)

# Create a small window to capture keyboard input and display HUD
window_name = "Pan-Tilt Manual Control"
cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

print("--- Manual Pan-Tilt Control ---")
print("Controls:")
print("  LEFT  / RIGHT : Pan servo")
print("  UP    / DOWN  : Tilt servo")
print("  SPACE         : Reset to home/start angles")
print("  Q or ESC      : Quit")

try:
    while True:
        # Create a blank display frame with live telemetry
        hud = np.zeros((220, 420, 3), dtype=np.uint8)
        
        cv2.putText(hud, "PAN-TILT MANUAL CONTROL", (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(hud, f"Pan  (CH {PAN_CHANNEL}): {current_pan:3d} deg  [{PAN_MIN_DEG}-{PAN_MAX_DEG}]",
                    (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
        cv2.putText(hud, f"Tilt (CH {TILT_CHANNEL}): {current_tilt:3d} deg  [{TILT_MIN_DEG}-{TILT_MAX_DEG}]",
                    (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
        cv2.putText(hud, "Arrows: Move | Space: Center | Q: Quit", (20, 180),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

        cv2.imshow(window_name, hud)
        
        # waitKeyEx captures extended arrow key scan codes across Linux/Wayland/X11
        key = cv2.waitKeyEx(30)

        if key in (ord('q'), ord('Q'), 27):  # 27 = ESC
            break

        # Arrow key mapping (supports standard OpenCV key codes and Linux scan codes)
        # UP ARROW: Increase Tilt
        elif key in (82, 65362, 2490368):
            current_tilt = min(TILT_MAX_DEG, current_tilt + STEP_DEG)
            pwm.set_angle(TILT_CHANNEL, current_tilt)

        # DOWN ARROW: Decrease Tilt
        elif key in (84, 65364, 2621440):
            current_tilt = max(TILT_MIN_DEG, current_tilt - STEP_DEG)
            pwm.set_angle(TILT_CHANNEL, current_tilt)

        # LEFT ARROW: Decrease Pan
        elif key in (81, 65361, 2424832):
            current_pan = max(PAN_MIN_DEG, current_pan - STEP_DEG)
            pwm.set_angle(PAN_CHANNEL, current_pan)

        # RIGHT ARROW: Increase Pan
        elif key in (83, 65363, 2555904):
            current_pan = min(PAN_MAX_DEG, current_pan + STEP_DEG)
            pwm.set_angle(PAN_CHANNEL, current_pan)

        # SPACE BAR: Reset to center/home
        elif key == 32:
            current_pan = int(PAN_START_DEG)
            current_tilt = int(TILT_START_DEG)
            pwm.set_angle(PAN_CHANNEL, current_pan)
            pwm.set_angle(TILT_CHANNEL, current_tilt)

finally:
    pwm.release()
    cv2.destroyAllWindows()
    print("Manual test ended. Servos released.")