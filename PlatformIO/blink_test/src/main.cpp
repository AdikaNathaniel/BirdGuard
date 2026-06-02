#include <Arduino.h>

const int LED_PIN = 13;

void setup() {
    Serial.begin(9600);
    pinMode(LED_PIN, OUTPUT);
    Serial.println("Nano ready. Send 'B' to blink LED.");
}

void loop() {
    if (Serial.available()) {
        char cmd = Serial.read();
        if (cmd == 'B' || cmd == 'b') {
            Serial.println("Blinking...");
            for (int i = 0; i < 5; i++) {
                digitalWrite(LED_PIN, HIGH);
                delay(200);
                digitalWrite(LED_PIN, LOW);
                delay(200);
            }
            Serial.println("Done.");
        }
    }
}
