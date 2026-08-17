import time
import serial

SERIAL_PORT = '/dev/serial0'
SERIAL_BAUD = 9600

print(f"Opening {SERIAL_PORT} @ {SERIAL_BAUD} baud...")
ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
time.sleep(2)  # let the Nano finish booting/resetting after the port opens
print("Port open.")

print("Sending 'o' (laser ON) -- watch the laser/relay now.")
ser.write(b'o')
time.sleep(3)

print("Sending 'f' (laser OFF).")
ser.write(b'f')
time.sleep(1)

ser.close()
print("Done. If the laser/relay did not react, see the checklist printed below.")
print("""
If nothing happened:
  1. Confirm wiring: Pi GND (pin 6) -> Nano GND, Pi TX (pin 8) -> Nano RX (D0).
     TX must go to RX, not TX to TX.
  2. Confirm the Nano is actually powered (USB or Pi 5V -> VIN) and running
     the sketch that handles 'o'/'f' (check its serial monitor separately,
     via USB from a PC, for the startup banner + "Laser ON"/"Laser OFF" prints).
  3. Confirm nothing else has /dev/serial0 open at the same time.
""")
