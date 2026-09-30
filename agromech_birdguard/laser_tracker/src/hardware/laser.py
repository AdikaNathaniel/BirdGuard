"""Laser = power relay (cuts the laser PSU) + trigger signal (Pi -> Nano D2 -> D6).

Both start OFF and are always switched together: relay first on the way up,
trigger first on the way down.
"""
import time
from gpiozero import DigitalOutputDevice


class Laser:
    def __init__(self, pin, active_high=True, relay_pin=None,
                 relay_active_high=True, relay_settle_s=0.1):
        self._trigger = DigitalOutputDevice(
            pin, active_high=active_high, initial_value=False)
        self._relay = None
        if relay_pin is not None:
            self._relay = DigitalOutputDevice(
                relay_pin, active_high=relay_active_high, initial_value=False)
        self._relay_settle_s = relay_settle_s
        self.is_on = False

    def on(self):
        if self.is_on:
            return
        if self._relay:
            self._relay.on()                  # power first...
            time.sleep(self._relay_settle_s)  # ...let the supply come up
        self._trigger.on()
        self.is_on = True

    def off(self):
        # Always drive both low, even if we think it is already off
        self._trigger.off()
        if self._relay:
            self._relay.off()
        self.is_on = False

    def close(self):
        self.off()
        self._trigger.close()
        if self._relay:
            self._relay.close()
