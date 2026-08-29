from adafruit_servokit import ServoKit

# PCA9685 (16-channel, 12-bit PWM driver) over I2C:
# Pi 3.3V -> PCA9685 VCC (logic power)
# Pi GND  -> PCA9685 GND
# Pi GPIO2 (SDA, physical pin 3) -> PCA9685 SDA
# Pi GPIO3 (SCL, physical pin 5) -> PCA9685 SCL
#
# The servo/motor itself connects to one of the PCA9685's 16 output
# channels, which is powered separately from its own V+ terminal (e.g. 5V
# for a standard hobby servo) -- NOT from the Pi's 3.3V logic supply.
CHANNEL = 0   # which PCA9685 output channel the motor is wired to

CENTER_ANGLE = 90
STEP_DEGREES = 3   # degrees per step
MAX_STEPS = 10      # u10/d10 = 30 degrees from center (60-120 range)

kit = ServoKit(channels=16)


def move_to(angle):
    angle = max(0, min(180, angle))
    kit.servo[CHANNEL].angle = angle
    print(f"Angle set to: {angle}")


def stop():
    kit.servo[CHANNEL].angle = None  # cuts the PWM signal -- motor goes limp/unpowered
    print("Stopped (motor released, no signal)")


def main():
    print("--- Pi -> PCA9685 Motor Driver (I2C) ---")
    print(f"Send u1-u{MAX_STEPS} to move up in steps, d1-d{MAX_STEPS} to move down in steps.")
    print("Send 'c' to re-center, 's' to release the motor. Ctrl+C to quit.")

    move_to(CENTER_ANGLE)

    try:
        while True:
            cmd = input("> ").strip().lower()

            if cmd == 'c':
                move_to(CENTER_ANGLE)
                continue

            if cmd == 's':
                stop()
                continue

            if len(cmd) >= 2 and cmd[0] in ('u', 'd'):
                try:
                    step = int(cmd[1:])
                except ValueError:
                    print("Invalid command.")
                    continue

                if not (1 <= step <= MAX_STEPS):
                    print(f"Step must be between 1 and {MAX_STEPS}.")
                    continue

                if cmd[0] == 'u':
                    move_to(CENTER_ANGLE + step * STEP_DEGREES)
                else:
                    move_to(CENTER_ANGLE - step * STEP_DEGREES)
            else:
                print("Invalid command. Use u1-u10, d1-d10, c, or s.")

    except KeyboardInterrupt:
        pass
    finally:
        move_to(CENTER_ANGLE)
        print("\nShutdown complete.")


if __name__ == "__main__":
    main()
