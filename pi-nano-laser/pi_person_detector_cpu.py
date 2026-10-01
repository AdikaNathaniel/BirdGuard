import time
import json
import socket
import os
import signal
import subprocess
import threading
import cv2
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from picamera2 import Picamera2
from ultralytics import YOLO
from pymongo import MongoClient
from adafruit_servokit import ServoKit

# Python only auto-converts SIGINT (Ctrl+C) into a catchable KeyboardInterrupt
# -- SIGTERM (what `pkill`/the backend's STOP_DETECTOR command sends) kills
# the process immediately by default, skipping the try/finally cleanup below.
# Route it through the same path so the laser always gets switched off and
# the servos always get re-centered/released on stop, not just on Ctrl+C.
def _handle_sigterm(signum, frame):
    raise KeyboardInterrupt


signal.signal(signal.SIGTERM, _handle_sigterm)

# --- CONFIG ---
# Central tunables for the whole script: which GPIO fires the laser, where
# detection events get broadcast, what counts as a "person" detection, and
# the camera/recording settings. Kept together at the top so none of this
# needs hunting through the rest of the file to adjust.
LASER_GPIO = 12               # Pi GPIO12 -> Nano D2 -> Nano D6 -> laser
POWER_RELAY_GPIO = 17         # Pi GPIO17 -> 2-channel relay IN1 -> laser PSU positive wire.
                               # Cuts the laser's power supply entirely (not just the trigger
                               # signal) whenever no person is being detected, for energy
                               # saving and as a true hardware-level off between detections
                               # rather than just holding the Nano's trigger line low. Follows
                               # the exact same on/off timing as LASER_GPIO below -- both are
                               # driven together at every transition, never independently.
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
TARGET_CLASS = "person"
CONFIDENCE_THRESHOLD = 0.5
LASER_OFF_DELAY = 3.0         # Seconds to keep laser on after last detection
FRAME_WIDTH = 1280            # final frame size, after rotation
FRAME_HEIGHT = 720
VIDEO_FPS = 30
PREVIEW_PORT = 8080           # browse http://<pi-ip>:8080/ for a live MJPEG preview

# --- CAMERA ORIENTATION + COLOUR ---
# The camera is mounted on its side. For 90/270 the sensor is read as a tall
# centre strip and then turned upright, so the frame is still a full-quality
# FRAME_WIDTH x FRAME_HEIGHT landscape picture rather than a narrow portrait.
CAMERA_ROTATION = 270         # clockwise degrees: 0, 90, 180 or 270
CAMERA_SATURATION = 1.5       # colour strength: 0 = greyscale, 1 = normal
CAMERA_BRIGHTNESS = 0.2       # -1.0 (dark) .. 1.0 (bright), 0 = normal

# --- PAN/TILT TRACKING (PCA9685 over I2C) ---
# Values from agromech_birdguard/laser_tracker/config/settings.py, verified
# there with the servo sweep / manual servo / tracking tests.
PCA9685_I2C_ADDRESS = 0x40
PAN_CHANNEL = 2
TILT_CHANNEL = 3
SERVO_MIN_US = 500            # pulse width at 0 deg
SERVO_MAX_US = 2500           # pulse width at 180 deg
PAN_MIN_DEG, PAN_MAX_DEG = 0, 180
TILT_MIN_DEG, TILT_MAX_DEG = 40, 140   # keeps laser pointed at backdrop
PAN_START_DEG = 90
TILT_START_DEG = 90
# The camera is fixed and only the laser moves, so each pixel always maps to
# the same pan/tilt angles. Every frame the angles are recalculated fresh
# from the target's centre (nothing accumulates, so it can't drift to a limit):
#   err_x = (cx - FRAME_WIDTH/2) / (FRAME_WIDTH/2)     -1 left .. +1 right
#   err_y = (cy - FRAME_HEIGHT/2) / (FRAME_HEIGHT/2)   -1 top  .. +1 bottom
#   pan   = PAN_AT_FRAME_CENTER  + err_x * PAN_DEG_TO_FRAME_EDGE
#   tilt  = TILT_AT_FRAME_CENTER + err_y * TILT_DEG_TO_FRAME_EDGE
# Values estimated from the first 9-point calibration run (right-edge points
# excluded as mis-clicks). A negative DEG_TO_FRAME_EDGE flips that direction.
PAN_AT_FRAME_CENTER = 74.5    # servo pan that puts the dot at the picture centre
TILT_AT_FRAME_CENTER = 109.0  # servo tilt that puts the dot at the picture centre
PAN_DEG_TO_FRAME_EDGE = -36.0 # pan change from centre to right edge (+ = pan up moves right)
                               # Negative: flipped after a live test showed the pan servo
                               # turning away from the person with +36.
