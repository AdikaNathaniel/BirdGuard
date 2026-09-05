# BirdGuard Pi Setup (from a fresh SD card)

Run these in order.

---

## 1. Find the Pi's IP address on the network

The Pi's IP is DHCP-assigned and changes depending on which network it's
on, so this is where a new user (or a new network) should always start --
any IP shown as an example anywhere in this guide is just from one
specific session, not a fixed address.

First, make sure `nmap` is installed on your own PC (not the Pi):

**Option A: winget**
```bash
winget install nmap
```

**Option B: Chocolatey (if you have it installed)**
```bash
choco install nmap
```

**Option C: Manual download**
If neither package manager is available, download the installer directly
from the official site: https://nmap.org/download.html

Once `nmap` is installed, scan your local network for live devices
(adjust the subnet if your router uses something other than
`192.168.0.x` -- check your PC's own IP to confirm):

```bash
nmap -sn 192.168.0.0/24
```

If this fails with `'nmap' is not recognized as an internal or external
command, operable program or batch file` even after installing it (common
right after a fresh install, before your terminal's PATH picks up the new
entry), run it with the full path directly instead. Nmap usually installs
to:

```bash
"C:\Program Files (x86)\Nmap\nmap.exe" -sn 192.168.0.0/24
```

This lists every responding device's IP and MAC address, but not which
one is the Pi by name. To identify it, open your router's admin panel
(e.g. `http://192.168.0.1/index.html#entry`, exact path varies by
router) and look at its connected-devices list for the entry named
`BirdGuard` (or similar) -- note its MAC address there, then match that
MAC address against the `nmap` scan output to find its current IP.

Once you have that IP, SSH in with it:

```bash
ssh pi@192.168.0.101
```

(where `192.168.0.101` is only an example -- substitute the real IP you
just found). You'll be prompted for a password -- it's `birdguard`.

If the Pi later drops off this address (new network, router reassigned a
different DHCP lease, etc.), re-run the `nmap` scan above rather than
assuming the old IP still works -- `hostname -I` on the Pi itself or the
router's connected-devices list both confirm the current address too.

---

## 2. Install system packages, enable I2C, create the venv, install Python packages

```bash
sudo apt update && sudo apt install -y python3-picamera2 python3-libcamera i2c-tools && sudo raspi-config nonint do_i2c 0 && python3 -m venv /home/pi/birdguard-env --system-site-packages && source /home/pi/birdguard-env/bin/activate && mkdir -p ~/pip-tmp && TMPDIR=~/pip-tmp pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu && TMPDIR=~/pip-tmp pip install opencv-python ultralytics pymongo adafruit-circuitpython-servokit && rm -rf ~/pip-tmp && rpicam-still --list-cameras && sudo i2cdetect -y 1
```

Chained with `&&` so it stops immediately if any step fails, rather than
continuing on top of a broken prior step. What it does, in order:

1. Updates apt.
2. Installs `picamera2`/`libcamera`/I2C tools system-wide -- `picamera2`
   specifically has to come from `apt`, not `pip`, since it depends on
   `libcamera` bindings built for the Pi's specific OS image.
3. Enables I2C non-interactively (`do_i2c 0` = enable) -- needed for the
   PCA9685 servo driver board.
4. Creates the Python virtual environment with `--system-site-packages`,
   so it can see the apt-installed `picamera2` without needing a separate
   (and less reliable) pip install of it inside the venv.
5. Installs `torch`/`torchvision` **first, from PyTorch's CPU-only wheel
   index**, before installing `ultralytics`.

   **Why this order matters:** a plain `pip install ultralytics` lets pip
   resolve whatever `torch` build it wants, and recent PyTorch ARM64
   wheels on the default index assume CUDA/GPU availability by default
   (NVIDIA also sells ARM+GPU hardware like Jetson, and pip can't tell a
   Raspberry Pi apart from one by platform tag alone) -- pulling in a
   454MB GPU build of `torch` plus 1GB+ of NVIDIA CUDA packages
   (`nvidia-cudnn-cu13`, etc.) that a Raspberry Pi has no GPU to ever use,
   and that are large enough to cause download timeouts on a slow
   connection. Installing the CPU-only build explicitly first means
   `ultralytics`'s own install sees that requirement already satisfied
   and skips pulling the GPU version at all.
6. Installs the remaining Python dependencies:
   - `opencv-python` -> `cv2`
   - `ultralytics` -> YOLOv8 (torch/torchvision already satisfied by
     step 5, so this stays lightweight)
   - `pymongo` -> MongoDB detection-logging client
   - `adafruit-circuitpython-servokit` -> PCA9685 servo control

   Both pip steps set `TMPDIR` to a folder on the real disk first (see
   below for why).
7. Runs two checks so you know immediately whether it worked: camera
   detection (`rpicam-still --list-cameras`) and an I2C bus scan
   (`sudo i2cdetect -y 1`, should show `40` if the PCA9685 is wired up).

**Why `TMPDIR` is redirected:** `pip` downloads/builds packages under
`/tmp` by default, which on this Pi is a small RAM-backed `tmpfs`, not
part of the main disk. A large download can exhaust that tmpfs and fail
with `OSError: [Errno 28] No space left on device` -- even while the
actual SD card still has plenty of room free (confirmed via `df -h /`
showing only 16% used, 48G available, while the failure was happening).
Pointing `TMPDIR` at `~/pip-tmp` (a real folder on disk) avoids this;
it's removed afterward since it's only scratch space.

If a step ever fails again with `No space left on device` despite
`TMPDIR` being set, first purge pip's own download cache (which can grow
large from partial/retried installs) before retrying:
```bash
pip cache purge
```

---

## 3. Verify everything actually works

Run each of these and check the output before trusting the setup is done.

```bash
python3 -c "import cv2, torch, pymongo; from ultralytics import YOLO; from adafruit_servokit import ServoKit; print('All imports OK')"
```
Should print `All imports OK` with no errors. If any import fails, that
specific package didn't install correctly -- re-run its `pip install`
line from step 2 with `TMPDIR` set, and read the actual error rather than
assuming it's the same tmpfs/CUDA issue again.

```bash
rpicam-still --list-cameras
```
Should list at least one camera (e.g. `imx708` or `imx219` depending on
which camera module is attached) with its supported resolutions/modes.
If nothing is listed, the camera ribbon cable is likely loose or the
camera isn't enabled -- check the physical connection and
`/boot/firmware/config.txt` for `camera_auto_detect=1`.

```bash
sudo i2cdetect -y 1
```
Should show `40` in the grid if the PCA9685 servo driver board is wired
and powered correctly. If the whole grid comes back empty (`--`
everywhere, no error about I2C being disabled), the I2C *interface*
itself is fine -- the board simply isn't responding, which almost always
means a physical wiring problem, not a software one:
- SDA (Pi GPIO2) -> PCA9685 SDA
- SCL (Pi GPIO3) -> PCA9685 SCL
- VCC (Pi 3.3V) -> PCA9685 VCC (logic power -- the board needs this
  just to show up on the scan, separate from V+/servo power)
- GND -> GND

A re-flashed SD card often means the Pi was physically handled/opened up
around the same time, so double-check nothing came loose during that.
