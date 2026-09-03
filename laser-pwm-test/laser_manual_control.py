# Manual interactive laser control over the Pi<->Nano UART link -- types
# single-character commands ('o'/'f') to the Nano, which handles the
# actual laser GPIO on its end; this script only talks serial, no direct
# GPIO/laser hardware access from the Pi itself.
import time
import serial

SERIAL_PORT = '/dev/serial0'
SERIAL_BAUD = 9600

print(f"Opening {SERIAL_PORT} @ {SERIAL_BAUD} baud...")
ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
time.sleep(2)  # let the Nano finish booting/resetting after the port opens
print("Port open.")
print("Type 'o' + Enter to turn laser ON, 'f' + Enter to turn it OFF, 'q' + Enter to quit.\n")

try:
    while True:
        cmd = input("> ").strip().lower()
        if cmd == 'q':
            break
        elif cmd in ('o', 'f'):
            ser.write(cmd.encode())
            print(f"Sent {cmd!r}")
        else:
            print("Type 'o', 'f', or 'q'.")
finally:
    ser.close()
    print("Port closed.")