TILT_DEG_TO_FRAME_EDGE = 36.0 # tilt change from centre to bottom edge (+ = tilt up moves down)
# If a good calibration from calibrate_laser_aim.py exists, it is used
# instead of the simple centre/edge numbers above.
CALIBRATION_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "laser_aim_calibration.json")
AIM_SMOOTHING = 0.5           # 0..1 -- fraction of the way to the new aim per frame
                               # (1 = jump straight there, lower = steadier but slower)
MIN_MOVE_DEG = 1.0            # skip moves smaller than this (stops servo buzzing)
MAX_CALIBRATION_ERROR_DEG = 3.0  # ignore a calibration file with a worse fit than this
RETURN_HOME_DELAY = 3.0       # seconds without a person before servos re-center
# Constant aim correction (degrees) added to every aim. Measured live with
# `--adjust` on 2026-10-01 (person target): pan +30.5, tilt -16.0.
AIM_OFFSET_PAN_DEG = 30.5
AIM_OFFSET_TILT_DEG = -16.0
# A newer `--adjust` result saved with `x` goes to this file and *replaces*
# the two values above (it is never added on top of them).
AIM_OFFSET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "laser_aim_offset.json")
ADJUST_STEPS_DEG = [0.5, 1.0, 2.0, 5.0]   # step sizes in --adjust mode

# Same Atlas cluster/database the NestJS backend uses -- the Pi writes
# detection events directly, the backend's detection-service only reads.
# Standard (non-SRV) connection string -- the mongodb+srv:// form needs a
# DNS TXT record lookup that this network's DNS doesn't handle correctly
# (SRV lookups work fine, TXT lookups time out even against 8.8.8.8),
# so the host list is spelled out explicitly to avoid that lookup entirely.
MONGODB_URI = os.environ.get(
    "MONGODB_URI",
    "mongodb://adikanathaniel4_db_user:oLAjlIr1kRY31LZQ@"
    "ac-w0spglj-shard-00-00.u4du6ig.mongodb.net:27017,"
    "ac-w0spglj-shard-00-01.u4du6ig.mongodb.net:27017,"
    "ac-w0spglj-shard-00-02.u4du6ig.mongodb.net:27017/"
    "birdguard?ssl=true&replicaSet=atlas-8gkcz2-shard-0&authSource=admin&appName=Cluster0",
)

# Session folder -- every run gets its own timestamped directory so
# recordings/snapshots from different runs never overwrite each other.
session_name = datetime.now().strftime("session_%Y-%m-%d_%H-%M-%S")
SESSION_DIR = f"/home/pi/birdguard-test/{session_name}"
DETECTIONS_DIR = f"{SESSION_DIR}/detections"
VIDEO_PATH = f"{SESSION_DIR}/recording.avi"
os.makedirs(DETECTIONS_DIR, exist_ok=True)


def set_gpio(pin: int, high: bool):
    # Drives a pin via the `pinctrl` CLI tool rather than a Python GPIO
    # library. `dh`/`dl` = "digital high" / "digital low" in pinctrl's own
    # syntax. Shared by both LASER_GPIO (read by the Arduino Nano, D2) and
    # POWER_RELAY_GPIO (drives the relay module directly) -- same call,
    # different pin number.
    state = "dh" if high else "dl"
    try:
        subprocess.run(["pinctrl", "set", str(pin), "op", state], check=True)
    except Exception as e:
        print(f"pinctrl call failed (GPIO{pin}): {e}")


