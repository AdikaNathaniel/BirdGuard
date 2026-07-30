#include <Arduino.h>

// Laser module wiring: PWM pin -> Nano D5, GND -> Nano GND
const int LASER_PIN = 5;

// Relay module wiring: IN -> Nano D6, VCC -> Nano 5V, GND -> Nano GND
// Relay COM/NO sit in the laser's power line from the constant voltage source.
const int RELAY_PIN = 6;

void setup() {
  pinMode(LASER_PIN, OUTPUT);
  pinMode(RELAY_PIN, OUTPUT);
  analogWrite(LASER_PIN, 0);   // Laser OFF
  digitalWrite(RELAY_PIN, LOW); // Relay de-energized

  Serial.begin(9600);
  Serial.println("--- Laser Test ---");
  Serial.println("Send 'o' to turn laser ON, 'f' to turn laser OFF.");
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();

    switch (cmd) {
      case 'o': case 'O':
        analogWrite(LASER_PIN, 255);
        digitalWrite(RELAY_PIN, HIGH);
        Serial.println("Laser ON");
        break;
      case 'f': case 'F':
        analogWrite(LASER_PIN, 0);
        digitalWrite(RELAY_PIN, LOW);
        Serial.println("Laser OFF");
        break;
    }
  }
}
