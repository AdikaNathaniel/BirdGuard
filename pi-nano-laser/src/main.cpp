#include <Arduino.h>

// Bridge: Pi GPIO12 -> Nano D2 (signal in), Nano D6 -> laser PWM pin (signal out).
// D6 used instead of D5 -- D5 was damaged from earlier direct-drive over-current testing.
// Pi GND <-> Nano GND, Nano GND <-> laser GND (all common).
// Pi just runs `pinctrl set 12 op dh` / `pinctrl set 12 op dl` to drive this.
#define INPUT_PIN 2
#define LASER_PIN 6

void setup() {
    pinMode(INPUT_PIN, INPUT);
    pinMode(LASER_PIN, OUTPUT);
    analogWrite(LASER_PIN, 0); // laser OFF at boot

    Serial.begin(9600);
    Serial.println("--- Pi -> Nano -> Laser bridge ---");
}

void loop() {
    // Polls the Pi's GPIO12 state every 500ms and mirrors it straight
    // onto the laser pin -- no debouncing/edge-detection needed here
    // since the Pi side already handles on/off timing logic.
    int signal = digitalRead(INPUT_PIN);

    if (signal == HIGH) {
        analogWrite(LASER_PIN, 255);
        Serial.println("HIGH from Pi - Laser ON");
    } else {
        analogWrite(LASER_PIN, 0);
        Serial.println("LOW from Pi - Laser OFF");
    }

    delay(500);
}