def set_laser_power(high: bool):
    # Toggles the laser's trigger signal and its power-relay together --
    # every call site in this file wants both at once, so callers never
    # have to remember to drive both pins themselves.
    set_gpio(LASER_GPIO, high)
    set_gpio(POWER_RELAY_GPIO, high)


# --- CAMERA ROTATION ---
# Clockwise rotation in degrees -> OpenCV rotate code
_ROTATE_CODES = {
    90: cv2.ROTATE_90_CLOCKWISE,
    180: cv2.ROTATE_180,
    270: cv2.ROTATE_90_COUNTERCLOCKWISE,
}


def centre_crop(picam2, size):
    # Largest centred sensor area with the same shape as `size`, so the
    # sideways (tall) capture is cropped rather than squashed/stretched.
    max_x, max_y, max_w, max_h = picam2.camera_controls["ScalerCrop"][1]
    aspect = size[0] / size[1]
    crop_w, crop_h = max_w, max_h
    if max_w / max_h > aspect:
        crop_w = int(max_h * aspect)
    else:
        crop_h = int(max_w / aspect)
    return (max_x + (max_w - crop_w) // 2, max_y + (max_h - crop_h) // 2,
            crop_w, crop_h)


def rotate_frame(frame):
    if CAMERA_ROTATION in _ROTATE_CODES:
        return cv2.rotate(frame, _ROTATE_CODES[CAMERA_ROTATION])
    return frame


# --- PAN/TILT TRACKING ---
def pixel_terms(x, y, quadratic):
    # Must match pixel_terms() in calibrate_laser_aim.py. Pixels are scaled
    # to roughly -1..1; the quadratic terms (8+ calibration points) capture
    # the curve from pan and tilt interacting on the pan/tilt head.
    u = (x - FRAME_WIDTH / 2) / (FRAME_WIDTH / 2)
    v = (y - FRAME_HEIGHT / 2) / (FRAME_HEIGHT / 2)
    return [u, v, 1.0] + ([u * u, v * v, u * v] if quadratic else [])


def load_calibration(path=CALIBRATION_PATH):
    # Returns (pan_coef, tilt_coef), or None to use the simple centre/edge
    # mapping (PAN_AT_FRAME_CENTER etc.) when there is no usable calibration.
    if not os.path.exists(path):
        print(f"No aim calibration at {path} -- using simple centre/edge mapping.")
        return None
    with open(path) as f:
        cal = json.load(f)
    if cal.get("version") != 2:
        print("Aim calibration is from an older calibrate_laser_aim.py -- ignoring it, "
              "using simple centre/edge mapping.")
        return None
    if (cal.get("frame_size") != [FRAME_WIDTH, FRAME_HEIGHT]
            or cal.get("camera_rotation") != CAMERA_ROTATION):
        print("Aim calibration was made with a different frame size/rotation -- ignoring it, "
              "using simple centre/edge mapping.")
        return None
    rms = cal.get("rms_error_deg", {})
    if max(rms.get("pan", 99), rms.get("tilt", 99)) > MAX_CALIBRATION_ERROR_DEG:
        print(f"Aim calibration fit error too high (pan {rms.get('pan', 99):.1f} / tilt "
              f"{rms.get('tilt', 99):.1f} deg) -- ignoring it, using simple centre/edge mapping.")
        return None
    print(f"Aim calibration loaded ({len(cal.get('points', []))} points, "
          f"fit error pan {rms.get('pan', 0):.2f} / tilt {rms.get('tilt', 0):.2f} deg)")
    return cal["pan"], cal["tilt"]


