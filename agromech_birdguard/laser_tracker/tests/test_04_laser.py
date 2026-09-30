import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import time
from config.settings import LASER_GPIO_PIN, LASER_ACTIVE_HIGH
from src.hardware.laser import Laser

laser = Laser(LASER_GPIO_PIN, LASER_ACTIVE_HIGH)
for i in range(5):
    laser.on()
    print(f"Laser ON ({i + 1}/5)")
    time.sleep(0.5)
    laser.off()
    time.sleep(0.5)
laser.close()
print("Laser test done.")