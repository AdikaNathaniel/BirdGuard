"""Picamera2 wrapper used by every test script."""
import time
import cv2
from picamera2 import Picamera2

# Clockwise rotation in degrees -> OpenCV rotate code
_ROTATE_CODES = {
    90: cv2.ROTATE_90_CLOCKWISE,
    180: cv2.ROTATE_180,
    270: cv2.ROTATE_90_COUNTERCLOCKWISE,
}


class Camera:
    """Frames come out at `resolution` (width, height) after rotation.

    For 90/270 the sensor is read as a tall centre strip and then turned on its
    side, so the final picture is still wide instead of a narrow portrait.
    """

    def __init__(self, resolution=(1280, 720), frame_rate=15, rotation=0,
                 saturation=1.5, brightness=0.2):
        rotation = int(rotation) % 360
        if rotation not in (0, 90, 180, 270):
            raise ValueError("rotation must be 0, 90, 180 or 270")
        self.rotation = rotation

        w, h = resolution
        # Sideways: ask the sensor for a tall image so it is wide once rotated
        size = (h, w) if rotation in (90, 270) else (w, h)
        self.picam2 = Picamera2()
        video_config = self.picam2.create_video_configuration(
            main={"size": size, "format": "RGB888"})
        self.picam2.configure(video_config)
        self.picam2.set_controls({"FrameRate": frame_rate,  # <- FPS variable
                                  "ScalerCrop": self._centre_crop(size),
                                  "AwbEnable": True,
                                  "Saturation": saturation,
                                  "Brightness": brightness})
        self.picam2.start()
        time.sleep(2)  # let auto white balance and exposure settle

    def _centre_crop(self, size):
        """Largest centred sensor area with the same shape as `size` (no stretching)."""
        max_x, max_y, max_w, max_h = self.picam2.camera_controls["ScalerCrop"][1]
        aspect = size[0] / size[1]
        crop_w, crop_h = max_w, max_h
        if max_w / max_h > aspect:
            crop_w = int(max_h * aspect)
        else:
            crop_h = int(max_w / aspect)
        return (max_x + (max_w - crop_w) // 2, max_y + (max_h - crop_h) // 2,
                crop_w, crop_h)

    def read(self):
        # Picamera2 "RGB888" is already BGR byte order, which is what OpenCV
        # and Ultralytics expect -- converting here would swap red and blue.
        frame = self.picam2.capture_array()
        if self.rotation:
            frame = cv2.rotate(frame, _ROTATE_CODES[self.rotation])
        return True, frame

    def release(self):
        self.picam2.stop()
        self.picam2.close()
