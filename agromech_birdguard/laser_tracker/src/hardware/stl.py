from adafruit_servokit import ServoKit
import time

kit = ServoKit(channels=16)
# Standard neutral pulse for RC servos is ~1500us (angle 90)
kit.servo[2].set_pulse_width_range(500, 2500)

print("Commanding Neutral (90 deg)...")
kit.servo[2].angle = 90
time.sleep(3)

print("Commanding 95 deg...")
kit.servo[2].angle = 95
time.sleep(3)

print("Releasing...")
kit.servo[2].angle = None
