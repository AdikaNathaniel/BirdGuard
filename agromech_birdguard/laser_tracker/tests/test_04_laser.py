import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import time
from gpiozero import DigitalOutputDevice
from config.settings import (LASER_GPIO_PIN, LASER_ACTIVE_HIGH,
                             RELAY_GPIO_PIN, RELAY_ACTIVE_HIGH, RELAY_SETTLE_S)
from src.hardware.laser import Laser

# Relay cuts the laser's power supply; the laser pin is the trigger signal.
# Both start OFF and are always switched together.
relay = DigitalOutputDevice(RELAY_GPIO_PIN, active_high=RELAY_ACTIVE_HIGH,
                            initial_value=False)
laser = Laser(LASER_GPIO_PIN, LASER_ACTIVE_HIGH)


def laser_on():
    relay.on()                   # power first...
    time.sleep(RELAY_SETTLE_S)   # ...let the supply come up...
    laser.on()                   # ...then trigger


def laser_off():
    laser.off()                  # trigger off first, then cut power
    relay.off()


print(f"Laser trigger: GPIO{LASER_GPIO_PIN} | Power relay: GPIO{RELAY_GPIO_PIN}")
print("Type o + Enter = laser ON,  f + Enter = laser OFF,  q + Enter = quit")
try:
    while True:
        cmd = input("> ").strip().lower()
        if cmd == "o":
            laser_on()
            print("Laser ON (relay powered)")
        elif cmd == "f":
            laser_off()
            print("Laser OFF (relay unpowered)")
        elif cmd == "q":
            break
        elif cmd:
            print("Unknown command - use o, f or q")
except (KeyboardInterrupt, EOFError):
    print()
finally:
    laser_off()
    laser.close()
    relay.close()
print("Laser test done. Laser and relay OFF.")
