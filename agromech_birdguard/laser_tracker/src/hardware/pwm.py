"""PCA9685 PWM controller over I2C (Adafruit ServoKit)."""
from adafruit_servokit import ServoKit


class PWMController:
    def __init__(self, address=0x40, channels=16, frequency_hz=50,
                 servo_min_us=500, servo_max_us=2500):
        self.kit = ServoKit(channels=channels, address=address)
        #self.kit.frequency = frequency_hz
        for ch in range(channels):
            self.kit.servo[ch].set_pulse_width_range(servo_min_us, servo_max_us)

    def set_angle(self, channel, angle):
        self.kit.servo[channel].angle = max(0, min(180, angle))

    def release(self):
        for ch in range(16):
            self.kit.servo[ch].angle = None   # stop holding torque
