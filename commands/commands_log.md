# BirdGuard Command Log

---

## PlatformIO / Arduino

### Upload firmware to Arduino Nano
```bash
pio run --target upload
```

### Open serial monitor
```bash
pio device monitor --port COM5 --baud 9600
```

### List connected serial devices
```bash
pio device list
```

---

## Serial Monitor Controls (pan-tilt-laser)

| Key | Action |
|-----|--------|
| `w` | Tilt continuous up |
| `s` | Tilt continuous down |
| `a` | Pan continuous left |
| `d` | Pan continuous right |
| `i` | Nudge tilt up |
| `k` | Nudge tilt down |
| `j` | Nudge pan left |
| `l` | Nudge pan right |
| `o` | Laser ON |
| `f` | Laser OFF |
| `space` / `x` | Stop all motors |

---

## SSH & Networking

### Clear old SSH host key
```bash
ssh-keygen -R 192.168.43.190
```

### SSH into the Pi
```bash
ssh pi@192.168.43.190
```

### Scan network for Pi IP
```bash
arp -a
```

---

## File Transfer (PC ↔ Pi)

### Copy detector script to Pi
```bash
scp "C:\Users\23324\Desktop\Projects\BirdGuard\picam-test\picam_detector.py" pi@192.168.43.190:/home/pi/picam_detector.py
```

### Copy setup script to Pi
```bash
scp "C:\Users\23324\Desktop\Projects\BirdGuard\setup\setup.sh" pi@192.168.43.190:/home/pi/setup.sh
```

### Copy session results from Pi to PC
```bash
scp -r pi@192.168.43.190:/home/pi/birdguard-test/ "C:\Users\23324\Desktop\Projects\BirdGuard\picam-test\detections"
```

---

## Raspberry Pi Setup (run on Pi via SSH)

### Run setup script
```bash
bash setup.sh
```

### Create virtual environment
```bash
python3 -m venv /home/pi/birdguard-env --system-site-packages
```

### Activate virtual environment
```bash
source /home/pi/birdguard-env/bin/activate
```

### Install all Python packages
```bash
pip install ultralytics opencv-python supervision picamera2 depthai blobconverter
```

### Check if camera is detected
```bash
python3 -c "from picamera2 import Picamera2; print(Picamera2.global_camera_info())"
```

### Check camera config
```bash
grep -i camera /boot/firmware/config.txt
```

### Enable camera in config
```bash
sudo nano /boot/firmware/config.txt
# Add: camera_auto_detect=1
```

### Enable SSH on Pi
```bash
sudo systemctl enable ssh && sudo systemctl start ssh
```

### Run the bird detector
```bash
source /home/pi/birdguard-env/bin/activate && python picam_detector.py
```

### Set up SSH keys from Pi to PC (for auto-transfer)
```bash
ssh-keygen -t ed25519
ssh-copy-id 23324@192.168.43.116
```

---

## Windows OpenSSH Server Setup (run in PowerShell as Admin)

### Install OpenSSH Server
```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
```

### Start and enable SSH service
```powershell
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic
```

---

## Session Results Location (on Pi)

- **Video:** `/home/pi/birdguard-test/<session_name>/recording.mp4`
- **Annotated images:** `/home/pi/birdguard-test/<session_name>/detections/`
