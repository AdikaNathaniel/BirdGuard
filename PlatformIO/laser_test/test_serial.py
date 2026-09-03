import serial
import time
import sys

# Sends the laser-on command ('o') to the Nano and captures anything it
# sends back over the next 6 seconds -- used to check whether the Nano
# reboots or prints unexpected output in response, not just whether the
# laser physically turns on.
port = sys.argv[1] if len(sys.argv) > 1 else "COM5"

ser = serial.Serial(port, 9600, timeout=0.1)
time.sleep(2.5)  # let the Nano finish booting/resetting after the port opens
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
