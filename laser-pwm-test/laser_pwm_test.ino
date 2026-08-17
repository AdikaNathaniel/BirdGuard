#include <Servo.h>

Servo panServo;
Servo tiltServo;

// --- PINS ---
const int LASER_PIN = 5; // PWM-capable pin, wired directly to laser's PWM input (laser GND -> Nano GND)

// --- CALIBRATION ---
int panStop = 90;
int tiltStop = 90;
int speedOffset = 15;
int nudgeTime = 55;
// -------------------

int laserDuty = 0; // 0-255, current PWM duty cycle

void setup() {
  panServo.attach(9);
  tiltServo.attach(10);

  pinMode(LASER_PIN, OUTPUT);
  analogWrite(LASER_PIN, 0); // Start with laser OFF

  panServo.write(panStop);
  tiltServo.write(tiltStop);

  Serial.begin(9600);
  Serial.println("--- Laser PWM Test ---");
  Serial.println("O = full ON (255)   F = full OFF (0)");
  Serial.println("0-9 = set duty ~0%-100% in 10% steps");
  Serial.println("CONTINUOUS: W/S (Tilt), A/D (Pan)   STOP: Spacebar or X");
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

      // --- LASER: FULL ON/OFF ---
      case 'o': case 'O':
        setLaser(255);
        break;
      case 'f': case 'F':
        setLaser(0);
        break;

      // --- LASER: DUTY STEPS 0-9 ---
      case '0': case '1': case '2': case '3': case '4':
      case '5': case '6': case '7': case '8': case '9': {
        int step = cmd - '0';           // 0-9
        int duty = map(step, 0, 9, 0, 255);
        setLaser(duty);
        break;
      }

      // --- STOP (X or Space) ---
      case 'x': case ' ':
        stopAll();
        break;
    }
  }
}

void setLaser(int duty) {
  laserDuty = constrain(duty, 0, 255);
  analogWrite(LASER_PIN, laserDuty);
  Serial.print("Laser duty: ");
  Serial.println(laserDuty);
}

void stopAll() {
  panServo.write(panStop);
  tiltServo.write(tiltStop);
  setLaser(0);
  Serial.println("Stopped. Motors + laser off.");
}