def load_aim_offset(path=AIM_OFFSET_PATH):
    # Saved --adjust file replaces the in-code defaults (never added to them)
    if not os.path.exists(path):
        print(f"Aim offset (in code): pan {AIM_OFFSET_PAN_DEG:+.1f} / tilt {AIM_OFFSET_TILT_DEG:+.1f} deg")
        return AIM_OFFSET_PAN_DEG, AIM_OFFSET_TILT_DEG
    with open(path) as f:
        off = json.load(f)
    print(f"Aim offset (from {os.path.basename(path)}): "
          f"pan {off['pan']:+.1f} / tilt {off['tilt']:+.1f} deg")
    return float(off["pan"]), float(off["tilt"])


def save_aim_offset(pan, tilt, path=AIM_OFFSET_PATH):
    with open(path, "w") as f:
        json.dump({"pan": pan, "tilt": tilt,
                   "saved_at": datetime.now().isoformat(timespec="seconds")}, f, indent=2)
    print(f"\n>>> Saved aim offset pan {pan:+.1f} / tilt {tilt:+.1f} deg -> {path}")


class KeyReader:
    """Single key presses from the terminal (works over SSH), read on a thread.

    Puts the terminal in cbreak mode (no Enter needed, Ctrl+C still works)
    and restores it on close.
    """

    def __init__(self):
        import queue, sys, termios, tty
        self._sys, self._termios = sys, termios
        self.keys = queue.Queue()
        self._fd = sys.stdin.fileno()
        self._old = termios.tcgetattr(self._fd)
        tty.setcbreak(self._fd)
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while True:
            ch = self._sys.stdin.read(1)
            if not ch:
                return
            self.keys.put(ch)

    def get(self):
        # Next pending key, or None
        return None if self.keys.empty() else self.keys.get_nowait()

    def close(self):
        self._termios.tcsetattr(self._fd, self._termios.TCSADRAIN, self._old)


class PanTiltTracker:
    """Aims the laser straight at a pixel (fixed camera, only the laser moves).

    Each frame computes absolute target angles fresh from the person's pixel
    position -- from calibrate_laser_aim.py's fit if there is a good one,
    otherwise the simple centre/edge mapping -- so nothing builds
    up over time and it can't drift off to a range limit. With no person for
    RETURN_HOME_DELAY seconds it re-centers.

    The PCA9685 gives no position feedback, so `pan`/`tilt` are the last
    commanded angles -- the only record of where the servos are.
    """

    def __init__(self, calibration, offset=(0.0, 0.0)):
        self.calibration = calibration
        # Constant correction added to every aim (measured with --adjust)
        self.offset_pan, self.offset_tilt = offset
        self.kit = ServoKit(channels=16, address=PCA9685_I2C_ADDRESS)
        for ch in (PAN_CHANNEL, TILT_CHANNEL):
            self.kit.servo[ch].set_pulse_width_range(SERVO_MIN_US, SERVO_MAX_US)
        self.at_home = False
        self.center()

    def center(self):
        self.move_to(PAN_START_DEG, TILT_START_DEG)
        self.at_home = True

    def move_to(self, pan, tilt):
        self.pan = max(PAN_MIN_DEG, min(PAN_MAX_DEG, pan))
        self.tilt = max(TILT_MIN_DEG, min(TILT_MAX_DEG, tilt))
        self.kit.servo[PAN_CHANNEL].angle = self.pan
        self.kit.servo[TILT_CHANNEL].angle = self.tilt

    def angles_for_pixel(self, x, y):
        if self.calibration is None:
            # Simple centre/edge mapping, recalculated fresh every frame
            err_x = (x - FRAME_WIDTH / 2) / (FRAME_WIDTH / 2)
            err_y = (y - FRAME_HEIGHT / 2) / (FRAME_HEIGHT / 2)
            return (PAN_AT_FRAME_CENTER + err_x * PAN_DEG_TO_FRAME_EDGE,
                    TILT_AT_FRAME_CENTER + err_y * TILT_DEG_TO_FRAME_EDGE)
        pan_coef, tilt_coef = self.calibration
        terms = pixel_terms(x, y, quadratic=len(pan_coef) == 6)
        return (sum(c * t for c, t in zip(pan_coef, terms)),
                sum(c * t for c, t in zip(tilt_coef, terms)))

    def aim_at(self, x, y):
        target_pan, target_tilt = self.angles_for_pixel(x, y)
        target_pan += self.offset_pan
        target_tilt += self.offset_tilt
        # Compare the remaining distance to the *target* (not the smoothed
        # step), otherwise smoothing halves every step and the servo stalls
        # up to 2 * MIN_MOVE_DEG short of where it should be.
        if (abs(target_pan - self.pan) >= MIN_MOVE_DEG
                or abs(target_tilt - self.tilt) >= MIN_MOVE_DEG):
            self.move_to(self.pan + AIM_SMOOTHING * (target_pan - self.pan),
                         self.tilt + AIM_SMOOTHING * (target_tilt - self.tilt))
        self.at_home = False

    def update(self, bbox):
        x1, y1, x2, y2 = bbox
        self.aim_at((x1 + x2) / 2, (y1 + y2) / 2)

    def target_lost(self, seconds_since_seen):
        if not self.at_home and seconds_since_seen > RETURN_HOME_DELAY:
            self.center()
            print(">>> Target lost -- pan/tilt re-centered")

    def release(self):
        # Re-center, then stop holding torque
        self.center()
        time.sleep(0.5)
        self.kit.servo[PAN_CHANNEL].angle = None
        self.kit.servo[TILT_CHANNEL].angle = None


