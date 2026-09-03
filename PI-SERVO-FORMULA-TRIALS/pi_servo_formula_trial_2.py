from gpiozero import AngularServo
from time import sleep

# gpiozero.AngularServo variant of the formula trial -- unlike
# pi_servo_formula_trial.py (raw RPi.GPIO + manual duty-cycle formula),
# this hands the pulse-width range straight to gpiozero and lets it
# compute the PWM signal internally; you just set `.angle` directly.
# Initialize the servo on GPIO pin 15
# min_pulse_width and max_pulse_width may need to be adjusted for your servo
servo = AngularServo(15, min_angle=0, max_angle=180, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000)


# Function to set the servo angle
def set_angle(angle):
    servo.angle = angle
    sleep(1)  # give the servo time to physically reach the new angle before accepting the next command


# Main program loop
try:
    while True:
        angle = int(input("Enter angle (0 to 180): "))  # User input for angle
        set_angle(angle)  # Set servo to entered angle
except KeyboardInterrupt:
    print("Program stopped by user")
