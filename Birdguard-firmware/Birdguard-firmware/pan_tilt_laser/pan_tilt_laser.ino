#include <Servo.h>

Servo panServo;
Servo tiltServo;

// --- PINS ---
const int LASER_PIN = 5; // Connect laser signal here

// --- CALIBRATION ---
int panStop = 90;    
int tiltStop = 90; 
int speedOffset = 15; 
int nudgeTime = 55;  
// -------------------

void setup() {
  panServo.attach(9);
  tiltServo.attach(10);
  
  // Set up Laser Pin
  pinMode(LASER_PIN, OUTPUT);
  digitalWrite(LASER_PIN, LOW); // Start with laser OFF
  
  // Initialize motors to stop
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
      // --- CONTINUOUS MOVEMENT (WASD) ---
      case 'w': tiltServo.write(tiltStop + speedOffset); break; 
      case 's': tiltServo.write(tiltStop - speedOffset); break; 
      case 'a': panServo.write(panStop + speedOffset);  break; 
      case 'd': panServo.write(panStop - speedOffset);  break; 

      // --- NUDGE MOVEMENT (IJKL) ---
      case 'i': nudge(tiltServo, tiltStop + speedOffset); break; 
      case 'k': nudge(tiltServo, tiltStop - speedOffset); break; 
      case 'j': nudge(panServo, panStop + speedOffset);   break; 
      case 'l': nudge(panServo, panStop - speedOffset);   break; 

      // --- LASER CONTROL (O/F) ---
      case 'o': case 'O':
        digitalWrite(LASER_PIN, HIGH);
        Serial.println("Laser ON");
        break;
      case 'f': case 'F':
        digitalWrite(LASER_PIN, LOW);
        Serial.println("Laser OFF");
        break;

      // --- STOP (X or Space) ---
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
