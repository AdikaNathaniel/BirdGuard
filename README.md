# BirdGuard

An automated bird deterrent system that detects birds (or, in the current test configuration, people) in real time using a Raspberry Pi camera and drives a laser-mounted pan-tilt turret via an Arduino Nano to scare them off.

## How It Works

1. A Raspberry Pi 5 with an Arducam 64MP camera module captures a live video feed.
2. An RF-DETR Nano object detection model (running on-device via `picamera2`) identifies the target class in each frame.
3. On detection, the Pi sends a single-character command over UART to an Arduino Nano.
4. The Nano fires a relay-driven laser and (optionally) aims a pan-tilt servo mount at the target.
5. Detections are also broadcast over UDP and logged, with annotated video saved locally for review.

```
Arducam 64MP → Raspberry Pi 5 (RF-DETR Nano detector) → UART → Arduino Nano → Laser + Pan-Tilt Servos
```

## Repository Layout

| Path | Purpose |
|---|---|
| `picam-test/picam_detector.py` | Main detection pipeline: Arducam capture + RF-DETR inference + UART trigger + video recording |
| `rfdetr-arducam/rf_detr-detector.py` | Standalone RF-DETR detector variant |
| `pi-laser/laser_control.py` | Pi-side laser control test script |
| `nano-test/toggle_light.py` | Simple Nano UART test (toggle light/relay) |
| `PlatformIO/pan_tilt_laser/` | Arduino Nano firmware (PlatformIO project) for pan-tilt servos + laser |
| `setup/setup.sh` | Raspberry Pi provisioning script (system deps, Python venv, model deps) |
| `PinOut/` | Wiring/pinout references |
| `Designs/` | Hardware/mechanical design files |
| `commands/` | Command log / notes |
| `documentation/` | Project documentation |
| `Research/` | Background research |

## Hardware

- Raspberry Pi 5
- Arducam 64MP camera module
- Arduino Nano
- Pan-tilt servo mount (continuous-rotation servos, open-loop — no positional feedback)
- Relay-driven laser module

### Wiring (Pi → Nano UART)

| Pi Pin | Nano Pin |
|---|---|
| Pin 8 (TX / GPIO14) | D0 (RX) |
| Pin 6 (GND) | GND |
| Pin 2 (5V) | VIN |

Serial: `/dev/serial0`, 9600 baud.

## Setup

On a freshly flashed Raspberry Pi OS:

```bash
bash setup/setup.sh
```

This installs system dependencies (`libcamera`, `picamera2`), creates a Python virtual environment at `~/birdguard-env`, and installs the detection stack (`rfdetr`, `opencv-python`, `depthai`, `supervision`, `ultralytics`, `picamera2`).

Flash the Arduino Nano firmware from `PlatformIO/pan_tilt_laser/` using PlatformIO.

## Running the Detector

```bash
ssh pi@<pi-ip>
cd ~/picam-test
source ~/birdguard-env/bin/activate
python picam_detector.py
```

Stop with `Ctrl+C`. Video and detection snapshots are saved under `~/birdguard-test/session_<timestamp>/`.

### Config (`picam_detector.py`)

| Setting | Default | Notes |
|---|---|---|
| `TARGET_CLASS` | `"person"` | Change to `"bird"` for production |
| `CONFIDENCE_THRESHOLD` | `0.5` | |
| `LASER_OFF_DELAY` | `3.0`s | How long the laser stays on after the last detection |
| `FRAME_WIDTH` / `FRAME_HEIGHT` | `640x480` | |
| `VIDEO_FPS` | `30` | |

## Arduino Nano Firmware Commands

Single-character commands over USB/UART serial (9600 baud):

| Command | Action |
|---|---|
| `w` / `s` | Tilt up / down (continuous) |
| `a` / `d` | Pan left / right (continuous) |
| `i` / `k` | Tilt nudge (55ms pulse) |
| `j` / `l` | Pan nudge (55ms pulse) |
| `o` | Laser ON |
| `f` | Laser OFF |
| `x` / space | Stop all motors |

## Status

- ✅ RF-DETR Nano detection pipeline working end-to-end on the Arducam feed
- ✅ Pi → Nano UART link proven (detection triggers laser relay)
- ✅ Arducam 64MP integrated and tuned for the detection pipeline
- ⏳ Pan-tilt aiming not yet integrated with detection (currently laser-only trigger)
- ⏳ Nano → Pi return channel not yet wired (needs voltage divider)
