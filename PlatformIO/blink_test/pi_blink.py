import serial
import time

# Minimal serial smoke test -- confirms the Pi<->Nano UART link is alive
# by sending a known byte ('B') a few times and printing back whatever
# the Nano's blink-test sketch responds with.
ser = serial.Serial('/dev/serial0', 9600, timeout=3)
time.sleep(1)  # let the Nano finish booting/resetting after the port opens

for i in range(5):
    ser.write(b'B')
    time.sleep(0.5)

response = ser.read(50)
print('Response:', response)
ser.close()
