from adafruit_servokit import ServoKit

# PCA9685 (16-channel, 12-bit PWM driver) over I2C:
# Pi 3.3V -> PCA9685 VCC (logic power)
# Pi GND  -> PCA9685 GND
# Pi GPIO2 (SDA, physical pin 3) -> PCA9685 SDA
# Pi GPIO3 (SCL, physical pin 5) -> PCA9685 SCL
#
# Each servo connects to one of the PCA9685's 16 output channels. All
# channels share the same V+ terminal for motor power (e.g. 5V for a
# standard hobby servo) -- NOT the Pi's 3.3V logic supply.
PAN_CHANNEL = 0
TILT_CHANNEL = 15

CENTER_ANGLE = 90
STEP_DEGREES = 3   # degrees per step
MAX_STEPS = 10      # step 10 = 30 degrees from center (60-120 range)

kit = ServoKit(channels=16)


def move_to(channel, angle, label):
    angle = max(0, min(180, angle))
    kit.servo[channel].angle = angle
    print(f"{label} angle set to: {angle}")


def stop(channel, label):
    kit.servo[channel].angle = None  # cuts the PWM signal -- motor goes limp/unpowered
    print(f"{label} stopped (released, no signal)")


def center_all():
    move_to(PAN_CHANNEL, CENTER_ANGLE, "Pan")
    move_to(TILT_CHANNEL, CENTER_ANGLE, "Tilt")


def stop_all():
    stop(PAN_CHANNEL, "Pan")
    stop(TILT_CHANNEL, "Tilt")


def main():
    print("--- Pi -> PCA9685 Pan/Tilt Driver (I2C) ---")
    print(f"Pan:  u1-u{MAX_STEPS} (up in steps), d1-d{MAX_STEPS} (down in steps)")
    print(f"Tilt: i1-i{MAX_STEPS} (up in steps), k1-k{MAX_STEPS} (down in steps)")
    print("'c' to re-center both, 's' to release both. Ctrl+C to quit.")

    center_all()

    try:
        while True:
            cmd = input("> ").strip().lower()

            if cmd == 'c':
                center_all()
                continue

            if cmd == 's':
                stop_all()
                continue

            if len(cmd) >= 2 and cmd[0] in ('u', 'd', 'i', 'k'):
                try:
                    step = int(cmd[1:])
                except ValueError:
                    print("Invalid command.")
                    continue

                if not (1 <= step <= MAX_STEPS):
                    print(f"Step must be between 1 and {MAX_STEPS}.")
                    continue

                if cmd[0] in ('u', 'd'):
                    channel, label = PAN_CHANNEL, "Pan"
                    sign = 1 if cmd[0] == 'u' else -1
                else:
                    channel, label = TILT_CHANNEL, "Tilt"
                    sign = 1 if cmd[0] == 'i' else -1

                move_to(channel, CENTER_ANGLE + sign * step * STEP_DEGREES, label)
            else:
                print("Invalid command. Use u1-u10, d1-d10 (pan), i1-i10, k1-k10 (tilt), c, or s.")

    except KeyboardInterrupt:
        pass
    finally:
        center_all()
        print("\nShutdown complete.")


if __name__ == "__main__":
    main()
