import serial
import time

ser = serial.Serial('/dev/serial0', 9600, timeout=3)
time.sleep(1)

for i in range(5):
    ser.write(b'B')
    time.sleep(0.5)

response = ser.read(50)
print('Response:', response)
ser.close()
