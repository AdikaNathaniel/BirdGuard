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

## GPIO Control (Pi -> Nano laser bridge)

### Drive GPIO12 HIGH (laser ON signal)
```bash
pinctrl set 12 op dh
```

### Drive GPIO12 LOW (laser OFF signal)
```bash
pinctrl set 12 op dl
```

### Read back GPIO12 state
```bash
pinctrl get 12
```

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

### SSH into the Pi (current IP as of this session -- Pi's DHCP-assigned
### address changes over time, always confirm before relying on either)
```bash
ssh pi@192.168.43.233
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

### Check if camera is detected (libcamera, alternative)
```bash
rpicam-still --list-cameras
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

## Servo / PCA9685 Motor Control

### Run the pan/tilt motor driver
Interactive typed-command control: `u1`-`u10`/`d1`-`d10` step pan
(channel 0), `i1`-`i10`/`k1`-`k10` step tilt (channel 4), `c` recenters
both, `s` releases both, Ctrl+C to quit.
```bash
cd ~/BirdGuard/pi-driver-motor
source ~/birdguard-env/bin/activate
python pi_driver_motor.py
```

### Run the servo stop-point / duty-cycle calibration tool
Prompts for a channel, then accepts: `<number>` (set angle and hold),
`p<number>` (pulse for a default duration then auto-release),
`p<number>,<seconds>` (pulse for an exact duration, e.g. `p180,1.77`),
`t<number>` (send the angle and time how long until you press Enter at
the target position), `r` (release now), `q` (quit).
```bash
cd ~/BirdGuard/pi-driver-motor
source ~/birdguard-env/bin/activate
python pi_servo_calibrate.py
```

### Emergency-release a stuck/spinning servo
Use when a servo (pan channel 0, tilt channel 4) is still moving/spinning
and won't stop on its own -- e.g. after killing a detector script that
didn't clean up, or after a calibration test left a channel holding a
signal. Cuts the PWM signal on both channels entirely rather than trying
to re-center, since a miscalibrated or continuous-rotation servo may keep
moving even when told to go back to 90 degrees.
```bash
source ~/birdguard-env/bin/activate
python3 -c "from adafruit_servokit import ServoKit; kit = ServoKit(channels=16); kit.servo[0].angle = None; kit.servo[4].angle = None"
```

### Run the GPIO15 formula trial (RPi.GPIO software PWM)
Standalone, no PCA9685 -- one servo directly on GPIO15. Enter an angle
(0-180) to compute it via the given duty-cycle formula and move the
servo; `r` releases, `q` quits.
```bash
cd ~/BirdGuard/PI-SERVO-FORMULA-TRIALS
source ~/birdguard-env/bin/activate
python pi_servo_formula_trial.py
```

### Run the GPIO15 formula trial (gpiozero AngularServo variant)
Same GPIO15 servo, driven via `gpiozero.AngularServo` instead of raw
`RPi.GPIO`. Enter an angle (0-180) at the prompt; Ctrl+C to stop.
```bash
cd ~/BirdGuard/PI-SERVO-FORMULA-TRIALS
source ~/birdguard-env/bin/activate
python pi_servo_formula_trial_2.py
```

### Install/replace GPIO library for Pi 5 compatibility
`RPi.GPIO` fails on the Pi 5 (`RuntimeError: Cannot determine SOC
peripheral base address`) -- `rpi-lgpio` is a drop-in replacement that
supports the Pi 5's hardware under the same `RPi.GPIO` import name.
```bash
pip uninstall RPi.GPIO -y
pip install rpi-lgpio
```

### Scan the I2C bus for the PCA9685
Confirms the board is actually detected (should show address `40`) before
suspecting a software/calibration issue.
```bash
sudo i2cdetect -y 1
```

---

## Person Detector Process Management

### Run the person detector manually (foreground, for live debug output)
```bash
cd ~/BirdGuard/pi-nano-laser
source ~/birdguard-env/bin/activate
python -u pi_person_detector_cpu.py
```

### Run the pan/tilt-tracking detector variant manually
```bash
cd ~/BirdGuard/pi-nano-laser
source ~/birdguard-env/bin/activate
python -u pi_person_detector_cpu_offset.py
```

### Check whether a detector is already running (and holding the camera)
```bash
pgrep -af person_detector
```

### Check which process actually has the camera device open
Useful when `pgrep` finds nothing but the camera still reports
"Device or resource busy" -- catches orphaned/stuck handles.
```bash
sudo fuser -v /dev/video* /dev/media*
```

### Kill a stuck detector process to free the camera
```bash
pkill -f pi_person_detector_cpu.py
# or, for the tracking variant:
pkill -f pi_person_detector_cpu_offset.py
```

---

## Tailscale Diagnostics & Recovery

### Check Tailscale status and peer list
```bash
tailscale status
```

### Ping the backend over the tailnet (confirms the tunnel is actually alive)
```bash
tailscale ping -c 3 birdguard-backend-1
```

### Bounce Tailscale on the Pi (fixes most stale-connection episodes)
```bash
sudo tailscale down
sudo tailscale up
```

### Manually trigger the Tailscale self-heal watchdog and read its log
```bash
sudo systemctl start birdguard-tailscale-heal.service
journalctl -u birdguard-tailscale-heal.service -n 20 --no-pager
```

### Check when the watchdog last ran / will next run
```bash
systemctl list-timers birdguard-tailscale-heal.timer
```

---

## Fly.io Backend Management (run from the Windows dev PC, in `birdguard-backend/`)

### Check machine status
```bash
flyctl status
```

### Tail live logs (filter for errors as needed)
```bash
flyctl logs
```

### Deploy backend changes
```bash
flyctl deploy
```

### Restart the machine (fixes a wedged Tailscale daemon)
```bash
flyctl machine restart <machine-id>
```

### Stop + start the machine (forces a reschedule onto different
### hardware -- use when a plain restart doesn't clear a host-level
### networking fault, e.g. Tailscale can't reach its coordination
### servers, MongoDB DNS failing)
```bash
flyctl machine stop <machine-id>
flyctl machine start <machine-id>
```

---

## Session Results Location (on Pi)

- **Video:** `/home/pi/birdguard-test/<session_name>/recording.mp4`
- **Annotated images:** `/home/pi/birdguard-test/<session_name>/detections/`
