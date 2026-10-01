"""Pixel -> servo angle calibration for the fixed camera + pan/tilt laser.

The camera is fixed and only the laser moves, so every pixel in the frame
always corresponds to the same pan/tilt angles. This script records that
relationship: steer the laser dot with the arrow keys, click on the dot in
the video window, save the point, repeat across the frame. The fitted
mapping is written to laser_aim_calibration.json, which
pi_person_detector_cpu.py loads to aim straight at a detection's pixel.

Needs a display (Pi desktop or VNC). Aim the laser at a wall/backdrop with
nobody in front of it.

Controls (click the video window first):
  Arrow keys   move pan / tilt by the current step
  [ / ]        step size down / up (0.5, 1, 2, 5 deg)
  L            laser on / off
  Mouse click  mark where the laser dot is in the picture
  S            save the marked pixel + current pan/tilt as a point
  U            undo the last saved point
  W            fit, write laser_aim_calibration.json and quit
  Q / Esc      quit without writing
"""
import json
import os
import subprocess
import time
import cv2
import numpy as np
from picamera2 import Picamera2
from adafruit_servokit import ServoKit

# Must match pi_person_detector_cpu.py
LASER_GPIO = 12
POWER_RELAY_GPIO = 17
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
CAMERA_ROTATION = 270
CAMERA_SATURATION = 1.5
CAMERA_BRIGHTNESS = 0.2
PCA9685_I2C_ADDRESS = 0x40
PAN_CHANNEL = 2
TILT_CHANNEL = 3
SERVO_MIN_US = 500
SERVO_MAX_US = 2500
PAN_MIN_DEG, PAN_MAX_DEG = 0, 180
TILT_MIN_DEG, TILT_MAX_DEG = 40, 140
PAN_START_DEG = 90
TILT_START_DEG = 90

CALIBRATION_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "laser_aim_calibration.json")
MIN_POINTS = 4
EDGE_MARGIN_PX = 40           # refuse clicks this close to the frame edge
STEPS = [0.5, 1, 2, 5]
WINDOW = "Laser aim calibration"

_ROTATE_CODES = {
    90: cv2.ROTATE_90_CLOCKWISE,
    180: cv2.ROTATE_180,
    270: cv2.ROTATE_90_COUNTERCLOCKWISE,
}


def set_gpio(pin, high):
    subprocess.run(["pinctrl", "set", str(pin), "op", "dh" if high else "dl"], check=True)


def set_laser_power(high):
    if high:
        set_gpio(POWER_RELAY_GPIO, True)
        time.sleep(0.1)
        set_gpio(LASER_GPIO, True)
    else:
        set_gpio(LASER_GPIO, False)
        set_gpio(POWER_RELAY_GPIO, False)


def centre_crop(picam2, size):
    max_x, max_y, max_w, max_h = picam2.camera_controls["ScalerCrop"][1]
    aspect = size[0] / size[1]
    crop_w, crop_h = max_w, max_h
    if max_w / max_h > aspect:
        crop_w = int(max_h * aspect)
    else:
        crop_h = int(max_w / aspect)
    return (max_x + (max_w - crop_w) // 2, max_y + (max_h - crop_h) // 2,
            crop_w, crop_h)


def open_camera():
    sideways = CAMERA_ROTATION in (90, 270)
    size = (FRAME_HEIGHT, FRAME_WIDTH) if sideways else (FRAME_WIDTH, FRAME_HEIGHT)
    picam2 = Picamera2()
    picam2.configure(picam2.create_video_configuration(
        main={"size": size, "format": "RGB888"}))
    picam2.start()
    picam2.set_controls({"ScalerCrop": centre_crop(picam2, size),
                         "AwbEnable": True,
                         "Saturation": CAMERA_SATURATION,
                         "Brightness": CAMERA_BRIGHTNESS})
    time.sleep(2)
    return picam2


def read_frame(picam2):
    frame = picam2.capture_array()
    if CAMERA_ROTATION in _ROTATE_CODES:
        frame = cv2.rotate(frame, _ROTATE_CODES[CAMERA_ROTATION])
    return frame


def pixel_terms(x, y, quadratic):
    # Must match pixel_terms() in pi_person_detector_cpu.py. Pixels are
    # scaled to roughly -1..1 so the quadratic terms stay well-conditioned.
    u = (x - FRAME_WIDTH / 2) / (FRAME_WIDTH / 2)
    v = (y - FRAME_HEIGHT / 2) / (FRAME_HEIGHT / 2)
    return [u, v, 1.0] + ([u * u, v * v, u * v] if quadratic else [])


def fit(points):
    """Least-squares fit of pan/tilt from pixel position.

    4-7 points: plane (pan = a*u + b*v + c). 8+ points: adds u^2, v^2, u*v so
    the curve from pan and tilt interacting on the pan/tilt head is captured.
    """
    # 8+ (not 6) leaves spare points, so the RMS error still exposes a bad click
    quadratic = len(points) >= 8
    terms = np.array([pixel_terms(p["x"], p["y"], quadratic) for p in points])
    pan = np.array([p["pan"] for p in points])
    tilt = np.array([p["tilt"] for p in points])
    pan_coef = np.linalg.lstsq(terms, pan, rcond=None)[0]
    tilt_coef = np.linalg.lstsq(terms, tilt, rcond=None)[0]
    pan_rms = float(np.sqrt(np.mean((terms @ pan_coef - pan) ** 2)))
    tilt_rms = float(np.sqrt(np.mean((terms @ tilt_coef - tilt) ** 2)))
    return pan_coef.tolist(), tilt_coef.tolist(), pan_rms, tilt_rms


