#include <Arduino.h>

// Nano-only bench test: laser PWM -> Nano D6, laser GND -> Nano GND.
// No Pi involved -- toggled directly over USB serial.
const int LASER_PIN = 6;

void setup() {
  pinMode(LASER_PIN, OUTPUT);
  analogWrite(LASER_PIN, 0); // laser OFF at boot

  Serial.begin(9600);
  Serial.println("--- Nano -> Laser toggle test ---");
  Serial.println("Send 'o' to turn laser ON, 'f' to turn laser OFF.");
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();

    switch (cmd) {
      case 'o': case 'O':
        analogWrite(LASER_PIN, 255);
        Serial.println("Laser ON");
        break;
      case 'f': case 'F':
        analogWrite(LASER_PIN, 0);
        Serial.println("Laser OFF");
        break;
    }
  }
}
