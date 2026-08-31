from adafruit_servokit import ServoKit

# One-off tool for finding a continuous-rotation servo's true stop point.
# The library's default "center" (90 deg) assumes a generic calibration --
# individual continuous-rotation servos usually need their own stop value
# found empirically (or trimmed via a physical potentiometer, if present).
kit = ServoKit(channels=16)


def main():
    print("--- Servo Stop-Point Calibration ---")
    channel = int(input("Channel to test (e.g. 0 for pan, 4 for tilt): ").strip())
    print(f"Testing channel {channel}. Enter angle values (e.g. 88, 89, 90.5) and")
    print("watch the motor -- find the exact value where rotation stops.")
    print("Enter 'r' to release (cut signal), 'q' to quit.")

    try:
        while True:
            cmd = input(f"[ch{channel}] angle> ").strip().lower()

            if cmd == 'q':
                break

            if cmd == 'r':
                kit.servo[channel].angle = None
                print("Released (signal cut).")
                continue

            try:
                angle = float(cmd)
            except ValueError:
                print("Enter a number, 'r' to release, or 'q' to quit.")
                continue

            angle = max(0.0, min(180.0, angle))
            kit.servo[channel].angle = angle
            print(f"Set channel {channel} to {angle}")

    finally:
        kit.servo[channel].angle = None
        print("\nReleased on exit.")


if __name__ == "__main__":
    main()
