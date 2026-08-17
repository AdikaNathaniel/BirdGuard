#include <Arduino.h>

#define INPUT_PIN 2

void setup() {
    pinMode(INPUT_PIN, INPUT);
    Serial.begin(9600);
}

void loop() {
    int signal = digitalRead(INPUT_PIN);

    if (signal == HIGH) {
        Serial.println("HIGH - Signal received from Raspberry Pi");
    } else {
        Serial.println("LOW - No signal");
    }

    delay(500);
}
