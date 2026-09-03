#include <Arduino.h>

// Internal pull-up means the pin reads HIGH when idle/undriven -- so logic
// is inverted here: Pi actively driving LOW is what counts as "signal".
#define INPUT_PIN 2

void setup() {
    pinMode(INPUT_PIN, INPUT_PULLUP);
    Serial.begin(9600);
}

void loop() {
    // Diagnostic-only sketch -- just reports what it sees on the input
    // pin every 500ms via Serial, doesn't drive anything itself. Used to
    // confirm the Pi->Nano signal wire is actually toggling correctly
    // before trusting a more complex sketch built on top of it.
    int signal = digitalRead(INPUT_PIN);

    if (signal == LOW) {
        Serial.println("LOW - Signal received from Raspberry Pi");
    } else {
        Serial.println("HIGH - No signal (idle/pulled up)");
    }

    delay(500);
}
