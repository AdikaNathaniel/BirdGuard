#include <Arduino.h>

// Internal pull-up means the pin reads HIGH when idle/undriven -- so logic
// is inverted here: Pi actively driving LOW is what counts as "signal".
#define INPUT_PIN 2

void setup() {
    pinMode(INPUT_PIN, INPUT_PULLUP);
    Serial.begin(9600);
}

void loop() {
    int signal = digitalRead(INPUT_PIN);

    if (signal == LOW) {
        Serial.println("LOW - Signal received from Raspberry Pi");
    } else {
        Serial.println("HIGH - No signal (idle/pulled up)");
    }

    delay(500);
}
