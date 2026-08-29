import board
import busio
from adafruit_pca9685 import PCA9685

# PCA9685 (16-channel, 12-bit PWM driver) over I2C:
# Pi 3.3V -> PCA9685 VCC (logic power)
# Pi GND  -> PCA9685 GND
# Pi GPIO2 (SDA, physical pin 3) -> PCA9685 SDA
# Pi GPIO3 (SCL, physical pin 5) -> PCA9685 SCL
#
# Laser module: PWM pin -> PCA9685 channel output, GND -> PCA9685 GND.
# The laser's own 12V power comes from its separate boosted supply, not
# the PCA9685 -- this channel only carries the on/off signal.
CHANNEL = 1  # PCA9685 output channel the laser's PWM pin is wired to (channel 0 is the motor)

i2c = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c)
pca.frequency = 50  # shared across all 16 channels on the chip -- matches the motor's frequency

pca.channels[CHANNEL].duty_cycle = 0  # laser OFF at startup


def set_laser(on: bool):
    pca.channels[CHANNEL].duty_cycle = 0xFFFF if on else 0
    print(f"Laser {'ON' if on else 'OFF'}")


def main():
    print("--- Pi -> PCA9685 -> Laser (PWM) ---")
    print("Send 'o' to turn laser ON, 'f' to turn laser OFF. Ctrl+C to quit.")

    try:
        while True:
            cmd = input("> ").strip().lower()

            if cmd == 'o':
                set_laser(True)
            elif cmd == 'f':
                set_laser(False)
            else:
                print("Invalid command. Use 'o' or 'f'.")

    except KeyboardInterrupt:
        pass
    finally:
        set_laser(False)
        print("\nShutdown complete.")


if __name__ == "__main__":
    main()
