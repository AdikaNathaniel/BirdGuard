import time
import json
import serial
import socket
import os
import cv2
import numpy as np
from datetime import datetime
from picamera2 import Picamera2
from hailo_platform import (HEF, VDevice, HailoStreamInterface, InferVStreams,
                             ConfigureParams, InputVStreamParams, OutputVStreamParams,
                             FormatType)

# --- CONFIG ---
SERIAL_PORT = '/dev/serial0'
SERIAL_BAUD = 9600
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
TARGET_CLASS = "person"       # Change to "bird" for production
CONFIDENCE_THRESHOLD = 0.5
LASER_OFF_DELAY = 3.0         # Seconds to keep laser on after last detection
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
VIDEO_FPS = 60
HEF_PATH = "/usr/share/hailo-models/yolov8s_h8l.hef"
MODEL_INPUT_SIZE = 640        # yolov8s_h8l.hef expects 640x640x3 UINT8

# Standard 80-class COCO order (same ordering Ultralytics/YOLO use) --
# index 0 = person, index 14 = bird. The HEF only returns class indices,
# not names, so this list is required to map back to TARGET_CLASS.
COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
    "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
    "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
    "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
    "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
    "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
    "hair drier", "toothbrush"
]

# Session folder
session_name = datetime.now().strftime("session_%Y-%m-%d_%H-%M-%S")
SESSION_DIR = f"/home/pi/birdguard-test/{session_name}"
DETECTIONS_DIR = f"{SESSION_DIR}/detections"
VIDEO_PATH = f"{SESSION_DIR}/recording.avi"
os.makedirs(DETECTIONS_DIR, exist_ok=True)


