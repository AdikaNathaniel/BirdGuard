import sys
import termios
import tty
import time
from gpiozero import Servo, PWMOutputDevice

# --- PINS (BCM numbering) ---
PAN_PIN = 17    # physical pin 11
TILT_PIN = 27   # physical pin 13
LASER_PIN = 18  # physical pin 12 (hardware PWM capable)

# --- CALIBRATION ---
# gpiozero's Servo value range is -1.0 (min pulse) to 1.0 (max pulse), with
# 0.0 as the centre/stop position -- equivalent to Arduino's Servo.write(90)
# for a continuous-rotation servo.
PAN_STOP = 0.0
TILT_STOP = 0.0
SPEED_OFFSET = 0.3
NUDGE_TIME = 0.055  # seconds

pan_servo = Servo(PAN_PIN)
tilt_servo = Servo(TILT_PIN)
laser = PWMOutputDevice(LASER_PIN)

pan_servo.value = PAN_STOP
tilt_servo.value = TILT_STOP
laser.value = 0  # laser OFF


def stop_all():
    pan_servo.value = PAN_STOP
    tilt_servo.value = TILT_STOP
    print("Motors Stopped.")


def nudge(servo, speed, stop_value):
    servo.value = speed
    time.sleep(NUDGE_TIME)
    servo.value = stop_value
    print("Motors Stopped.")


def get_key():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def main():
    print("--- Pan-Tilt-Laser System (Pi native) ---")
    print("CONTINUOUS: W/S (Tilt), A/D (Pan)")
    print("NUDGE:      I/K (Tilt), J/L (Pan)")
    print("LASER:      O (On), F (Off)")
    print("STOP ALL:   Spacebar or X   |   Ctrl+C to quit")

    try:
        while True:
            cmd = get_key()

            if cmd == 'w':
                tilt_servo.value = TILT_STOP + SPEED_OFFSET
            elif cmd == 's':
                tilt_servo.value = TILT_STOP - SPEED_OFFSET
            elif cmd == 'a':
                pan_servo.value = PAN_STOP + SPEED_OFFSET
            elif cmd == 'd':
                pan_servo.value = PAN_STOP - SPEED_OFFSET

            elif cmd == 'i':
                nudge(tilt_servo, TILT_STOP + SPEED_OFFSET, TILT_STOP)
            elif cmd == 'k':
                nudge(tilt_servo, TILT_STOP - SPEED_OFFSET, TILT_STOP)
            elif cmd == 'j':
                nudge(pan_servo, PAN_STOP + SPEED_OFFSET, PAN_STOP)
            elif cmd == 'l':
                nudge(pan_servo, PAN_STOP - SPEED_OFFSET, PAN_STOP)

            elif cmd in ('o', 'O'):
                laser.value = 1
                print("Laser ON")
            elif cmd in ('f', 'F'):
                laser.value = 0
                print("Laser OFF")

            elif cmd in ('x', ' '):
                stop_all()

            elif cmd == '\x03':  # Ctrl+C
                break

    except KeyboardInterrupt:
        pass
    finally:
        stop_all()
        laser.value = 0
        pan_servo.close()
        tilt_servo.close()
        laser.close()
        print("\nShutdown complete.")


if __name__ == "__main__":
    main()
