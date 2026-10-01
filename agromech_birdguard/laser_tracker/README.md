# Raspberry Pi 5 Laser Tracker

YOLO person detection -> pan/tilt servo tracking -> laser on target.

## Hardware

- Raspberry Pi 5 (8 GB)
- Pi Camera v3 (CSI ribbon)
- PCA9685 16-ch PWM (I2C) -> pan servo ch0, tilt servo ch1
- Laser module switched by a logic-level MOSFET on GPIO18

## Wiring

### PCA9685 -> Pi

| PCA9685 | Pi 5 |
| --- | --- |
| VCC | 3V3 (pin 1) |
| GND | GND (pin 6) |
| SDA | GPIO2 (pin 3) |
| SCL | GPIO3 (pin 5) |

Servo power (V+ screw terminals): external 5-6 V supply. NEVER from the Pi 5 V pin.
Enable I2C: sudo raspi-config -> Interface Options -> I2C.
Verify with: i2cdetect -y 1  (should show 40)

### Laser MOSFET -> Pi

| MOSFET module | Pi 5 |
| --- | --- |
| SIG / gate | GPIO18 (pin 12) |
| GND | GND (any) |

The laser supply must share a ground with the Pi.

## Setup

sudo apt update
sudo apt install -y python3-picamera2 python3-opencv i2c-tools
python3 -m venv --system-site-packages ~/venvs/tracker
source ~/venvs/tracker/bin/activate
pip install -r requirements.txt

## Model

Download + export (run once, creates models/yolo11n_ncnn_model/):
yolo export model=yolo11n.pt format=ncnn

## Tests - run in this order

| Step | Command | Proves |
| --- | --- | --- |
| 1 | python tests/test_01_camera.py | camera frames at set FPS |
| 2 | python tests/test_02_detection.py | YOLO detects "person" |
| 3a | python tests/test_03a_servo.py | pan/tilt sweep |
| 3b | python tests/test_03b_servo.py | manual pan/tilt with arrow keys |
| 4 | python tests/test_04_laser.py | laser on/off |
| 5 | python tests/test_05_ai_laser.py | person => laser on |
| 6 | python tests/test_06_tracking.py | servos track, laser on target |

Full pipeline:  python main.py

## Safety

Aim the tilt range away from eyes/people. The tilt limits in config/settings.py
keep the laser pointed at a safe backdrop by default.