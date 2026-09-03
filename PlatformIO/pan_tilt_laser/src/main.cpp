#include <Arduino.h>
#include <Servo.h>

// Pan-tilt only for now -- laser control stripped out to isolate and test
// servo movement first. Servo signal wires: pan -> D9, tilt -> D10.
// Servo VCC/GND wired separately (external 5V supply, common ground).
Servo panServo;
Servo tiltServo;

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

  panServo.write(panStop);
  tiltServo.write(tiltStop);

  Serial.begin(9600);
  Serial.println("--- Pan-Tilt System (laser disabled for now) ---");
  Serial.println("CONTINUOUS: W/S (Tilt), A/D (Pan)");
  Serial.println("NUDGE:      I/K (Tilt), J/L (Pan)");
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

      case 'x': case ' ':
        stopAll();
        break;
    }
  }
}

void nudge(Servo &s, int speed) {
  // Brief timed move then snap back to stop -- blocking `delay()` is fine
  // here since nothing else needs to run concurrently on this simple sketch.
  s.write(speed);
  delay(nudgeTime);
  stopAll();
}

void stopAll() {
  panServo.write(panStop);
  tiltServo.write(tiltStop);
  Serial.println("Motors Stopped.");
}
