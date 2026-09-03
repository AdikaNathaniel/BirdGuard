#include <Arduino.h>
#include <Servo.h>

// Bridge: Pi GPIO13 (physical pin 33) -> Nano D9 (signal in), Nano D10 ->
// servo signal (out). Pi GND <-> Nano GND, Nano GND <-> servo GND (all common).
// Servo VCC -> 5V, Servo GND -> Nano GND, Servo signal -> Nano D10.
//
// D9 uses the internal pull-up, so it reads HIGH when idle/undriven instead
// of floating and picking up noise -- logic is inverted as a result: the Pi
// actively driving the line LOW is what counts as "signal" (servo UP).
// Pi commands: `pinctrl set 13 op dl` = UP, `pinctrl set 13 op dh` = DOWN.
#define INPUT_PIN 9
#define SERVO_PIN 10

Servo upDownServo;

const int UP_POS = 120;
const int DOWN_POS = 60;

void setup() {
    pinMode(INPUT_PIN, INPUT_PULLUP);
    upDownServo.attach(SERVO_PIN);
    upDownServo.write(DOWN_POS); // start DOWN

    Serial.begin(9600);
    Serial.println("--- Pi -> Nano -> Servo (Up/Down) bridge ---");
}

void loop() {
    // Level-triggered, not edge-triggered: the servo position directly
    // follows whatever the Pi's pin state currently is, re-checked every
    // 500ms -- there's no "toggle" behavior, just continuous mirroring.
    int signal = digitalRead(INPUT_PIN);

    if (signal == LOW) {
        upDownServo.write(UP_POS);
        Serial.println("LOW from Pi - Servo UP");
    } else {
        upDownServo.write(DOWN_POS);
        Serial.println("HIGH (idle) - Servo DOWN");
    }

    delay(500);
}