def main():
    print(f"Session: {SESSION_DIR}")
    print(f"Target: {TARGET_CLASS.upper()} | Confidence: {CONFIDENCE_THRESHOLD}")
    print(f"Video: {VIDEO_PATH}")

    # Init UART
    try:
        ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
        time.sleep(1)
        print(f"UART ready: {SERIAL_PORT} @ {SERIAL_BAUD} baud")
    except Exception as e:
        print(f"UART not available: {e}")
        ser = None

    # Init UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Init camera
    picam2 = Picamera2()
    config = picam2.create_video_configuration(
        main={"size": (FRAME_WIDTH, FRAME_HEIGHT), "format": "RGB888"},
        controls={"FrameDurationLimits": (33333, 66666)}
    )
    picam2.configure(config)
    picam2.start()
    picam2.set_controls({"AwbEnable": True, "Saturation": 1.5, "Brightness": 0.2})
    time.sleep(2)

    # Init video writer
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    writer = cv2.VideoWriter(VIDEO_PATH, fourcc, VIDEO_FPS, (FRAME_WIDTH, FRAME_HEIGHT))
    print(f"Recording started -> {VIDEO_PATH}")

    # Live preview needs a display (X11/Wayland). Over a headless SSH session
    # there isn't one -- Qt hard-aborts the process (not a catchable exception)
    # if imshow/namedWindow is called with no DISPLAY, so check env vars up
    # front and never touch a cv2 GUI function at all when headless.
    headless = not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    if headless:
        print("No display available -- running headless (no live preview). Use Ctrl+C to stop.")
    else:
        cv2.namedWindow("BirdGuard - Hailo Detection", cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty("BirdGuard - Hailo Detection", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    laser_on = False
    last_detection_time = 0
    frame_count = 0
    detection_count = 0
    last_write_time = time.time()

    # Scale factors: model runs on a plain 640x640 resize (no letterbox),
    # so bbox coords must be scaled back independently per axis to map
    # onto the FRAME_WIDTH x FRAME_HEIGHT display/recording frame.
    scale_x = FRAME_WIDTH / MODEL_INPUT_SIZE
    scale_y = FRAME_HEIGHT / MODEL_INPUT_SIZE

    print(f"Loading HEF: {HEF_PATH}")
    hef = HEF(HEF_PATH)

    with VDevice() as target:
        configure_params = ConfigureParams.create_from_hef(hef=hef, interface=HailoStreamInterface.PCIe)
        network_group = target.configure(hef, configure_params)[0]
        network_group_params = network_group.create_params()

        input_vstream_info = hef.get_input_vstream_infos()[0]
        output_vstream_info = hef.get_output_vstream_infos()[0]

        # Input layer is native UINT8 -- feed raw 0-255 pixel values, no normalization.
        input_vstreams_params = InputVStreamParams.make_from_network_group(
            network_group, quantized=True, format_type=FormatType.UINT8)
        # Output is the fused NMS-by-class postprocess, already dequantized to FLOAT32.
        output_vstreams_params = OutputVStreamParams.make_from_network_group(
            network_group, quantized=False, format_type=FormatType.FLOAT32)

        print("Model loaded.")
        print(f"\nWatching for {TARGET_CLASS.upper()}... (Ctrl+C to stop)\n")

        with InferVStreams(network_group, input_vstreams_params, output_vstreams_params) as infer_pipeline:
            with network_group.activate(network_group_params):
                try:
                    while True:
                        frame = picam2.capture_array()  # RGB888, FRAME_WIDTH x FRAME_HEIGHT
                        bgr = frame

                        model_input = cv2.resize(frame, (MODEL_INPUT_SIZE, MODEL_INPUT_SIZE))
                        model_input = np.expand_dims(model_input, axis=0)  # (1, 640, 640, 3)

                        results = infer_pipeline.infer({input_vstream_info.name: model_input})
                        # Output is batch-wrapped (batch size 1): raw_detections[0] is the
                        # per-image result, itself a length-80 list indexed by class, each
                        # entry an (N, 5) array of [y_min, x_min, y_max, x_max, score] (0-1).
                        raw_detections = results[output_vstream_info.name][0]

                        if frame_count == 0:
                            print(f"DEBUG raw_detections len={len(raw_detections)} "
                                  f"person_shape={np.asarray(raw_detections[0]).shape}")

                        target_found = False
                        detections = []

                        if 0 <= COCO_CLASSES.index(TARGET_CLASS) < len(raw_detections):
                            class_id = COCO_CLASSES.index(TARGET_CLASS)
                            label = TARGET_CLASS
                            # Only the TARGET_CLASS slot of the 80-class
                            # output is read -- the HEF's fused NMS
                            # postprocess already separates detections by
                            # class, so no manual class filtering needed.
                            for det in raw_detections[class_id]:
                                y1n, x1n, y2n, x2n, conf = det
                                if conf < CONFIDENCE_THRESHOLD:
                                    continue

                                target_found = True
                                last_detection_time = time.time()

                                # Coordinates come out normalized (0-1)
                                # relative to MODEL_INPUT_SIZE -- convert to
                                # pixel coordinates on the actual capture
                                # frame using the precomputed per-axis scale.
                                x1 = int(x1n * MODEL_INPUT_SIZE * scale_x)
                                y1 = int(y1n * MODEL_INPUT_SIZE * scale_y)
                                x2 = int(x2n * MODEL_INPUT_SIZE * scale_x)
                                y2 = int(y2n * MODEL_INPUT_SIZE * scale_y)
                                detections.append((x1, y1, x2, y2, label, float(conf)))

                                print(f"[{datetime.now().strftime('%H:%M:%S')}] DETECTED: {label.upper()} | conf: {conf:.2f}")

                                payload = {
                                    "timestamp": time.time(),
                                    "label": label,
                                    "confidence": float(conf),
                                    "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
                                }
                                sock.sendto(json.dumps(payload).encode(), (UDP_IP, UDP_PORT))

                        # --- LASER CONTROL ---
                        if target_found and not laser_on:
                            if ser:
                                ser.write(b'O')
                            laser_on = True
                            print(">>> LASER ON")

                        elif not target_found and laser_on:
                            if time.time() - last_detection_time > LASER_OFF_DELAY:
                                if ser:
                                    ser.write(b'F')
                                laser_on = False
                                print(">>> LASER OFF")

                        # --- VIDEO RECORDING ---
                        video_frame = bgr.copy()
                        if detections:
                            for x1, y1, x2, y2, label, conf in detections:
                                cv2.rectangle(video_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                cv2.putText(video_frame, f"{label} {conf:.2f}", (x1, y1 - 8),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                            cv2.imwrite(f"{DETECTIONS_DIR}/frame_{frame_count:05d}.jpg", video_frame)
                            detection_count += 1

                        now = time.time()
                        repeats = max(1, round((now - last_write_time) * VIDEO_FPS))
                        last_write_time = now
                        for _ in range(repeats):
                            writer.write(video_frame)
                        frame_count += 1

                        if not headless:
                            cv2.imshow("BirdGuard - Hailo Detection", video_frame)
                            if cv2.waitKey(1) & 0xFF == ord('q'):
                                print("\n\n'q' pressed, stopping.")
                                break

                except KeyboardInterrupt:
                    print(f"\n\nStopped. {frame_count} frames | {detection_count} detections")
                    print(f"Video saved: {VIDEO_PATH}")
                finally:
                    if laser_on and ser:
                        ser.write(b'F')
                        print("Laser OFF (cleanup)")
                    writer.release()
                    picam2.stop()
                    cv2.destroyAllWindows()
                    if ser:
                        ser.close()
                    sock.close()


if __name__ == "__main__":
    main()
