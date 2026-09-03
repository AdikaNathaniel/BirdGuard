import cv2
import time
import socket
import json
import argparse
from ultralytics import YOLO

# --- Configuration ---
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
BIRD_LABEL_ID = 14 

# Simulation Constants (Rough estimates for depth estimation)
KNOWN_BIRD_WIDTH_MM = 150 
FOCAL_LENGTH_PIXELS = 500
CX, CY = 320, 240

def main():
    # 1. Argument Parsing
    parser = argparse.ArgumentParser()
    parser.add_argument('-hl', '--headless', type=str, default="True", help="Run in headless mode (True/False). Default: True")
    parser.add_argument('-d', '--debug', action='store_true', help="Debug mode: Detect ALL objects.")
    args = parser.parse_args()

    headless = args.headless.lower() == "true"
    debug_mode = args.debug

    # 2. UDP Setup
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print("Starting No-OAK Bird Detector with Inbuilt Camera...")

    # 3. Model Setup (Running YOLO on CPU locally)
    model = YOLO("yolov10n.pt") 

    # 4. Inbuilt Camera Setup
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open inbuilt camera.")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    try:
        print("Processing camera feed. Press 'q' to quit.")

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Run YOLO detection
            # classes filter: only birds unless debug
            target_classes = None if debug_mode else [BIRD_LABEL_ID]
            results = model(frame, classes=target_classes, verbose=False)[0]
            
            # Iterate through detections
            for result in results.boxes:
                # Extract coordinates (xyxy)
                box = result.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = map(int, box)
                
                conf = float(result.conf[0])
                cls = int(result.cls[0])
                label = model.names[cls]

                # --- Imitation Depth / Spatial Math ---
                # Since this is "no oak" (no stereo depth sensor like the
                # OAK-D Lite scripts have), depth is *estimated* here from
                # bounding-box size alone -- assumes birds are roughly a
                # known real-world width, so a smaller box implies farther
                # away. Much less accurate than real stereo depth, but
                # needs only a single regular webcam.
                box_w = x2 - x1
                box_h = y2 - y1
                center_x = x1 + box_w // 2
                center_y = y1 + box_h // 2
                
                # Z = (Known Width * Focal Length) / Pixel Width
                z_mm = int((KNOWN_BIRD_WIDTH_MM * FOCAL_LENGTH_PIXELS) / box_w) if box_w > 0 else 0
                
                # X and Y in 3D space
                x_mm = int((center_x - CX) * z_mm / FOCAL_LENGTH_PIXELS)
                y_mm = int((center_y - CY) * z_mm / FOCAL_LENGTH_PIXELS)

                # Payload creation
                payload = {
                    "timestamp": time.time(),
                    "id": 0, # Note: Standard YOLO without tracker doesn't have unique IDs
                    "label": str(label),
                    "spatial": {"x_mm": x_mm, "y_mm": y_mm, "z_mm": z_mm},
                    "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
                }
                sock.sendto(json.dumps(payload).encode('utf-8'), (UDP_IP, UDP_PORT))

                # Logging
                if debug_mode or cls == BIRD_LABEL_ID:
                    print(f"[{str(label).upper()}] | X:{x_mm}mm Y:{y_mm}mm Z:{z_mm}mm (est)")

                # UI Overlay
                if not headless:
                    cv2.putText(frame, f"{label} {conf:.2f}", (x1 + 10, y1 + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, (0, 255, 0), 1)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 1)

            if not headless:
                cv2.imshow("No-OAK Bird Detector", frame)
                if cv2.waitKey(1) == ord('q'):
                    break

    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cap.release()
        sock.close()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
