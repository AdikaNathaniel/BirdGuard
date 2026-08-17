import time
import serial

SERIAL_PORT = '/dev/serial0'
SERIAL_BAUD = 9600

print(f"Opening {SERIAL_PORT} @ {SERIAL_BAUD} baud...")
ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=2)
time.sleep(2)  # let the Nano finish booting/resetting after the port opens
ser.reset_input_buffer()

def send_and_listen(cmd, label):
    print(f"\nSending {label!r}...")
    ser.write(cmd)
    time.sleep(0.5)
    reply = ser.read(ser.in_waiting or 1)
    if reply:
        print(f"Got back: {reply!r}")
    else:
        print("No reply received.")

send_and_listen(b'o', "o (laser ON)")
send_and_listen(b'f', "f (laser OFF)")

ser.close()
print("""
If you saw "Got back: b'Laser ON\\r\\n'" (and similarly for OFF), the full
round-trip Pi -> Nano -> Pi link is confirmed working -- both wires and the
voltage divider are good.

If "No reply received" both times, check:
  1. Voltage divider wiring: Nano TX -> 1k -> (junction -> Pi RX) -> 2k -> GND
  2. Pi TX -> Nano RX and Pi GND -> Nano GND still connected
  3. Nano is powered and running a sketch that Serial.println()s on 'o'/'f'
     (your existing pan_tilt_laser.ino does this already)
""")
