import cv2
import depthai as dai
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
    # Allows the user to run the script without a video window showing.
    # Useful for saving CPU resources on a Raspberry Pi.
    parser = argparse.ArgumentParser()
    parser.add_argument('-hl', '--headless', type=str, default="True", help="Run in headless mode. Default: True")
    args = parser.parse_args()
    
    headless = args.headless.lower() == "true"

    # --- 2. Network Setup ---
    # Initialize a UDP socket to broadcast the bird's coordinates
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print("Starting Host Detector (YOLO + ByteTrack + Spatial Math on CPU)...")

    # --- 3. Load AI Models ---
    # Load the YOLO object detection model directly onto the host's CPU/RAM
    model = YOLO("yolov10.pt")
    
    # Initialize ByteTrack to handle object occlusions and smooth trajectories
    # track_activation_threshold: minimum confidence to start tracking a new object
    # lost_track_buffer: how many frames to remember a bird if it flies behind a branch
    tracker = sv.ByteTrack(track_activation_threshold=0.3, lost_track_buffer=30, frame_rate=30)

    # --- 4. DepthAI v3 Pipeline Setup ---
    # We configure the camera to act as a "dumb" sensor, just sending raw video and depth
    device = dai.Device()
    with dai.Pipeline(device) as pipeline:
        
        # A. Setup the main RGB Color Camera
        camRgb = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_A)
        camRgbOut = camRgb.requestOutput(
            size=(640, 480), 
            resizeMode=dai.ImgResizeMode.CROP, 
            fps=30
        )

        # B. Setup the Left and Right Mono Cameras for Stereo Vision
        monoLeft = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_B)
        monoRight = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_C)
        
        leftOut = monoLeft.requestOutput((640, 400))
        rightOut = monoRight.requestOutput((640, 400))

        # C. Setup the Stereo Depth Node
        stereo = pipeline.create(dai.node.StereoDepth)
        stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.FAST_DENSITY)
        stereo.setDepthAlign(dai.CameraBoardSocket.CAM_A) # Align depth map to match color video
        stereo.setOutputSize(640, 480) # Force width to be a multiple of 16 to prevent crashes
        
        # Link the mono cameras to the stereo calculator
        leftOut.link(stereo.left)
        rightOut.link(stereo.right)

        # D. Create Output Queues to stream data to the host computer
        qRgb = camRgbOut.createOutputQueue(maxSize=4, blocking=False)
        qDepth = stereo.depth.createOutputQueue(maxSize=4, blocking=False)

        # --- 5. Execution Loop ---
        try:
            pipeline.start()

            # Retrieve camera lens properties (intrinsics) needed for manual 3D math
            calibData = device.readCalibration()
            intrinsics = calibData.getCameraIntrinsics(dai.CameraBoardSocket.CAM_A, 640, 480)
            fx, fy = intrinsics[0][0], intrinsics[1][1] # Focal lengths
            cx, cy = intrinsics[0][2], intrinsics[1][2] # Optical centers

            prev_frame_time = time.time()
            new_frame_time = 0

            # Main loop: Runs constantly while the camera is connected
            while pipeline.isRunning():
                # Grab the latest video frame and depth map from the camera
                inRgb = qRgb.get()
                inDepth = qDepth.get()
                
                frame = inRgb.getCvFrame()
                depthFrame = inDepth.getFrame() # A 2D array where each pixel value is distance in mm
                
                new_frame_time = time.time()
                
                # --- HOST CPU PROCESSING ---
                # Run YOLO detection on the current frame, looking strictly for birds
                results = model(frame, classes=[BIRD_LABEL_ID], verbose=False)[0]
                detections = sv.Detections.from_ultralytics(results)

                # Feed YOLO detections into ByteTrack to maintain consistent tracking IDs
                tracked_detections = tracker.update_with_detections(detections)

                # Process every bird currently being tracked
                for i in range(len(tracked_detections)):
                    t_box = tracked_detections.xyxy[i].astype(int)
                    t_id = int(tracked_detections.tracker_id[i])
                    
                    # Calculate the center (X, Y) pixel of the bird's bounding box
                    center_x = int((t_box[0] + t_box[2]) / 2)
                    center_y = int((t_box[1] + t_box[3]) / 2)
                    
                    # Ensure our calculated center doesn't fall outside the image boundaries
                    center_x = max(0, min(center_x, depthFrame.shape[1] - 1))
                    center_y = max(0, min(center_y, depthFrame.shape[0] - 1))

                    # Look up the Z coordinate (distance in mm) directly from the depth map array
                    z_mm = float(depthFrame[center_y, center_x])
                    
                    # If Z is 0, the camera couldn't calculate depth for that specific pixel, so skip it
                    if z_mm == 0: 
                        continue

                    # Manual Spatial Calculation using Pinhole Camera Geometry
                    # Converts 2D screen pixels into physical 3D space millimeters
                    x_mm = int((center_x - cx) * z_mm / fx)
                    y_mm = int((center_y - cy) * z_mm / fy)
                    z_mm = int(z_mm)

                    # Build the JSON payload to send to the motor controller script
                    payload = {
                        "timestamp": time.time(),
                        "id": t_id,
                        "label": "bird",
                        "spatial": {"x_mm": x_mm, "y_mm": y_mm, "z_mm": z_mm},
                        "bbox": {"x1": int(t_box[0]), "y1": int(t_box[1]), "x2": int(t_box[2]), "y2": int(t_box[3])}
                    }
                    sock.sendto(json.dumps(payload).encode('utf-8'), (UDP_IP, UDP_PORT))

                    # Draw boxes and data on the video feed (only if headless mode is off)
                    if not headless:
                        cv2.rectangle(frame, (t_box[0], t_box[1]), (t_box[2], t_box[3]), (0, 0, 255), 2)
                        cv2.putText(frame, f"Bird #{t_id} | Z:{z_mm}mm", (t_box[0], t_box[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

                # Calculate Frames Per Second (FPS)
                fps = 1 / (new_frame_time - prev_frame_time)
                prev_frame_time = new_frame_time
                
                # Render the final video output window
                if not headless:
                    cv2.putText(frame, f"Host Processing FPS: {int(fps)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                    cv2.imshow("Pure Host Processing", frame)
                    
                    # Press 'q' on the keyboard to safely exit the window
                    if cv2.waitKey(1) == ord('q'):
                        break

        except KeyboardInterrupt:
            print("\nStopping gracefully...")
        except Exception as e:
            print(f"Error encountered: {e}")
        finally:
            # Cleanup: Always close the socket and destroy windows before quitting
            sock.close()
            cv2.destroyAllWindows()

if __name__ == "__main__":
    main()