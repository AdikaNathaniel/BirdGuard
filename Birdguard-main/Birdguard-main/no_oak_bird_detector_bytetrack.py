import cv2
import time
import socket
import json
import argparse
import numpy as np
import supervision as sv
from ultralytics import YOLO

# --- Configuration ---
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
# In the standard COCO dataset used by YOLO, ID 14 corresponds to 'bird'
BIRD_LABEL_ID = 14

def main():
    # --- 1. Command Line Arguments ---
    parser = argparse.ArgumentParser()
    parser.add_argument('-hl', '--headless', type=str, default="True", help="Run in headless mode. Default: True")
    args = parser.parse_args()
    
    headless = args.headless.lower() == "true"

    # --- 2. Network Setup ---
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print("Starting No-OAK Detector (YOLO + ByteTrack + Inbuilt Camera)...")

    # --- 3. Load AI Models ---
    model = YOLO("yolov10n.pt") 
    
    # Initialize ByteTrack
    tracker = sv.ByteTrack(track_activation_threshold=0.3, lost_track_buffer=30, frame_rate=30)

    # --- 4. Inbuilt Camera Setup ---
    # use index 0 for the default inbuilt camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open inbuilt camera (index 0).")
        return

    # Set resolution to 640x480 to match previous logic
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # Since we don't have a real depth sensor, we'll simulate depth (Z)
    # based on the assumption that a average bird has a known physical size.
    # This is a very rough estimation.
    KNOWN_BIRD_WIDTH_MM = 150 # Est. 15cm width
    FOCAL_LENGTH_PIXELS = 500 # Approximation for a typical webcam at 640x480

    prev_frame_time = time.time()
    new_frame_time = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            new_frame_time = time.time()
            
            # --- HOST CPU PROCESSING ---
            results = model(frame, classes=[BIRD_LABEL_ID], verbose=False)[0]
            detections = sv.Detections.from_ultralytics(results)

            # Feed YOLO detections into ByteTrack
            tracked_detections = tracker.update_with_detections(detections)

            # Process every bird currently being tracked
            for i in range(len(tracked_detections)):
                t_box = tracked_detections.xyxy[i].astype(int)
                t_id = int(tracked_detections.tracker_id[i])
                
                # Calculate center
                box_w = t_box[2] - t_box[0]
                box_h = t_box[3] - t_box[1]
                center_x = int(t_box[0] + box_w / 2)
                center_y = int(t_box[1] + box_h / 2)
                
                # Simulate depth Z (mm) = (Known Width * Focal Length) / Pixel Width
                if box_w > 0:
                    z_mm = int((KNOWN_BIRD_WIDTH_MM * FOCAL_LENGTH_PIXELS) / box_w)
                else:
                    z_mm = 0

                # Manual Spatial Calculation using Pinhole Geometry (Relative to center)
                # We'll use 320, 240 as approximate optical centers for 640x480
                cx, cy = 320, 240
                fx, fy = FOCAL_LENGTH_PIXELS, FOCAL_LENGTH_PIXELS
                
                x_mm = int((center_x - cx) * z_mm / fx)
                y_mm = int((center_y - cy) * z_mm / fy)

                # Build the JSON payload
                payload = {
                    "timestamp": time.time(),
                    "id": t_id,
                    "label": "bird",
                    "spatial": {"x_mm": x_mm, "y_mm": y_mm, "z_mm": z_mm},
                    "bbox": {"x1": int(t_box[0]), "y1": int(t_box[1]), "x2": int(t_box[2]), "y2": int(t_box[3])}
                }
                sock.sendto(json.dumps(payload).encode('utf-8'), (UDP_IP, UDP_PORT))

                # Draw boxes (only if headless mode is off)
                if not headless:
                    cv2.rectangle(frame, (t_box[0], t_box[1]), (t_box[2], t_box[3]), (0, 0, 255), 2)
                    cv2.putText(frame, f"Bird #{t_id} | Z:{z_mm}mm*", (t_box[0], t_box[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

            # FPS
            fps = 1 / (new_frame_time - prev_frame_time)
            prev_frame_time = new_frame_time
            
            if not headless:
                cv2.putText(frame, f"No-OAK FPS: {int(fps)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                cv2.imshow("No-OAK ByteTrack Detector", frame)
                if cv2.waitKey(1) == ord('q'):
                    break

    except KeyboardInterrupt:
        print("\nStopping gracefully...")
    finally:
        cap.release()
        sock.close()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
