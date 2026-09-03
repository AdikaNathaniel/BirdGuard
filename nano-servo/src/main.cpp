#include <Arduino.h>
#include <Servo.h>

// Servo signal wire -> Nano D11 directly (no MOSFET in the signal path --
// a MOSFET only switches power, it can't carry the servo's PWM timing).
// Servo VCC -> 5V, Servo GND -> Nano GND.
Servo upDownServo;

const int SERVO_PIN = 11;
const int CENTER_POS = 90;

// Safe range -- adjust these to match how far your mechanism can
// physically move without straining/hitting its limits.
const int UP_POS = 120;
const int DOWN_POS = 60;

void setup() {
  upDownServo.attach(SERVO_PIN);
  upDownServo.write(CENTER_POS);

  Serial.begin(9600);
  Serial.println("--- Up/Down Servo Test ---");
  Serial.println("Send 'u' to move UP, 'd' to move DOWN, 'c' to CENTER.");
}

void loop() {
  // Manual bench-test controller -- reads one command char over USB
  // serial and moves the servo directly to a fixed position (no ramping/
  // stepping like the Pi-driven pan/tilt scripts use).
  if (Serial.available() > 0) {
    char cmd = Serial.read();

    switch (cmd) {
      case 'u': case 'U':
        upDownServo.write(UP_POS);
        Serial.println("Moving UP");
        break;
      case 'd': case 'D':
        upDownServo.write(DOWN_POS);
        Serial.println("Moving DOWN");
        break;
      case 'c': case 'C':
        upDownServo.write(CENTER_POS);
        Serial.println("Centered");
        break;
    }
  }
}
