import argparse
import signal
import time

from adafruit_servokit import ServoKit

# One-off tool for finding a continuous-rotation servo's true stop point.
# The library's default "center" (90 deg) assumes a generic calibration --
# individual continuous-rotation servos usually need their own stop value
# found empirically (or trimmed via a physical potentiometer, if present).
#
# Also doubles as the "field of view" sweep the mobile app's Settings page
# triggers: run with --channel/--angle/--seconds to start a recurring
# oscillation non-interactively (used by the backend over SSH), instead of
# the interactive prompt below (used for manual calibration).
kit = ServoKit(channels=16)

PULSE_SECONDS = 0.4  # how long a "p<angle>" command holds before auto-releasing

# Same reasoning as pi_person_detector_cpu_offset.py: SIGTERM (what the
# backend's STOP_SERVO_SWEEP command sends via `pkill`) kills the process
# immediately by default, skipping cleanup -- route it through the same
# KeyboardInterrupt path used for Ctrl+C so the servo always gets released
# on stop, not left holding whatever angle it was mid-sweep.
def _handle_sigterm(signum, frame):
    raise KeyboardInterrupt


signal.signal(signal.SIGTERM, _handle_sigterm)


def recurring_sweep(channel, angle, duration):
    """Alternates the given channel between `angle` and its mirror on the
    other side of center (180 - angle), each held for `duration` seconds,
    repeating until interrupted (Ctrl+C or SIGTERM). Always releases the
    servo signal on the way out, however the loop ends."""
    angle = max(0.0, min(180.0, angle))
    mirror_angle = 180.0 - angle

    print(f"Recurring: {angle} <-> {mirror_angle}, {duration}s each. "
          f"Ctrl+C to stop.")
    current = angle
    try:
        while True:
            kit.servo[channel].angle = current
            print(f"  -> {current}")
            time.sleep(duration)
            current = mirror_angle if current == angle else angle
    except KeyboardInterrupt:
        print("\nRecurring stopped.")
    finally:
        kit.servo[channel].angle = None
        print("Released.")


def main():
    parser = argparse.ArgumentParser(description="Servo calibration / field-of-view sweep tool.")
    parser.add_argument("--channel", type=int, help="PCA9685 channel to drive (e.g. 0 for pan)")
    parser.add_argument("--angle", type=float, help="Angle (0-180) for a non-interactive recurring sweep")
    parser.add_argument("--seconds", type=float, help="Seconds to hold each side of the sweep")
    args = parser.parse_args()

    # If all three are given, skip the interactive prompt entirely and run
    # the sweep directly -- this is the path the backend uses (it can't
    # answer an interactive `input()` prompt over a one-shot SSH command).
    if args.channel is not None and args.angle is not None and args.seconds is not None:
        recurring_sweep(args.channel, args.angle, args.seconds)
        return

    print("--- Servo Stop-Point Calibration ---")
    channel = int(input("Channel to test (e.g. 0 for pan, 4 for tilt): ").strip())
    print(f"Testing channel {channel}.")
    print("  <number>   -- set angle and hold it (e.g. 88, 90.5)")
    print(f"  p<number>  -- pulse to that angle for {PULSE_SECONDS}s, then auto-release")
    print("  p<number>,<seconds> -- pulse to that angle for an exact duration you choose")
    print("               (e.g. p180,1.77), then auto-release")
    print("  pr<number>,<seconds> -- recurring: alternates between that angle and its")
    print("               mirror on the other side of center, each held for <seconds>,")
    print("               repeating until you press Ctrl+C (e.g. pr90,0.61)")
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
                # `t<angle>`: measures real-world rotation time by starting
                # a timer the instant the command is sent, then blocking
                # on `input()` until the operator confirms (by pressing
                # Enter) that the servo has visibly reached the target --
                # used to build the angle-to-duration calibration data
                # (e.g. 90 deg -> 0.61s) for timed-pulse control.
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

            if cmd.startswith('pr'):
                # `pr<angle>,<seconds>`: same recurring sweep as
                # recurring_sweep() above, entered interactively. Center
                # (90) is assumed as the mirror point since that's the
                # standard servo-angle midpoint; if this servo's real stop
                # point turns out to be elsewhere (see the plain stop-point
                # sweep below), the two halves of the swing won't be
                # perfectly symmetric in practice.
                value = cmd[2:]
                if ',' not in value:
                    print("Enter 'pr<angle>,<seconds>', e.g. pr90,0.61")
                    continue
                angle_str, duration_str = value.split(',', 1)
                try:
                    angle = float(angle_str)
                    duration = float(duration_str)
                except ValueError:
                    print("Enter 'pr<angle>,<seconds>', e.g. pr90,0.61")
                    continue

                # recurring_sweep() has its own try/finally releasing the
                # servo and its own KeyboardInterrupt handling scoped to
                # just the sweep, so Ctrl+C here returns to this prompt
                # rather than exiting the whole tool.
                recurring_sweep(channel, angle, duration)
                continue

            # `p<angle>` or `p<angle>,<seconds>`: pulse mode -- move then
            # auto-release after a duration, instead of holding forever.
            pulse = cmd.startswith('p')
            value = cmd[1:] if pulse else cmd

            # An explicit ",<seconds>" suffix overrides the default pulse
            # duration -- lets a specific measured timing (from a prior
            # `t<angle>` test) be replayed exactly, e.g. p180,1.77.
            pulse_seconds = PULSE_SECONDS
            if pulse and ',' in value:
                value, duration_str = value.split(',', 1)
                try:
                    pulse_seconds = float(duration_str)
                except ValueError:
                    print("Duration must be a number, e.g. p180,1.77")
                    continue

            try:
                angle = float(value)
            except ValueError:
                print("Enter a number, 'p<number>' to pulse, 'r' to release, or 'q' to quit.")
                continue

            angle = max(0.0, min(180.0, angle))
            kit.servo[channel].angle = angle

            if pulse:
                print(f"Pulsing channel {channel} to {angle} for {pulse_seconds}s...")
                time.sleep(pulse_seconds)
                kit.servo[channel].angle = None
                print("Auto-released.")
            else:
                # Plain `<angle>` with no prefix: set and hold indefinitely
                # until the next command (used for the manual stop-point
                # sweep -- try values close to 90 and watch for the one
                # that actually stops the motor).
                print(f"Set channel {channel} to {angle} (holding)")

    finally:
        kit.servo[channel].angle = None
        print("\nReleased on exit.")


if __name__ == "__main__":
    main()
