"""Central configuration - edit values here."""
from pathlib import Path
import time

# Project root: /home/pi/Desktop/agromech_birdguard/laser_tracker
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------- Camera ----------
FRAME_RATE = 15                 # target capture frame rate (FPS)
CAMERA_RESOLUTION = (1280, 720)  # final frame size (width, height), after rotation
CAMERA_ROTATION = 270           # clockwise degrees: 0, 90, 180 or 270
CAMERA_SATURATION = 1.5         # colour strength: 0 = greyscale, 1 = normal
CAMERA_BRIGHTNESS = 0.2         # -1.0 (dark) .. 1.0 (bright), 0 = normal

# ---------- Model ----------
# Set absolute path for the model
# YOLOv8n -- same model as pi-nano-laser/pi_person_detector_cpu.py
MODEL_PATH = str(BASE_DIR / "models" / "yolov8n.pt")
# Previous model (YOLO11n exported to NCNN), switch back by uncommenting:
# MODEL_PATH = str(BASE_DIR / "models" / "yolo11n_ncnn_model")
CONFIDENCE = 0.5
TARGET_CLASS = "person"
INFERENCE_SIZE = 640

# ---------- PCA9685 PWM ----------
PCA9685_I2C_ADDRESS = 0x40
PWM_FREQUENCY_HZ = 50
PAN_CHANNEL = 2
TILT_CHANNEL = 3
SERVO_MIN_US = 500              # pulse width at 0 deg
SERVO_MAX_US = 2500             # pulse width at 180 deg

PAN_MIN_DEG, PAN_MAX_DEG = 0, 180
TILT_MIN_DEG, TILT_MAX_DEG = 40, 140   # keeps laser pointed at backdrop
PAN_START_DEG = 90
TILT_START_DEG = 90

# ---------- Laser ----------
LASER_GPIO_PIN = 12             # BCM numbering: Pi GPIO12 -> Nano D2 -> Nano D6 -> laser PWM
LASER_ACTIVE_HIGH = True
RELAY_GPIO_PIN = 17             # BCM numbering, relay IN1 -> laser PSU positive
RELAY_ACTIVE_HIGH = True        # set False if the relay clicks on when the pin is LOW
RELAY_SETTLE_S = 0.1            # wait after powering the relay before triggering the laser
LASER_OFF_DELAY_S = 3.0         # keep laser on this long after the target was last seen
                                # (stops the relay clicking when detection flickers)

# ---------- Tracking ----------
TRACK_GAIN = 30.0               # deg correction per unit normalized error
DEAD_ZONE = 0.05                # ignore error within 5% of frame center
