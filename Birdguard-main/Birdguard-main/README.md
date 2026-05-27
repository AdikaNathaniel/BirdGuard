# Bird Project Vision

A production grade spatial AI microservice for the Raspberry Pi 5 and Luxonis OAK-D Lite. This service detects birds in real time, calculates their 3D coordinates in millimeters, and broadcasts the data via UDP.

## Technical Overview

The service utilizes the DepthAI V3 API to orchestrate a high performance pipeline on the Myriad X VPU:

1. Unified Camera Node: Manages the IMX214 color sensor and OV7251 mono sensors.
2. StereoDepth Node: Generates a depth map aligned to the color sensor with undistortion enabled for spatial accuracy.
3. SpatialDetectionNetwork: Runs a YOLOv10 Nano model for object detection and maps bounding boxes to depth data for 3D localization.
4. ObjectTracker Node: Provides temporal consistency by assigning persistent IDs to detected objects across frames.

## Requirements

* Hardware: Raspberry Pi 5, Luxonis OAK-D Lite.
* Software: Python 3.11 or higher, `uv` package manager.
* Core Libraries: `depthai`, `opencv-python`, `blobconverter`.

## Linux Setup (Raspberry Pi 5)

While this code can be run on Windows for testing, deployment on Linux (Raspberry Pi OS) requires configuring USB permissions for the Myriad X VPU.

1. Configure udev rules:
```bash
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666"' | sudo tee /etc/udev/rules.d/80-movidius.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

2. Troubleshooting:
If you encounter USB connection issues or the device is not detected, refer to the official Luxonis USB Deployment Guide:
https://docs.luxonis.com/hardware/platform/deploy/usb-deployment-guide/

## Installation

Install the required dependencies using `uv`:

```bash
uv add depthai opencv-python blobconverter
```

## Usage

### 1. Start the Microservice

The detector runs in headless mode by default for maximum performance on edge hardware.

```bash
# Production mode (Headless)
uv run .\bird_detector.py

# Debug mode (Display window + detect all objects)
uv run .\bird_detector.py --headless False --debug
```

### 2. Receive Data

A separate script can listen to the UDP broadcast on port 5005.

```bash
uv run .\udp_receiver_example.py
```

## Data Schema

The service broadcasts JSON payloads via UDP.

### Object Detection Payload

```json
{
  "timestamp": 1713962400.123,
  "id": 1,
  "label": "bird",
  "spatial": {
    "x_mm": 150,
    "y_mm": -20,
    "z_mm": 4500
  },
  "bbox": {
    "x1": 100,
    "y1": 150,
    "x2": 250,
    "y2": 300
  }
}
```

### System Heartbeat

The service sends a heartbeat every 10 seconds to indicate health.

```json
{
  "status": "active",
  "timestamp": 1713962410.123
}
```

## Performance Optimizations

* Resolution: RGB stream is locked to 416x416 to ensure transformation data alignment and prevent memory exhaustion on OAK-D Lite.
* Threading: Non blocking output queues with maxSize 1 are used to prevent latency accumulation.
* Hardware: Median filtering is disabled to optimize VPU memory bandwidth.
