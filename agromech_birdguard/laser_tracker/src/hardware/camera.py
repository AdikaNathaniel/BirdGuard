"""Picamera2 wrapper used by every test script."""
import cv2
from picamera2 import Picamera2


class Camera:
    def __init__(self, resolution=(1280, 720), frame_rate=15):
        self.picam2 = Picamera2()
        video_config = self.picam2.create_video_configuration(
            main={"size": resolution, "format": "RGB888"})
        self.picam2.configure(video_config)
        self.picam2.set_controls({"FrameRate": frame_rate})  # <- FPS variable
        self.picam2.start()

    def read(self):
        frame_rgb = self.picam2.capture_array()
        return True, cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

    def release(self):
        self.picam2.stop()
        self.picam2.close()