def normalise_key(raw_key):
    # Linux adds Num Lock / Caps Lock bits above 0xFFFF; Windows arrow codes
    # (2490368 etc.) have zero low bits and are kept as-is.
    if raw_key > 0xFFFFF and (raw_key & 0xFFFF) == 0:
        return raw_key
    return raw_key & 0xFFFF


def main():
    set_laser_power(False)
    kit = ServoKit(channels=16, address=PCA9685_I2C_ADDRESS)
    for ch in (PAN_CHANNEL, TILT_CHANNEL):
        kit.servo[ch].set_pulse_width_range(SERVO_MIN_US, SERVO_MAX_US)
    pan, tilt = float(PAN_START_DEG), float(TILT_START_DEG)
    kit.servo[PAN_CHANNEL].angle = pan
    kit.servo[TILT_CHANNEL].angle = tilt

    picam2 = open_camera()
    clicked = None
    points = []
    step_i = 1
    laser_on = False

    def on_mouse(event, x, y, flags, param):
        nonlocal clicked
        if event == cv2.EVENT_LBUTTONDOWN:
            clicked = (x, y)

    cv2.namedWindow(WINDOW, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(WINDOW, on_mouse)
    print(__doc__)
    print("Tip: spread points over the whole frame -- corners, edges and centre --")
    print(f"     but keep the dot clearly visible, at least {EDGE_MARGIN_PX}px in from the edge.")

    try:
        while True:
            frame = read_frame(picam2)
            for i, p in enumerate(points, 1):
                cv2.circle(frame, (p["x"], p["y"]), 6, (255, 0, 0), 2)
                cv2.putText(frame, str(i), (p["x"] + 8, p["y"] - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            if clicked:
                cv2.drawMarker(frame, clicked, (0, 255, 255), cv2.MARKER_CROSS, 25, 2)
            hud = (f"pan {pan:.1f}  tilt {tilt:.1f}  step {STEPS[step_i]}  "
                   f"laser {'ON' if laser_on else 'OFF'}  points {len(points)}")
            cv2.putText(frame, hud, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.putText(frame, "arrows move | [ ] step | L laser | click dot | S save | U undo | W write | Q quit",
                        (10, FRAME_HEIGHT - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
            cv2.imshow(WINDOW, frame)

            raw_key = cv2.waitKeyEx(30)
            if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break
            if raw_key == -1:
                continue
            key = normalise_key(raw_key)
            step = STEPS[step_i]

            if key in (ord("q"), ord("Q"), 27):
                print("Quit without writing calibration.")
                break
            elif key in (82, 65362, 2490368):      # up
                tilt = min(TILT_MAX_DEG, tilt + step)
            elif key in (84, 65364, 2621440):      # down
                tilt = max(TILT_MIN_DEG, tilt - step)
            elif key in (81, 65361, 2424832):      # left
                pan = max(PAN_MIN_DEG, pan - step)
            elif key in (83, 65363, 2555904):      # right
                pan = min(PAN_MAX_DEG, pan + step)
            elif key == ord("["):
                step_i = max(0, step_i - 1)
            elif key == ord("]"):
                step_i = min(len(STEPS) - 1, step_i + 1)
            elif key in (ord("l"), ord("L")):
                laser_on = not laser_on
                set_laser_power(laser_on)
            elif key in (ord("s"), ord("S")):
                if clicked is None:
                    print("Click on the laser dot first, then press S.")
                elif (min(clicked[0], FRAME_WIDTH - clicked[0]) < EDGE_MARGIN_PX
                      or min(clicked[1], FRAME_HEIGHT - clicked[1]) < EDGE_MARGIN_PX):
                    print(f"Not saved: click is within {EDGE_MARGIN_PX}px of the edge -- the dot "
                          "has probably left the picture. Move it further in and click again.")
                    clicked = None
                else:
                    points.append({"x": clicked[0], "y": clicked[1], "pan": pan, "tilt": tilt})
                    print(f"Saved point {len(points)}: pixel {clicked} -> pan {pan:.1f}, tilt {tilt:.1f}")
                    clicked = None
            elif key in (ord("u"), ord("U")):
                if points:
                    print(f"Removed point {len(points)}: {points.pop()}")
            elif key in (ord("w"), ord("W")):
                if len(points) < MIN_POINTS:
                    print(f"Need at least {MIN_POINTS} points (have {len(points)}).")
                    continue
                pan_coef, tilt_coef, pan_rms, tilt_rms = fit(points)
                with open(CALIBRATION_PATH, "w") as f:
                    json.dump({"version": 2,  # coefficients use normalised pixels
                               "frame_size": [FRAME_WIDTH, FRAME_HEIGHT],
                               "camera_rotation": CAMERA_ROTATION,
                               "pan": pan_coef, "tilt": tilt_coef,
                               "rms_error_deg": {"pan": pan_rms, "tilt": tilt_rms},
                               "points": points}, f, indent=2)
                print(f"Wrote {CALIBRATION_PATH}")
                print(f"Fit error (RMS): pan {pan_rms:.2f} deg, tilt {tilt_rms:.2f} deg")
                if max(pan_rms, tilt_rms) > 2:
                    print("Error is high -- check for mis-clicked points (U to undo) and re-run.")
                break

            kit.servo[PAN_CHANNEL].angle = pan
            kit.servo[TILT_CHANNEL].angle = tilt
    finally:
        set_laser_power(False)
        kit.servo[PAN_CHANNEL].angle = None
        kit.servo[TILT_CHANNEL].angle = None
        picam2.stop()
        cv2.destroyAllWindows()
        print("Laser OFF, servos released.")


if __name__ == "__main__":
    main()
