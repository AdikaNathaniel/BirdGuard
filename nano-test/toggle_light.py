"""Bridge Pi person-detection signals (UDP) to the Arduino Nano laser (serial).

picam_detector.py sends a UDP packet to 127.0.0.1:5005 every time it sees the
target class. This script listens for those packets and forwards on/off
commands to the Nano over serial, turning the laser on while signals keep
arriving and off again after a short gap with no signal.

Usage:
    python toggle_light.py <port> [--udp-ip HOST] [--udp-port PORT] [--off-delay SECONDS]

Example (running on the Pi itself, alongside picam_detector.py):
    python toggle_light.py /dev/serial0

Example (Windows bench test):
    python toggle_light.py COM5 --udp-port 5005
"""

import argparse
import json
import socket
import sys
import time

import serial

BAUD_RATE = 9600
LASER_ON = b"o"   # Nano: analogWrite(D5, 255) -- see LASER_PIN in main.cpp
LASER_OFF = b"f"  # Nano: analogWrite(D5, 0)

UDP_IP = "127.0.0.1"   # matches picam_detector.py UDP_IP
UDP_PORT = 5005        # matches picam_detector.py UDP_PORT
OFF_DELAY = 3.0         # seconds without a detection signal before turning off


def bridge(port: str, udp_ip: str, udp_port: int, off_delay: float):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((udp_ip, udp_port))
    sock.settimeout(0.5)

    try:
        with serial.Serial(port, BAUD_RATE, timeout=1) as arduino:
            time.sleep(2)  # wait for Nano to reset after serial connection opens

            laser_on = False
            last_signal_time = 0.0
            print(f"Listening for detections on {udp_ip}:{udp_port}, forwarding to {port} @ {BAUD_RATE} baud. Ctrl+C to stop.")

            try:
                while True:
                    try:
                        data, _ = sock.recvfrom(4096)
                    except socket.timeout:
                        data = None

                    if data is not None:
                        last_signal_time = time.time()

                        label = "?"
                        try:
                            label = json.loads(data.decode()).get("label", "?")
                        except (ValueError, UnicodeDecodeError):
                            pass

                        if not laser_on:
                            arduino.write(LASER_ON)
                            laser_on = True
                            print(f"Laser ON ({label} detected)")

                    elif laser_on and (time.time() - last_signal_time) > off_delay:
                        arduino.write(LASER_OFF)
                        laser_on = False
                        print("Laser OFF (no signal)")

            except KeyboardInterrupt:
                arduino.write(LASER_OFF)
                print("\nStopped. Laser OFF.")
    finally:
        sock.close()


def main():
    parser = argparse.ArgumentParser(description="Bridge Pi detection signals (UDP) to the Arduino Nano laser (serial).")
    parser.add_argument("port", help="Serial port to the Nano (e.g. /dev/serial0 on the Pi, COM5 on Windows)")
    parser.add_argument("--udp-ip", default=UDP_IP, help=f"UDP address to listen on (default: {UDP_IP})")
    parser.add_argument("--udp-port", type=int, default=UDP_PORT, help=f"UDP port to listen on (default: {UDP_PORT})")
    parser.add_argument("--off-delay", type=float, default=OFF_DELAY, help=f"Seconds without a signal before turning laser off (default: {OFF_DELAY})")
    args = parser.parse_args()

    try:
        bridge(args.port, args.udp_ip, args.udp_port, args.off_delay)
    except serial.SerialException as e:
        print(f"Serial error: {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"UDP socket error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
