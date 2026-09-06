from adafruit_servokit import ServoKit

# PCA9685 (16-channel, 12-bit PWM driver) over I2C:
# Pi 3.3V -> PCA9685 VCC (logic power)
# Pi GND  -> PCA9685 GND
# Pi GPIO2 (SDA, physical pin 3) -> PCA9685 SDA
# Pi GPIO3 (SCL, physical pin 5) -> PCA9685 SCL
#
# The tilt servo's 3-wire connector plugs into one PCA9685 channel header:
# yellow/orange -> signal, red -> V+ (motor power, e.g. 5V -- NOT the Pi's
# 3.3V logic supply), brown/black -> GND.
TILT_CHANNEL = 0

CENTER_ANGLE = 90
STEP_DEGREES = 10   # degrees moved per up/down command
MIN_ANGLE = 0
MAX_ANGLE = 180

kit = ServoKit(channels=16)

# Tracked separately from the servo's own state since a released servo
# (angle = None) doesn't report an angle back -- this is the single source
# of truth for "where up/down should move to next".
current_angle = CENTER_ANGLE


def move_to(angle):
    global current_angle
    # Clamped to the servo's full physical range as a hard safety limit.
    angle = max(MIN_ANGLE, min(MAX_ANGLE, angle))
    current_angle = angle
    kit.servo[TILT_CHANNEL].angle = angle
    print(f"Tilt angle set to: {angle}")


def stop():
    kit.servo[TILT_CHANNEL].angle = None  # cuts the PWM signal -- motor goes limp/unpowered
    print("Tilt stopped (released, no signal)")


def main():
    print("--- Pi -> PCA9685 Tilt Test (I2C) ---")
    print(f"Channel {TILT_CHANNEL}, starting centered at {CENTER_ANGLE} degrees")
    print("'up' to tilt up, 'down' to tilt down, 'c' to re-center, 's' to release. Ctrl+C to quit.")

    move_to(CENTER_ANGLE)

    try:
        while True:
            cmd = input("> ").strip().lower()

            if cmd == 'up':
                move_to(current_angle + STEP_DEGREES)
            elif cmd == 'down':
                move_to(current_angle - STEP_DEGREES)
            elif cmd == 'c':
                move_to(CENTER_ANGLE)
            elif cmd == 's':
                stop()
            else:
                print("Invalid command. Use 'up', 'down', 'c' (re-center), or 's' (release).")

    except KeyboardInterrupt:
        pass
    finally:
        stop()
        print("\nShutdown complete.")


if __name__ == "__main__":
    main()
