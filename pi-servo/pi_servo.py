from gpiozero import AngularServo, OutputDevice

# Up/down servo -- signal wire -> Pi GPIO27 (physical pin 13) directly.
# Servo VCC -> 5V, Servo GND -> 2N2222 collector, 2N2222 emitter -> common GND.
SERVO_PIN = 27

# 2N2222 base -> Pi GPIO12 (physical pin 32) through a ~470ohm resistor.
# Gates the servo's GND return path -- HIGH powers the servo on, LOW cuts it.
POWER_PIN = 12

CENTER_ANGLE = 90
STEP_DEGREES = 3   # degrees per step
MAX_STEPS = 10     # u10/d10 = 30 degrees from center (60-120 range, same safe limits as nano-servo)

power = OutputDevice(POWER_PIN, initial_value=False)

servo = AngularServo(
    SERVO_PIN,
    min_angle=0,
    max_angle=180,
    min_pulse_width=0.0005,
    max_pulse_width=0.0025,
)


def move_to(angle):
    # Clamped to the servo's full physical range as a hard safety limit.
    angle = max(0, min(180, angle))
    servo.angle = angle
    print(f"Up/down angle set to: {angle}")


def main():
    print("--- Pi Up/Down Servo Step Control ---")
    print("Send 'on' to power the servo, 'off' to cut power.")
    print(f"Send u1-u{MAX_STEPS} to move up in steps, d1-d{MAX_STEPS} to move down in steps.")
    print("Send 'c' to re-center. Ctrl+C to quit.")

    try:
        while True:
            cmd = input("> ").strip().lower()

            if cmd == 'on':
                power.on()
                print("Servo power ON")
                continue

            if cmd == 'off':
                power.off()
                print("Servo power OFF")
                continue

            # Every movement command below requires power to already be on
            # -- the transistor gate cuts the servo's ground return, so
            # commanding an angle while power is off would silently do
            # nothing at the hardware level.
            if not power.value:
                print("Servo power is off -- send 'on' first.")
                continue

            if cmd == 'c':
                move_to(CENTER_ANGLE)
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
                print("Invalid command. Use on, off, u1-u10, d1-d10, or c.")

    except KeyboardInterrupt:
        pass
    finally:
        if power.value:
            move_to(CENTER_ANGLE)
        power.off()
        servo.close()
        power.close()
        print("\nShutdown complete.")


if __name__ == "__main__":
    main()
