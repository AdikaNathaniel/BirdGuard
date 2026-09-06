# Imports the Adafruit library that talks to the PCA9685 board over I2C
# and exposes each of its 16 output channels as a simple `.angle`
# property -- setting `kit.servo[N].angle = X` sends the right PWM pulse
# width for that channel to hold a standard hobby servo at X degrees.
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
# This is the ONLY servo used by this script, so it's the only channel
# number that matters here -- change it if the servo is moved to a
# different channel on the board.
TILT_CHANNEL = 8

# The angle the servo returns to on startup and when 'c' is pressed --
# treated as the servo's neutral/resting position.
CENTER_ANGLE = 90

# Fixed target angles, not step increments -- one 'up' or 'down' command
# jumps straight to the matching angle below, rather than stepping there
# gradually across several commands. Inverted relative to raw angle for
# how this servo is mounted: confirmed by testing that a *lower* angle
# (110) physically tilts it up, and a *higher* angle (140) physically
# tilts it down. If the servo is ever remounted the other way round,
# these two values are the only thing that needs swapping.
UP_ANGLE = 110
DOWN_ANGLE = 140

# Hard safety bounds matching the physical limits of a standard servo --
# every angle passed to move_to() gets clamped inside this range no
# matter what, so a typo or a future bug can never command an angle the
# hardware can't actually reach.
MIN_ANGLE = 0
MAX_ANGLE = 180

# Constructs the driver object for the PCA9685 board itself (all 16
# channels), auto-detecting it on the I2C bus at its default address
# (0x40) -- this is the same object `sudo i2cdetect -y 1` would have
# shown responding at that address.
kit = ServoKit(channels=16)


def move_to(angle):
    """Moves the tilt servo to `angle` degrees, after clamping it into range."""
    # Clamped to the servo's full physical range as a hard safety limit.
    angle = max(MIN_ANGLE, min(MAX_ANGLE, angle))
    # Writing to .angle immediately updates the PWM signal on this
    # channel -- the servo starts physically moving toward this angle as
    # soon as this line runs, with no further action needed.
    kit.servo[TILT_CHANNEL].angle = angle
    print(f"Tilt angle set to: {angle}")


def stop():
    """Cuts the PWM signal to the servo entirely, letting it go limp."""
    kit.servo[TILT_CHANNEL].angle = None  # cuts the PWM signal -- motor goes limp/unpowered
    print("Tilt stopped (released, no signal)")


def main():
    # Print the available commands once up front so the operator doesn't
    # have to remember them mid-session.
    print("--- Pi -> PCA9685 Tilt Test (I2C) ---")
    print(f"Channel {TILT_CHANNEL}, starting centered at {CENTER_ANGLE} degrees")
    print(
        f"'up' moves straight to {UP_ANGLE}, 'down' moves straight to {DOWN_ANGLE}, "
        "'c' re-centers, 's' releases. Ctrl+C to quit."
    )

    # Start from a known, predictable position every time the script
    # runs, rather than trusting whatever angle the servo happened to be
    # left at by a previous run.
    move_to(CENTER_ANGLE)

    try:
        # Reads one typed command at a time and loops forever until the
        # user presses Ctrl+C -- there's no other way to exit this loop.
        while True:
            # .strip() removes any accidental leading/trailing whitespace
            # (e.g. from copy-pasting a command), .lower() means 'UP',
            # 'Up', and 'up' are all treated the same.
            cmd = input("> ").strip().lower()

            if cmd == 'up':
                move_to(UP_ANGLE)
            elif cmd == 'down':
                move_to(DOWN_ANGLE)
            elif cmd == 'c':
                move_to(CENTER_ANGLE)
            elif cmd == 's':
                stop()
            else:
                # Anything that isn't one of the four known commands
                # above -- reprints the usage hint rather than crashing
                # or silently doing nothing.
                print("Invalid command. Use 'up', 'down', 'c' (re-center), or 's' (release).")

    except KeyboardInterrupt:
        # Ctrl+C raises this -- caught here (rather than letting it print
        # a traceback) so the servo still gets released cleanly by the
        # `finally` block below before the script exits.
        pass
    finally:
        # Always releases the servo on the way out, whether the loop
        # ended via Ctrl+C or (in principle) any other exit path -- so
        # the motor never keeps drawing current or holding a position
        # after the script has stopped.
        stop()
        print("\nShutdown complete.")


# Only runs main() when this file is executed directly (e.g.
# `python pi_tilt_test.py`), not if it were ever imported as a module
# from another script.
if __name__ == "__main__":
    main()