# --- DETECTION LOGGING (writes directly to MongoDB; the backend's
# detection-service only ever reads this collection, never writes to it) ---
# Connection is attempted once at import time. If it fails (e.g. no
# internet), the script keeps running with logging silently disabled
# rather than crashing the whole detector over a non-essential feature.
try:
    _mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    _detections_collection = _mongo_client["birdguard"]["detections"]
except Exception as e:
    print(f"MongoDB connection failed (detection logging disabled): {e}")
    _detections_collection = None


def log_detection_event(label, confidence, bbox=None):
    # No-ops if the Mongo connection failed at startup -- logging is
    # best-effort and must never be the reason detection itself breaks.
    if _detections_collection is None:
        return
    try:
        doc = {
            "label": label,
            "confidence": confidence,
            "detectedAt": datetime.now(timezone.utc),
        }
        if bbox:
            doc["bbox"] = bbox
        _detections_collection.insert_one(doc)
    except Exception as e:
        print(f"Failed to log detection to MongoDB: {e}")


# --- MJPEG PREVIEW (no VNC/X server needed -- view at http://<pi-ip>:PORT/ in any browser) ---
# A tiny built-in HTTP server that streams whatever the main loop most
# recently wrote into `latest_frame` as a multipart JPEG stream -- the
# standard "motion JPEG" format most browsers can render natively as a
# live video feed with an <img> tag, no plugins or special player needed.
latest_frame = None
latest_frame_lock = threading.Lock()


