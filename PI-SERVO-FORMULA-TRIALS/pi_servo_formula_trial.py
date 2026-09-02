import time

import RPi.GPIO as GPIO

# --- CONFIG ---
SERVO_PIN = 15   # BCM numbering -- GPIO15 (physical pin 10). Not a
                 # hardware-PWM-capable pin on a regular Pi, so this uses
                 # RPi.GPIO's software PWM (fine for a single servo test,
                 # just a bit less precise/jitter-free than hardware PWM).
PWM_FREQ_HZ = 50  # standard servo signal frequency -> 20ms period

# Formula trial: uses the exact given formula --
#   raw_value = (6553 / 180) * angle + 1638
# -- which is a Raspberry Pi Pico `duty_u16` value (0-65535 scale). RPi.GPIO's
# software PWM on a regular Pi expects a duty-cycle *percentage* (0-100)
# instead, so raw_value is converted to that scale (raw_value / 65535 * 100)
# purely as a unit conversion -- the formula itself, and the pulse-width
# result it produces, are unchanged.


def angle_to_duty(angle):
    angle = max(0.0, min(180.0, angle))
    raw_value = (6553 / 180) * angle + 1638   # exact given formula
    duty_percent = (raw_value / 65535) * 100.0  # 16-bit scale -> 0-100% scale
    pulse_width_ms = (duty_percent / 100.0) * 20.0
    return duty_percent, pulse_width_ms, raw_value


GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)
pwm = GPIO.PWM(SERVO_PIN, PWM_FREQ_HZ)
pwm.start(0)


def main():
    print("--- Servo Formula Trial (GPIO15, RPi.GPIO software PWM) ---")
    print("Enter an angle (0-180) to move the servo using:")
    print("  raw_value = (6553/180)*angle + 1638   [given formula]")
    print("Enter 'r' to release (stop signal), 'q' to quit.")

    try:
        while True:
            cmd = input("angle> ").strip().lower()

            if cmd == 'q':
                break

            if cmd == 'r':
                pwm.ChangeDutyCycle(0)
                print("Released (signal stopped).")
                continue

            try:
                angle = float(cmd)
            except ValueError:
                print("Enter a number (0-180), 'r' to release, or 'q' to quit.")
                continue

            duty, pulse_ms, raw_value = angle_to_duty(angle)
            pwm.ChangeDutyCycle(duty)
            print(f"angle={angle:.1f} -> raw_value={raw_value:.1f} -> "
                  f"duty={duty:.2f}% -> pulse={pulse_ms:.3f}ms")

    finally:
        pwm.ChangeDutyCycle(0)
        time.sleep(0.1)
        pwm.stop()
        GPIO.cleanup()
        print("\nCleaned up on exit.")


if __name__ == "__main__":
    main()
