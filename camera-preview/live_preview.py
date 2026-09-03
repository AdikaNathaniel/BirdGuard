import os
import cv2
import time
from datetime import datetime
from picamera2 import Picamera2
from libcamera import controls

FRAME_WIDTH = 640
FRAME_HEIGHT = 480
VIDEO_FPS = 2  # matches the achievable real-time capture rate, so playback speed is accurate
WINDOW_NAME = "BirdGuard - Live Camera Preview"

# Session folder
session_name = datetime.now().strftime("preview_%Y-%m-%d_%H-%M-%S")
SESSION_DIR = f"/home/pi/birdguard-test/{session_name}"
VIDEO_PATH = f"{SESSION_DIR}/recording.avi"
os.makedirs(SESSION_DIR, exist_ok=True)

# Load the Arducam tuning file so color reproduction matches rpicam-still
tuning = Picamera2.load_tuning_file("arducam_64mp.json")
picam2 = Picamera2(tuning=tuning)
config = picam2.create_video_configuration(
    main={"size": (FRAME_WIDTH, FRAME_HEIGHT), "format": "RGB888"}
)
picam2.configure(config)
picam2.start()
picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous, "Saturation": 2.0})
time.sleep(1)

fourcc = cv2.VideoWriter_fourcc(*'XVID')
writer = cv2.VideoWriter(VIDEO_PATH, fourcc, VIDEO_FPS, (FRAME_WIDTH, FRAME_HEIGHT))
print(f"Video: {VIDEO_PATH}")

cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

print("Streaming live camera preview... (press 'q' or close window to stop)")

frame_count = 0

try:
    while True:
        frame = picam2.capture_array()  # RGB888
        frame = cv2.flip(frame, -1)  # 180 degree flip (physical camera mount is upside-down)
        # picamera2 delivers RGB, but OpenCV's imshow/VideoWriter expect
        # BGR channel order -- without this conversion, colors would be
        # visibly wrong (red/blue swapped) in both the preview and the file.
        bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        cv2.imshow(WINDOW_NAME, bgr)
        writer.write(bgr)
        frame_count += 1

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
            print("\nWindow closed by user.")
            break

except KeyboardInterrupt:
    print("\nStopped via Ctrl+C.")
finally:
    print(f"{frame_count} frames")
    print(f"Video saved: {VIDEO_PATH}")
    writer.release()
    cv2.destroyAllWindows()
    picam2.stop()