class _MJPEGHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Every GET request becomes a long-lived stream: send the MJPEG
        # multipart header once, then keep pushing whatever `latest_frame`
        # currently holds until the client disconnects.
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()
        try:
            while True:
                with latest_frame_lock:
                    frame = latest_frame
                if frame is None:
                    time.sleep(0.05)
                    continue
                ok, jpg = cv2.imencode(".jpg", frame)
                if not ok:
                    continue
                self.wfile.write(b"--frame\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                self.wfile.write(jpg.tobytes())
                self.wfile.write(b"\r\n")
                time.sleep(0.05)
        except (BrokenPipeError, ConnectionResetError):
            # Normal when a viewer closes the browser tab / app -- not an
            # actual error, just the stream ending.
            pass

    def log_message(self, format, *args):
        pass  # silence per-request access logging


def start_preview_server(port=PREVIEW_PORT):
    # Runs on its own daemon thread so the HTTP server can serve viewers
    # concurrently with the main detection loop, without blocking it.
    server = ThreadingHTTPServer(("0.0.0.0", port), _MJPEGHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def get_lan_ip():
    # Raspberry Pi OS maps the hostname to 127.0.1.1 in /etc/hosts, so
    # socket.gethostbyname(socket.gethostname()) returns a loopback address
    # instead of the real LAN IP. Opening a UDP "connection" (no packets
    # actually sent) forces the OS to pick the real outbound interface.
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="BirdGuard CPU detector + pan/tilt laser")
    parser.add_argument("--adjust", action="store_true",
                        help="live aim adjustment: nudge the aim with keys in this terminal "
                             "and save the correction to laser_aim_offset.json")
    parser.add_argument("--target", default=TARGET_CLASS,
                        help=f"object class to track (default: {TARGET_CLASS})")
    parser.add_argument("--conf", type=float, default=CONFIDENCE_THRESHOLD,
                        help=f"detection confidence threshold (default: {CONFIDENCE_THRESHOLD})")
    return parser.parse_args()


ADJUST_HELP = """
--- AIM ADJUST MODE --- (press keys in THIS terminal, no Enter needed)
  a / d    pan offset  - / +
  w / s    tilt offset + / -
  [ / ]    step size smaller / bigger
  r        reset offset to 0
  p        print current offset
  x        SAVE offset (used on every later run)
  Ctrl+C   stop
Watch the laser dot vs the white circle (aim point) in the browser preview.
If a key moves the dot the wrong way, use the opposite key.
"""


def handle_adjust_key(key, tracker, step_i):
    # Returns the (possibly changed) step index
    step = ADJUST_STEPS_DEG[step_i]
    if key == "a":
        tracker.offset_pan -= step
    elif key == "d":
        tracker.offset_pan += step
    elif key == "w":
        tracker.offset_tilt += step
    elif key == "s":
        tracker.offset_tilt -= step
    elif key == "[":
        step_i = max(0, step_i - 1)
    elif key == "]":
        step_i = min(len(ADJUST_STEPS_DEG) - 1, step_i + 1)
    elif key == "r":
        tracker.offset_pan = tracker.offset_tilt = 0.0
    elif key == "x":
        save_aim_offset(tracker.offset_pan, tracker.offset_tilt)
        return step_i
    elif key != "p":
        return step_i
    print(f"\n>>> offset pan {tracker.offset_pan:+.1f} / tilt {tracker.offset_tilt:+.1f} deg "
          f"(step {ADJUST_STEPS_DEG[step_i]} deg)")
    return step_i


def main():
    global latest_frame
    args = parse_args()
    target_class, confidence = args.target, args.conf
    print(f"Session: {SESSION_DIR}")
    print(f"Target: {target_class.upper()} | Confidence: {confidence}")
    print(f"Video: {VIDEO_PATH}")
    print(f"Laser trigger: GPIO{LASER_GPIO} -> Nano D2 -> Nano D6 -> laser")
    print(f"Power relay: GPIO{POWER_RELAY_GPIO} -> relay IN1 -> laser PSU")
    print(f"Pan/tilt: PCA9685 0x{PCA9685_I2C_ADDRESS:02X} channel {PAN_CHANNEL} (pan) / "
          f"{TILT_CHANNEL} (tilt) | Camera rotation: {CAMERA_ROTATION} deg")

    set_laser_power(False)  # laser + relay OFF at startup
    tracker = PanTiltTracker(load_calibration(), load_aim_offset())  # servos to start position

    # UDP socket for broadcasting each detection's bounding box to any
    # local listener (e.g. a future pan/tilt tracking process) -- fire
    # and forget, no listener needs to be present for this to work.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Load YOLOv8 -- the "n" (nano) variant, chosen for CPU inference
    # speed on the Pi rather than accuracy, since there's no GPU/NPU here.
    print("Loading YOLOv8 (n)...")
    model = YOLO("yolov8n.pt")
    print("Model loaded.")

    # Init camera at the configured resolution/frame-rate window via
    # picamera2 (libcamera) -- "RGB888" is BGR byte order, which is what
    # OpenCV/YOLO expect. Mounted sideways: ask the sensor for a tall image
    # so the frame is FRAME_WIDTH x FRAME_HEIGHT once rotated upright.
    sideways = CAMERA_ROTATION in (90, 270)
    capture_size = (FRAME_HEIGHT, FRAME_WIDTH) if sideways else (FRAME_WIDTH, FRAME_HEIGHT)
    picam2 = Picamera2()
    config = picam2.create_video_configuration(
        main={"size": capture_size, "format": "RGB888"},
        controls={"FrameDurationLimits": (33333, 66666)}
    )
    picam2.configure(config)
    picam2.start()
    picam2.set_controls({"ScalerCrop": centre_crop(picam2, capture_size),
                         "AwbEnable": True,
                         "Saturation": CAMERA_SATURATION,
                         "Brightness": CAMERA_BRIGHTNESS})
    time.sleep(2)  # let auto-exposure/auto-white-balance settle before recording starts

    # Init video writer — records continuously from the start, not just
    # during detections, so the full session is available for review.
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    writer = cv2.VideoWriter(VIDEO_PATH, fourcc, VIDEO_FPS, (FRAME_WIDTH, FRAME_HEIGHT))
    print(f"Recording started -> {VIDEO_PATH}")

    start_preview_server()
    pi_ip = get_lan_ip()
    print(f"Live preview: http://{pi_ip}:{PREVIEW_PORT}/  (no VNC/X server needed). Use Ctrl+C to stop.")

    laser_on = False
    last_detection_time = 0
    frame_count = 0
    detection_count = 0
    last_write_time = time.time()

    print(f"\nWatching for {target_class.upper()}... (Ctrl+C to stop)\n")

    keys = None
    step_i = 1
    if args.adjust:
        print(ADJUST_HELP)
        keys = KeyReader()

    try:
        while True:
            # --- CAPTURE + INFERENCE ---
            # One frame in, one YOLO pass out -- runs synchronously in the
            # main loop since CPU inference is already the bottleneck here;
            # no benefit to a separate inference thread.
            frame = rotate_frame(picam2.capture_array())
            bgr = frame

            results = model.predict(frame, conf=confidence, verbose=False)[0]
            target_found = False
            detections = []

            # Walk every detected box this frame and keep only the ones
            # matching target_class ("person") -- YOLO detects many object
            # classes, but only this one drives the laser/logging below.
            for box in results.boxes:
                class_id = int(box.cls[0])
                label = model.names[class_id]

                if label == target_class:
                    target_found = True
                    last_detection_time = time.time()

                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    conf = float(box.conf[0])
                    detections.append((x1, y1, x2, y2, label, conf))

                    if not args.adjust:  # keep the terminal readable while adjusting
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] DETECTED: {label.upper()} | conf: {conf:.2f}")

                    # Broadcast this detection's box over UDP -- fire and
                    # forget, for any downstream process that wants it
                    # (e.g. pan/tilt tracking), independent of the laser
                    # and MongoDB logic below.
                    payload = {
                        "timestamp": time.time(),
                        "label": label,
                        "confidence": conf,
                        "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
                    }
                    sock.sendto(json.dumps(payload).encode(), (UDP_IP, UDP_PORT))

            # --- LIVE AIM ADJUSTMENT (--adjust) ---
            if keys:
                key = keys.get()
                while key:
                    step_i = handle_adjust_key(key.lower(), tracker, step_i)
                    key = keys.get()

            # --- PAN/TILT TRACKING (every frame a person is visible) ---
            # Aim straight at the highest-confidence person's pixel position.
            # With no person for RETURN_HOME_DELAY seconds, re-center.
            if detections:
                tx1, ty1, tx2, ty2, _, _ = max(detections, key=lambda d: d[5])
                tracker.update((tx1, ty1, tx2, ty2))
            else:
                tracker.target_lost(time.time() - last_detection_time)

            # --- LASER + POWER RELAY CONTROL ---
            # (Pi GPIO12 -> Nano D2 -> Nano D6 -> laser trigger,
            #  Pi GPIO17 -> relay IN1 -> laser PSU positive -> laser power)
            # Edge-triggered, not level-triggered: both turn on once when a
            # person first appears, and off only after they've been gone
            # for LASER_OFF_DELAY seconds (debounced so brief gaps in
            # detection between frames don't flicker on/off, which would
            # also chatter the relay's mechanical contacts needlessly).
            if target_found and not laser_on:
                set_laser_power(True)
                laser_on = True
                print(">>> LASER ON (relay powered)")

                # Log this as one detection event (not per-frame) -- use
                # the highest-confidence detection in this frame.
                top = max(detections, key=lambda d: d[5])
                x1, y1, x2, y2, top_label, top_conf = top
                if not args.adjust:  # adjustment sessions aren't real detections
                    log_detection_event(top_label, top_conf, {"x1": x1, "y1": y1, "x2": x2, "y2": y2})

            elif not target_found and laser_on:
                if time.time() - last_detection_time > LASER_OFF_DELAY:
                    set_laser_power(False)
                    laser_on = False
                    print(">>> LASER OFF (relay unpowered)")

            # --- VIDEO RECORDING ---
            # Every frame gets written to the session's video file
            # regardless of detections; frames with a person also get a
            # drawn bounding box + label and a separate annotated snapshot
            # saved to disk for quick review without scrubbing the video.
            video_frame = bgr.copy()
            if detections:
                for x1, y1, x2, y2, label, conf in detections:
                    cv2.rectangle(video_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(video_frame, f"{label} {conf:.2f}", (x1, y1 - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                cv2.imwrite(f"{DETECTIONS_DIR}/frame_{frame_count:05d}.jpg", video_frame)
                detection_count += 1
            # Aim point (centre of the tracked box) -- where the laser dot
            # should land -- plus the commanded servo angles and aim offset
            if detections:
                tx1, ty1, tx2, ty2, _, _ = max(detections, key=lambda d: d[5])
                cv2.circle(video_frame, ((tx1 + tx2) // 2, (ty1 + ty2) // 2), 12, (255, 255, 255), 2)
            cv2.putText(video_frame,
                        f"pan {tracker.pan:.0f}  tilt {tracker.tilt:.0f}  "
                        f"offset {tracker.offset_pan:+.1f}/{tracker.offset_tilt:+.1f}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

            # Inference doesn't run at a perfectly steady frame rate, so
            # the frame is written `repeats` times (based on real elapsed
            # time since the last write) to keep the output video's
            # playback speed matching real time rather than drifting.
            now = time.time()
            repeats = max(1, round((now - last_write_time) * VIDEO_FPS))
            last_write_time = now
            for _ in range(repeats):
                writer.write(video_frame)
            frame_count += 1

            # Publish this frame for the MJPEG preview server's handler
            # thread to pick up on its next iteration.
            with latest_frame_lock:
                latest_frame = video_frame

    except KeyboardInterrupt:
        print(f"\n\nStopped. {frame_count} frames | {detection_count} detections")
        print(f"Video saved: {VIDEO_PATH}")
    finally:
        # Always leave the laser and relay off and release hardware/file
        # handles cleanly, however the loop above exited -- including a
        # crash, so the relay can't be left stuck powering the laser.
        if laser_on:
            set_laser_power(False)
            print("Laser + relay OFF (cleanup)")
        tracker.release()
        print("Pan/tilt re-centered and released (cleanup)")
        if keys:
            keys.close()
            print(f"Final offset: pan {tracker.offset_pan:+.1f} / tilt {tracker.offset_tilt:+.1f} deg "
                  "(only kept if you pressed x to save)")
        writer.release()
        picam2.stop()
        cv2.destroyAllWindows()
        sock.close()


if __name__ == "__main__":
    main()
