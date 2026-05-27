#!/bin/bash
# BirdGuard Pi Setup Script
# Run this after flashing a fresh Raspberry Pi OS
# Usage: bash setup.sh

echo "======================================"
echo "  BirdGuard Pi Setup"
echo "======================================"

# Step 1 - System update
echo ""
echo "[1/5] Updating system packages..."
sudo apt update && sudo apt full-upgrade -y

# Step 2 - Install system dependencies
echo ""
echo "[2/5] Installing system dependencies..."
sudo apt install -y libcap-dev python3-libcamera python3-picamera2

# Step 3 - Create virtual environment with system packages
echo ""
echo "[3/5] Creating virtual environment..."
python3 -m venv /home/pi/birdguard-env --system-site-packages
source /home/pi/birdguard-env/bin/activate

# Step 4 - Install Python dependencies
echo ""
echo "[4/5] Installing Python dependencies..."
pip install --resume-retries 5 \
    blobconverter \
    depthai \
    opencv-python \
    supervision \
    ultralytics \
    picamera2

# Step 5 - Copy BirdGuard project files
echo ""
echo "[5/5] Setup complete!"
echo ""
echo "======================================"
echo "  To run the detector:"
echo "  source /home/pi/birdguard-env/bin/activate"
echo "  python /home/pi/picam-test/picam_detector.py"
echo "======================================"
