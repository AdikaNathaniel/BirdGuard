import serial
import time
import sys

port = sys.argv[1] if len(sys.argv) > 1 else "COM5"

ser = serial.Serial(port, 9600, timeout=0.1)
time.sleep(2.5)
boot = ser.read_all()
print(f"Initial boot text: {boot!r}")

print("\nSending b'o' and watching for 6 seconds (looking for reboot banner or any bytes)...")
ser.write(b"o")
ser.flush()
end = time.time() + 6
collected = b""
while time.time() < end:
    n = ser.in_waiting
    if n:
        collected += ser.read(n)
    time.sleep(0.05)
print(f"Collected: {collected!r}")

ser.close()
