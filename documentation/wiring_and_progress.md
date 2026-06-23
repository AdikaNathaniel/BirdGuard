# BirdGuard — Wiring & Progress Documentation

## Project Overview
BirdGuard is an automated laser bird deterrent system. A Raspberry Pi 5 runs a YOLO-based
camera detector. When a bird (or person during testing) is detected, it sends a UART command
to an Arduino Nano which controls a pan-tilt laser module to deter the bird.

---

## Hardware Components
| Component | Details |
|-----------|---------|
| Single Board Computer | Raspberry Pi 5 |
| Camera | IMX708 (Pi Camera Module 3) — 4608x2592, up to 120fps |
| Microcontroller | Arduino Nano (ATmega328P, Optiboot bootloader) |
| Laser | Laser module on pin 5 (active LOW, via relay module) |
| Pan Servo | Connected to Nano pin 9 |
| Tilt Servo | Connected to Nano pin 10 |

---

## Wiring

### Pi → Nano UART (Working)
| Pi Physical Pin | Pi Function | Nano Pin | Notes |
|----------------|-------------|----------|-------|
| Pin 2 | 5V | VIN | Powers Nano when USB disconnected |
| Pin 6 | GND | GND | Shared ground reference |
| Pin 8 | TX (GPIO14) | D0 (RX) | Pi sends commands to Nano |

### Nano → Pi UART (Not yet wired — needs voltage divider)
```
Nano D1 (TX, 5V) ── 1kΩ ──┬── Pi Pin 10 (RX, 3.3V)
                            │
                           2kΩ
                            │
                           GND
```
> WARNING: Nano TX outputs 5V. Pi GPIO is 3.3V only.
> A 1kΩ/2kΩ voltage divider is required before connecting to Pi RX.

### Nano — Laser & Servos
| Nano Pin | Connected To |
|----------|-------------|
| D0 (RX) | Pi TX (pin 8) |
| D1 (TX) | (future) Pi RX via voltage divider |
| D5 | Laser module signal pin |
| D9 | Pan servo signal |
| D10 | Tilt servo signal |
| VIN | Pi 5V (pin 2) |
| GND | Pi GND (pin 6) |

---

## Pi UART Configuration

### Changes made to Pi 5
1. **Enabled UART** — added to `/boot/firmware/config.txt`:
   ```
   enable_uart=1
   ```

2. **Disabled serial console** — removed from `/boot/firmware/cmdline.txt`:
   ```
   console=serial0,115200   ← removed
   ```

3. **Serial port**: `/dev/serial0 → ttyAMA10`
4. **Baud rate**: 9600

---

## Arduino Nano — Upload Notes
- **Bootloader**: Optiboot at **115200 baud** (not old 57600 baud)
- **Upload method**: DTR auto-reset via FTDI chip (no manual button press needed)
- **IMPORTANT**: Disconnect Pi TX wire from Nano D0 before uploading from PC — it interferes with avrdude bootloader sync. Reconnect after upload.

### Upload command (from PC PowerShell)
```powershell
$port = New-Object System.IO.Ports.SerialPort("COM5", 115200)
$port.DtrEnable = $false; $port.Open()
Start-Sleep -Milliseconds 50
$port.DtrEnable = $true; Start-Sleep -Milliseconds 100
$port.DtrEnable = $false; $port.Close()
Start-Sleep -Milliseconds 200

$avrdude = "$env:USERPROFILE\.platformio\packages\tool-avrdude\avrdude.exe"
$conf = "$env:USERPROFILE\.platformio\packages\tool-avrdude\avrdude.conf"
$hex = "<path-to-firmware.hex>"
$flashArg = "flash:w:${hex}:i"
& $avrdude -C $conf -p atmega328p -c arduino -P COM5 -b 115200 -U $flashArg
```

---

## Nano Firmware — Command Reference
Sketch: `PlatformIO/pan_tilt_laser/src/main.cpp`

| Command | Action |
|---------|--------|
| `O` | Laser ON |
| `F` | Laser OFF |
| `W` | Tilt up (continuous) |
| `S` | Tilt down (continuous) |
| `A` | Pan left (continuous) |
| `D` | Pan right (continuous) |
| `I` | Nudge tilt up |
| `K` | Nudge tilt down |
| `J` | Nudge pan left |
| `L` | Nudge pan right |
| `X` or Space | Stop all motors |

---

## Software Stack

### Pi Packages Installed
```bash
pip install opencv-python ultralytics --break-system-packages
# picamera2 and numpy pre-installed with Pi OS
```

### YOLO Model
- **Model**: YOLOv8n (`yolov8n.pt`) — nano variant for Pi performance
- Auto-downloads on first run via ultralytics

---

## PlatformIO Projects

| Folder | Purpose |
|--------|---------|
| `PlatformIO/pan_tilt_laser/` | Main firmware — laser + servos + UART commands |
| `PlatformIO/blink_test/` | UART test — Pi sends 'B', Nano blinks LED |
| `PlatformIO/pin_detection/` | GND connectivity test sketch |

---

## Current Progress

### Completed
- [x] Pi Camera Module 3 (IMX708) detected and working
- [x] YOLOv8n running on Pi — detects person/bird/cat etc.
- [x] Pi UART enabled and configured (`/dev/serial0`)
- [x] Pi → Nano UART communication working (Pi TX → Nano D0)
- [x] Nano receives UART commands and controls laser relay
- [x] Real-time detection pipeline: Camera → YOLO → UART → Nano → Laser
- [x] Verified end-to-end: person detected → laser fires

### In Progress
- [ ] Resolve laser green light (direct pin 5 vs relay wiring — check laser module pinout)
- [ ] Wire Nano TX → Pi RX (voltage divider needed for 5V→3.3V)

### Remaining / Next Steps
- [ ] Change `TARGET_CLASS` from `"person"` to `"bird"` for production
- [ ] Implement pan-tilt aiming — send servo commands based on detected bird's bounding box position
- [ ] Add bidirectional UART (Nano confirms commands back to Pi)
- [ ] Field test with actual birds

---

## SSH & Network
| | |
|-|--|
| Pi hostname | BirdGuard |
| Pi IP | 192.168.43.190 |
| SSH user | pi |
| SSH password | birdguard2024 |
| Network | Mobile hotspot |
