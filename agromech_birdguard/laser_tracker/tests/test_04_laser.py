import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from config.settings import (LASER_GPIO_PIN, LASER_ACTIVE_HIGH,
                             RELAY_GPIO_PIN, RELAY_ACTIVE_HIGH, RELAY_SETTLE_S)
from src.hardware.laser import Laser

laser = Laser(LASER_GPIO_PIN, LASER_ACTIVE_HIGH,
              RELAY_GPIO_PIN, RELAY_ACTIVE_HIGH, RELAY_SETTLE_S)

print(f"Laser trigger: GPIO{LASER_GPIO_PIN} | Power relay: GPIO{RELAY_GPIO_PIN}")
print("Type o + Enter = laser ON,  f + Enter = laser OFF,  q + Enter = quit")
try:
    while True:
        cmd = input("> ").strip().lower()
        if cmd == "o":
            laser.on()
            print("Laser ON (relay powered)")
        elif cmd == "f":
            laser.off()
            print("Laser OFF (relay unpowered)")
        elif cmd == "q":
            break
        elif cmd:
            print("Unknown command - use o, f or q")
except (KeyboardInterrupt, EOFError):
    print()
finally:
    laser.close()
print("Laser test done. Laser and relay OFF.")
