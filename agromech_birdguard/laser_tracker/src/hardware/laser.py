"""Laser switch through a MOSFET driven by a GPIO pin."""
from gpiozero import DigitalOutputDevice


class Laser:
    def __init__(self, pin, active_high=True):
        self._device = DigitalOutputDevice(
            pin, active_high=active_high, initial_value=False)

    def on(self):
        self._device.on()

    def off(self):
        self._device.off()

    def close(self):
        self._device.close()