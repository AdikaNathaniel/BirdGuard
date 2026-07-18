"""Direct Pi GPIO control for a PWM laser module (2-wire: PWM signal + GND).

Unlike the Nano bridge (nano-test/toggle_light.py), this drives the laser
straight from the Raspberry Pi's own GPIO pins -- no Arduino/serial link
involved. Wire the laser module's PWM pin to a Pi GPIO pin (default BCM18,
a hardware-PWM-capable pin) and its GND pin to any Pi ground pin.

Requires gpiozero (preinstalled on Raspberry Pi OS):
    pip install gpiozero

Usage as a library:
    from laser_control import LaserControl

    laser = LaserControl(pin=18)
    laser.on()          # full power
    laser.on(0.5)       # 50% duty cycle
    laser.off()
    laser.close()

    # or as a context manager
    with LaserControl(pin=18) as laser:
        laser.on()

Usage from the command line:
    python laser_control.py --pin 18 --on
    python laser_control.py --pin 18 --on --power 0.5
    python laser_control.py --pin 18 --off
    python laser_control.py --pin 18 --blink --on-time 0.2 --off-time 0.2
    python laser_control.py --pin 18 --interactive
        press 'o' -> laser on, 'f' -> laser off, 'q' -> quit
"""

import argparse
import sys
import time

from gpiozero import PWMOutputDevice

try:
    import termios
    import tty

    def _read_key() -> str:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

except ImportError:
    import msvcrt

    def _read_key() -> str:
        return msvcrt.getch().decode(errors="ignore")

DEFAULT_PIN = 18       # BCM numbering, hardware PWM capable
DEFAULT_FREQUENCY = 1000  # Hz


class LaserControl:
    """Drives a PWM laser module on a single Pi GPIO pin."""

    def __init__(self, pin: int = DEFAULT_PIN, frequency: int = DEFAULT_FREQUENCY):
        self.pin = pin
        self.device = PWMOutputDevice(pin, frequency=frequency, initial_value=0)

    def on(self, power: float = 1.0):
        """Turn the laser on at the given duty cycle (0.0-1.0)."""
        if not 0.0 <= power <= 1.0:
            raise ValueError("power must be between 0.0 and 1.0")
        self.device.value = power

    def off(self):
        self.device.value = 0

    def set_power(self, power: float):
        self.on(power)

    def blink(self, on_time: float = 0.5, off_time: float = 0.5, power: float = 1.0, n: int = None):
        """Blink the laser. n=None blinks forever until interrupted."""
        count = 0
        try:
            while n is None or count < n:
                self.on(power)
                time.sleep(on_time)
                self.off()
                time.sleep(off_time)
                count += 1
        except KeyboardInterrupt:
            self.off()

    def interactive(self, power: float = 1.0):
        """Read single keypresses: 'o' turns the laser on, 'f' turns it off, 'q' quits."""
        print("Interactive mode: 'o'=on, 'f'=off, 'q'=quit")
        try:
            while True:
                key = _read_key().lower()
                if key == "o":
                    self.on(power)
                    print(f"Laser ON (GPIO{self.pin}, power={power})")
                elif key == "f":
                    self.off()
                    print(f"Laser OFF (GPIO{self.pin})")
                elif key in ("q", "\x03"):  # 'q' or Ctrl+C
                    break
        except KeyboardInterrupt:
            pass
        finally:
            self.off()
            print("\nExiting. Laser OFF.")

    def close(self):
        self.off()
        self.device.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    parser = argparse.ArgumentParser(description="Direct Pi GPIO control for a PWM laser module.")
    parser.add_argument("--pin", type=int, default=DEFAULT_PIN, help=f"BCM GPIO pin wired to the laser's PWM input (default: {DEFAULT_PIN})")
    parser.add_argument("--frequency", type=int, default=DEFAULT_FREQUENCY, help=f"PWM frequency in Hz (default: {DEFAULT_FREQUENCY})")
    parser.add_argument("--power", type=float, default=1.0, help="Duty cycle 0.0-1.0 when turning on (default: 1.0)")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--on", action="store_true", help="Turn the laser on and hold until Ctrl+C")
    group.add_argument("--off", action="store_true", help="Turn the laser off")
    group.add_argument("--blink", action="store_true", help="Blink the laser until Ctrl+C")
    group.add_argument("--interactive", action="store_true", help="Press 'o' to turn on, 'f' to turn off, 'q' to quit")

    parser.add_argument("--on-time", type=float, default=0.5, help="Blink on-duration in seconds (default: 0.5)")
    parser.add_argument("--off-time", type=float, default=0.5, help="Blink off-duration in seconds (default: 0.5)")

    args = parser.parse_args()

    try:
        with LaserControl(pin=args.pin, frequency=args.frequency) as laser:
            if args.off:
                laser.off()
                print(f"Laser OFF (GPIO{args.pin})")
            elif args.on:
                laser.on(args.power)
                print(f"Laser ON (GPIO{args.pin}, power={args.power}). Ctrl+C to stop.")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    pass
            elif args.blink:
                print(f"Blinking laser (GPIO{args.pin}, power={args.power}). Ctrl+C to stop.")
                laser.blink(on_time=args.on_time, off_time=args.off_time, power=args.power)
            elif args.interactive:
                laser.interactive(power=args.power)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
