#include <Arduino.h>
#include <Servo.h>

Servo panServo;
Servo tiltServo;

// --- PINS ---
const int LASER_PIN = 5;

// --- CALIBRATION ---
int panStop = 90;
int tiltStop = 90;
int speedOffset = 15;
int nudgeTime = 55;
// -------------------

void stopAll();
void nudge(Servo &s, int speed);

void setup() {
  panServo.attach(9);
  tiltServo.attach(10);

  pinMode(LASER_PIN, OUTPUT);
  digitalWrite(LASER_PIN, HIGH); // Laser OFF (active LOW module)

  panServo.write(panStop);
  tiltServo.write(tiltStop);

  Serial.begin(9600);
  Serial.println("--- Pan-Tilt-Laser System ---");
  Serial.println("CONTINUOUS: W/S (Tilt), A/D (Pan)");
  Serial.println("NUDGE:      I/K (Tilt), J/L (Pan)");
  Serial.println("LASER:      O (On), F (Off)");
  Serial.println("STOP ALL:   Spacebar or X");
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();

    switch (cmd) {
      case 'w': tiltServo.write(tiltStop + speedOffset); break;
      case 's': tiltServo.write(tiltStop - speedOffset); break;
      case 'a': panServo.write(panStop + speedOffset);   break;
      case 'd': panServo.write(panStop - speedOffset);   break;

      case 'i': nudge(tiltServo, tiltStop + speedOffset); break;
      case 'k': nudge(tiltServo, tiltStop - speedOffset); break;
      case 'j': nudge(panServo,  panStop + speedOffset);  break;
      case 'l': nudge(panServo,  panStop - speedOffset);  break;

      case 'o': case 'O':
        digitalWrite(LASER_PIN, LOW); // Active LOW = ON
        Serial.println("Laser ON");
        break;
      case 'f': case 'F':
        digitalWrite(LASER_PIN, HIGH); // Active LOW = OFF
        Serial.println("Laser OFF");
        break;

      case 'x': case ' ':
        stopAll();
        break;
    }
  }
}

void nudge(Servo &s, int speed) {
  s.write(speed);
  delay(nudgeTime);
  stopAll();
}

void stopAll() {
  panServo.write(panStop);
  tiltServo.write(tiltStop);
  Serial.println("Motors Stopped.");
}
