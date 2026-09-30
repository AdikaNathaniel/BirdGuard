"""Central configuration - edit values here."""
from pathlib import Path
import time

# Project root: /home/pi/Desktop/agromech_birdguard/laser_tracker
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------- Camera ----------
FRAME_RATE = 15                 # target capture frame rate (FPS)
CAMERA_RESOLUTION = (1280, 720)

# ---------- Model ----------
# Set absolute path for the model
MODEL_PATH = str(BASE_DIR / "models" / "yolo11n_ncnn_model")
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
LASER_GPIO_PIN = 18             # BCM numbering, drives MOSFET gate
LASER_ACTIVE_HIGH = True

# ---------- Tracking ----------
TRACK_GAIN = 30.0               # deg correction per unit normalized error
DEAD_ZONE = 0.05                # ignore error within 5% of frame center
