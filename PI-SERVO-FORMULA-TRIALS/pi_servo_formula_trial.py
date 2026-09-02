import time

import RPi.GPIO as GPIO

# --- CONFIG ---
SERVO_PIN = 15   # BCM numbering -- GPIO15 (physical pin 10). Not a
                 # hardware-PWM-capable pin on a regular Pi, so this uses
                 # RPi.GPIO's software PWM (fine for a single servo test,
                 # just a bit less precise/jitter-free than hardware PWM).
PWM_FREQ_HZ = 50  # standard servo signal frequency -> 20ms period

# Formula trial: linear mapping from angle (0-180) to a PWM duty-cycle
# percentage, targeting the same underlying 0.5ms-2.5ms pulse-width range
# the Raspberry Pi Pico's `duty_u16 = angle * 6553/180 + 1638` formula
# uses -- re-derived here in the units RPi.GPIO's software PWM actually
# expects (a 0-100 duty-cycle percentage), since the Pico's raw 16-bit
# duty_u16 values don't apply to a regular Pi's PWM implementation.
#
#   pulse_width_ms = 0.5 + (angle / 180) * 2.0   (0.5ms at 0 deg, 2.5ms at 180 deg)
#   duty_percent    = (pulse_width_ms / 20ms) * 100
#                   = 2.5 + (angle / 180) * 10


def angle_to_duty(angle):
    angle = max(0.0, min(180.0, angle))
    pulse_width_ms = 0.5 + (angle / 180.0) * 2.0
    duty_percent = (pulse_width_ms / 20.0) * 100.0
    return duty_percent, pulse_width_ms


GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)
pwm = GPIO.PWM(SERVO_PIN, PWM_FREQ_HZ)
pwm.start(0)


def main():
    print("--- Servo Formula Trial (GPIO15, RPi.GPIO software PWM) ---")
    print("Enter an angle (0-180) to move the servo using:")
    print("  duty% = 2.5 + (angle/180)*10   [0.5ms-2.5ms pulse range]")
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

            duty, pulse_ms = angle_to_duty(angle)
            pwm.ChangeDutyCycle(duty)
            print(f"angle={angle:.1f} -> pulse={pulse_ms:.3f}ms -> duty={duty:.2f}%")

    finally:
        pwm.ChangeDutyCycle(0)
        time.sleep(0.1)
        pwm.stop()
        GPIO.cleanup()
        print("\nCleaned up on exit.")


if __name__ == "__main__":
    main()
