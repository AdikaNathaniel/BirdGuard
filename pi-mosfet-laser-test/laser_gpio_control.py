from gpiozero import DigitalOutputDevice

# Drives an IRF520N MOSFET's gate as a simple on/off switch (not PWM) --
# the MOSFET does the actual switching of the laser's higher-current
# supply, since a Pi GPIO pin alone can't safely source that much current.
LASER_GATE_PIN = 12  # BCM numbering — Pi GPIO12 -> IRF520N "S" pin

laser = DigitalOutputDevice(LASER_GATE_PIN)
print(f"GPIO{LASER_GATE_PIN} ready (driving IRF520N gate).")
print("Type 'o' + Enter to turn laser ON, 'f' + Enter to turn it OFF, 'q' + Enter to quit.\n")

try:
    while True:
        cmd = input("> ").strip().lower()
        if cmd == 'q':
            break
        elif cmd == 'o':
            laser.on()
            print("Laser ON")
        elif cmd == 'f':
            laser.off()
            print("Laser OFF")
        else:
            print("Type 'o', 'f', or 'q'.")
finally:
    laser.off()
    laser.close()
    print("GPIO released.")
