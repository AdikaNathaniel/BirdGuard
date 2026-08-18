#include <Arduino.h>

// Laser module wiring: PWM pin -> Nano D5, GND -> Nano GND.
// Laser 12V/GND power comes straight from its own 12V adapter, always on --
// the PWM pin alone handles on/off and brightness (0 = off, 255 = full on).
// Signal path: Pi UART -> Nano RX (D0) -> this sketch -> Nano D5 -> laser PWM pin.
const int LASER_PIN = 6;

void setup() {
  pinMode(LASER_PIN, OUTPUT);
  analogWrite(LASER_PIN, 0);   // Laser OFF

  // LED_BUILTIN (pin 13) mirrors laser state — independent of D0/D1, so it
  // stays readable by eye even while the Pi's UART line contends with USB.
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

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
        digitalWrite(LED_BUILTIN, HIGH);
        Serial.println("Laser ON");
        break;
      case 'f': case 'F':
        analogWrite(LASER_PIN, 0);
        digitalWrite(LED_BUILTIN, LOW);
        Serial.println("Laser OFF");
        break;
    }
  }
}
