import time

from adafruit_servokit import ServoKit

# One-off tool for finding a continuous-rotation servo's true stop point.
# The library's default "center" (90 deg) assumes a generic calibration --
# individual continuous-rotation servos usually need their own stop value
# found empirically (or trimmed via a physical potentiometer, if present).
kit = ServoKit(channels=16)

PULSE_SECONDS = 0.4  # how long a "p<angle>" command holds before auto-releasing


def main():
    print("--- Servo Stop-Point Calibration ---")
    channel = int(input("Channel to test (e.g. 0 for pan, 4 for tilt): ").strip())
    print(f"Testing channel {channel}.")
    print("  <number>   -- set angle and hold it (e.g. 88, 90.5)")
    print(f"  p<number>  -- pulse to that angle for {PULSE_SECONDS}s, then auto-release")
    print("  t<number>  -- timed test: sends the angle immediately, then waits for you")
    print("               to press Enter the instant it reaches the target -- releases")
    print("               and prints the exact elapsed time")
    print("  r          -- release now (cut signal)")
    print("  q          -- quit")

    try:
        while True:
            cmd = input(f"[ch{channel}] angle> ").strip().lower()

            if cmd == 'q':
                break

            if cmd == 'r':
                kit.servo[channel].angle = None
                print("Released (signal cut).")
                continue

            if cmd.startswith('t'):
                try:
                    angle = float(cmd[1:])
                except ValueError:
                    print("Enter 't<number>', e.g. t180.")
                    continue
                angle = max(0.0, min(180.0, angle))
                start = time.monotonic()
                kit.servo[channel].angle = angle
                input(f"Sent {angle} to channel {channel} -- press Enter the instant "
                      f"it reaches the target position...")
                elapsed = time.monotonic() - start
                kit.servo[channel].angle = None
                print(f"Released. Elapsed time: {elapsed:.2f}s")
                continue

            pulse = cmd.startswith('p')
            value = cmd[1:] if pulse else cmd

            try:
                angle = float(value)
            except ValueError:
                print("Enter a number, 'p<number>' to pulse, 'r' to release, or 'q' to quit.")
                continue

            angle = max(0.0, min(180.0, angle))
            kit.servo[channel].angle = angle

            if pulse:
                print(f"Pulsing channel {channel} to {angle} for {PULSE_SECONDS}s...")
                time.sleep(PULSE_SECONDS)
                kit.servo[channel].angle = None
                print("Auto-released.")
            else:
                print(f"Set channel {channel} to {angle} (holding)")

    finally:
        kit.servo[channel].angle = None
        print("\nReleased on exit.")


if __name__ == "__main__":
    main()
