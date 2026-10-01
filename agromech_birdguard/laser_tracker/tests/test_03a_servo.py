import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import time
from config.settings import (PCA9685_I2C_ADDRESS, PWM_FREQUENCY_HZ, PAN_CHANNEL,
                             TILT_CHANNEL, SERVO_MIN_US, SERVO_MAX_US,
                             PAN_START_DEG, TILT_START_DEG,
                             PAN_MIN_DEG, PAN_MAX_DEG,
                             TILT_MIN_DEG, TILT_MAX_DEG)
from src.hardware.pwm import PWMController

pwm = PWMController(PCA9685_I2C_ADDRESS, frequency_hz=PWM_FREQUENCY_HZ,
                    servo_min_us=SERVO_MIN_US, servo_max_us=SERVO_MAX_US)

def move_servo_slow(channel: int, start_deg: int, end_deg: int, step_delay: float = 0.02, step_deg: int = 1):
    """
    Moves a servo smoothly between two angles at a controlled speed.
    - Increase step_delay (e.g. 0.04) to move slower.
    - Decrease step_delay (e.g. 0.01) to move faster.
    """
    step = step_deg if end_deg >= start_deg else -step_deg
    for angle in range(start_deg, end_deg + step, step):
        pwm.set_angle(channel, angle)
        time.sleep(step_delay)

# Initialize positions
pwm.set_angle(PAN_CHANNEL, PAN_START_DEG)
pwm.set_angle(TILT_CHANNEL, TILT_START_DEG)
time.sleep(0.5)

# --- PAN SWEEP ---
# Move Pan from START -> MAX
move_servo_slow(PAN_CHANNEL, PAN_START_DEG, PAN_MAX_DEG, step_delay=0.03, step_deg=1)
# Move Pan from MAX -> MIN
move_servo_slow(PAN_CHANNEL, PAN_MAX_DEG, PAN_MIN_DEG, step_delay=0.03, step_deg=1)
# Return Pan to START
move_servo_slow(PAN_CHANNEL, PAN_MIN_DEG, PAN_START_DEG, step_delay=0.03, step_deg=1)

# --- TILT SWEEP ---
# Move Tilt from START -> MAX
move_servo_slow(TILT_CHANNEL, TILT_START_DEG, TILT_MAX_DEG, step_delay=0.03, step_deg=1)
# Move Tilt from MAX -> MIN
move_servo_slow(TILT_CHANNEL, TILT_MAX_DEG, TILT_MIN_DEG, step_delay=0.03, step_deg=1)
# Return Tilt to START
move_servo_slow(TILT_CHANNEL, TILT_MIN_DEG, TILT_START_DEG, step_delay=0.03, step_deg=1)

time.sleep(0.5)
pwm.release()
print("Servo test done.")
