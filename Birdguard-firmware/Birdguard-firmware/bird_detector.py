import cv2
import depthai as dai
import time
import socket
import json
import argparse

# --- Configuration ---
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
BIRD_LABEL_ID = 14 

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
    print(f"Starting Bird Detector with the OAK-D Lite...")

    # 3. Create Pipeline
    # Runs entirely on the OAK-D Lite's own onboard processor (not the
    # host CPU) -- the host just receives already-processed tracklet
    # results over USB, unlike the Pi-camera scripts elsewhere in this
    # project which do inference on the Pi's own CPU.
    pipeline = dai.Pipeline()

    # CAM_A is the color camera (used for detection), CAM_B/C are the
    # left/right mono cameras feeding stereo depth -- this is what lets
    # the device report real-world X/Y/Z spatial coordinates per
    # detection, not just a 2D pixel bounding box.
    camRgb = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_A)
    monoLeft = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_B)
    monoRight = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_C)

    stereo = pipeline.create(dai.node.StereoDepth)
    leftOutput = monoLeft.requestOutput((640, 400))
    rightOutput = monoRight.requestOutput((640, 400))
    leftOutput.link(stereo.left)
    rightOutput.link(stereo.right)

    # Combines the RGB detector (YOLOv10-nano) with the stereo depth map
    # so each detection carries a real-world distance, not just a 2D box.
    spatialDetectionNetwork = pipeline.create(dai.node.SpatialDetectionNetwork).build(camRgb, stereo, "yolov10-nano")
    objectTracker = pipeline.create(dai.node.ObjectTracker)

    spatialDetectionNetwork.setConfidenceThreshold(0.6)
    spatialDetectionNetwork.input.setBlocking(False)
    spatialDetectionNetwork.setBoundingBoxScaleFactor(0.5)
    # Ignore depth readings outside this range (mm) -- filters out noise
    # from objects too close to focus or too far for reliable stereo depth.
    spatialDetectionNetwork.setDepthLowerThreshold(100)
    spatialDetectionNetwork.setDepthUpperThreshold(5000)
    labelMap = spatialDetectionNetwork.getClasses()

    # Apply filtering only if not in debug -- in debug mode every detected
    # class gets tracked/logged, useful for confirming the pipeline works
    # at all before narrowing down to just BIRD_LABEL_ID.
    if not debug_mode:
        objectTracker.setDetectionLabelsToTrack([BIRD_LABEL_ID])

    objectTracker.setTrackerType(dai.TrackerType.SHORT_TERM_IMAGELESS)
    objectTracker.setTrackerIdAssignmentPolicy(dai.TrackerIdAssignmentPolicy.SMALLEST_ID)

    # Output queues the host-side loop below reads from -- the device
    # keeps pushing frames/tracklets into these independently of when the
    # host actually calls .get() on them.
    preview = objectTracker.passthroughTrackerFrame.createOutputQueue()
    tracklets = objectTracker.out.createOutputQueue()

    # Wires the pipeline stages together: detections flow into the
    # tracker, which assigns persistent IDs across frames (so the same
    # bird keeps the same `t.id` as it moves, rather than being treated
    # as a brand-new detection every frame).
    spatialDetectionNetwork.passthrough.link(objectTracker.inputTrackerFrame)
    spatialDetectionNetwork.passthrough.link(objectTracker.inputDetectionFrame)
    spatialDetectionNetwork.out.link(objectTracker.inputDetections)

    try:
        pipeline.start()
        print("Pipeline active. Waiting for detections...")

        while pipeline.isRunning():
            imgFrame = preview.get()
            track = tracklets.get()
            
            frame = imgFrame.getCvFrame()
            trackletsData = track.tracklets
            
            for t in trackletsData:
                # Tracklet ROI is stored normalized (0-1); denormalize
                # against the actual frame size to get real pixel coords.
                roi = t.roi.denormalize(frame.shape[1], frame.shape[0])
                x1 = int(roi.topLeft().x)
                y1 = int(roi.topLeft().y)
                x2 = int(roi.bottomRight().x)
                y2 = int(roi.bottomRight().y)

                try:
                    label = labelMap[t.label]
                except:
                    label = t.label

                # Extract spatial coordinates
                x, y, z = int(t.spatialCoordinates.x), int(t.spatialCoordinates.y), int(t.spatialCoordinates.z)

                # Payload creation
                payload = {
                    "timestamp": time.time(),
                    "id": t.id,
                    "label": str(label),
                    "spatial": {"x_mm": x, "y_mm": y, "z_mm": z},
                    "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
                }
                sock.sendto(json.dumps(payload).encode('utf-8'), (UDP_IP, UDP_PORT))

                # Logging
                if debug_mode or t.label == BIRD_LABEL_ID:
                    print(f"[{str(label).upper()}] ID:{t.id} | X:{x}mm Y:{y}mm Z:{z}mm")

                # UI Overlay (only if not headless)
                if not headless:
                    cv2.putText(frame, str(label), (x1 + 10, y1 + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, (255,255,255))
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 1)

            if not headless:
                cv2.imshow("Bird Detector", frame)
                if cv2.waitKey(1) == ord('q'):
                    break

    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        pipeline.stop()
        sock.close()
        if not headless:
            cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
