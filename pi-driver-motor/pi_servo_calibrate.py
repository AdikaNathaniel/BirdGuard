import argparse
import select
import signal
import sys
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


def _stdin_ready(timeout):
    """Non-blocking check for a pending line on stdin -- lets
    run_pulse_sequence() below watch for the 'r' stop command in between
    (and during) pulses without pausing playback to block on input()."""
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    return bool(ready)


def read_pulse_sequence():
    """Collects a sequence of (angle, duration) pairs, each typed the same
    way as a single pulse command (`p<angle>,<seconds>`), one per line,
    until the user types 'done'."""
    sequence = []
    print("Enter each step as p<angle>,<seconds> (e.g. p90,0.70). Type 'done' when finished.")
    while True:
        entry = input("  step> ").strip().lower()
        if entry == 'done':
            break

        value = entry[1:] if entry.startswith('p') else entry
        if ',' not in value:
            print("Enter in the form p<angle>,<seconds>, e.g. p90,0.70 (or 'done' to finish).")
            continue
        angle_str, duration_str = value.split(',', 1)
        try:
            angle = float(angle_str)
            duration = float(duration_str)
        except ValueError:
            print("Angle and seconds must both be numbers, e.g. p90,0.70")
            continue

        angle = max(0.0, min(180.0, angle))
        sequence.append((angle, duration))
        print(f"  Added step {len(sequence)}: angle={angle}, hold={duration}s.")

    return sequence


def run_pulse_sequence(channel, sequence, interactive=True):
    """Cycles through the given [(angle, duration), ...] steps forever --
    pulsing to each angle, holding for its duration, then auto-releasing
    before moving to the next, exactly like a single p<angle>,<seconds>
    command -- looping back to the start once the sequence ends.

    When `interactive` (the manual `recur` command), stops when the user
    types 'r' and presses Enter -- checked continuously via _stdin_ready,
    not just between steps, so it can interrupt mid-hold too.

    When not `interactive` (the mobile app's Settings page, launched
    non-interactively over SSH with stdin redirected from /dev/null),
    stdin is never going to receive real input -- select() on a
    /dev/null-backed stdin reports "ready" immediately and reading it
    returns EOF forever, which would busy-loop straight through every
    hold duration instead of actually waiting. So this mode just sleeps
    normally instead, and relies entirely on the SIGTERM handler above
    (wired up to the backend's STOP_SERVO_SWEEP command) to stop it."""
    if not sequence:
        print("No steps in the sequence -- nothing to run.")
        return

    if interactive:
        print(f"Recurring sequence ({len(sequence)} step(s)). Type 'r' + Enter at any time to stop.")
    else:
        print(f"Recurring sequence ({len(sequence)} step(s)). Stop via SIGTERM (the backend's stop action).")

    try:
        while True:
            for angle, duration in sequence:
                print(f"  -> pulsing to {angle} for {duration}s...")
                kit.servo[channel].angle = angle

                if not interactive:
                    time.sleep(duration)
                    kit.servo[channel].angle = None
                    continue

                remaining = duration
                stop_requested = False
                while remaining > 0:
                    slice_time = min(0.1, remaining)
                    if _stdin_ready(slice_time):
                        if sys.stdin.readline().strip().lower() == 'r':
                            stop_requested = True
                            break
                    remaining -= slice_time

                kit.servo[channel].angle = None  # auto-release, same as a plain pulse

                if stop_requested:
                    print("Recurring sequence stopped.")
                    return
    finally:
        kit.servo[channel].angle = None
        print("Released.")


def main():
    parser = argparse.ArgumentParser(description="Servo calibration / field-of-view sweep tool.")
    parser.add_argument("--channel", type=int, help="PCA9685 channel to drive (e.g. 0 for pan)")
    parser.add_argument("--angle", type=float, help="Angle (0-180) for a non-interactive mirror sweep")
    parser.add_argument("--seconds", type=float, help="Seconds to hold each side of the mirror sweep")
    parser.add_argument("--angle1", type=float, help="Step 1 angle (0-180) for a non-interactive two-step sequence")
    parser.add_argument("--seconds1", type=float, help="Step 1 hold duration in seconds")
    parser.add_argument("--angle2", type=float, help="Step 2 angle (0-180) for a non-interactive two-step sequence")
    parser.add_argument("--seconds2", type=float, help="Step 2 hold duration in seconds")
    args = parser.parse_args()

    # If all five are given, run the two-step recurring sequence directly,
    # non-interactively -- this is the path the mobile app's Settings page
    # uses (the backend launches this over a one-shot SSH command, which
    # can't answer an interactive `input()` prompt).
    two_step_args = (args.channel, args.angle1, args.seconds1, args.angle2, args.seconds2)
    if all(v is not None for v in two_step_args):
        try:
            run_pulse_sequence(
                args.channel,
                [(args.angle1, args.seconds1), (args.angle2, args.seconds2)],
                interactive=False,
            )
        except KeyboardInterrupt:
            pass
        return

    # Older single-angle mirror sweep, kept for backward compatibility --
    # if all three of these are given instead, skip the interactive
    # prompt and run that directly.
    if args.channel is not None and args.angle is not None and args.seconds is not None:
        try:
            recurring_sweep(args.channel, args.angle, args.seconds)
        except KeyboardInterrupt:
            pass
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
    print("  recur      -- recurring sequence: enter your own list of p<angle>,<seconds>")
    print("               steps (e.g. p90,0.70 then p140,0.90), then it cycles through")
    print("               them forever -- pulse, auto-release, next step, repeat from")
    print("               the start -- until you type 'r'")
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

            if cmd == 'recur':
                sequence = read_pulse_sequence()
                run_pulse_sequence(channel, sequence)
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
