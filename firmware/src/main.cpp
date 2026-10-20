#include <Arduino.h>

  unsigned long lastToggle = 0;
  bool ledOn = false;

  void setup() {
    pinMode(LED_BUILTIN, OUTPUT);
  }

  void loop() {
    if (millis() - lastToggle >= 500) {
      lastToggle = millis();
      ledOn = !ledOn;
      digitalWrite(LED_BUILTIN, ledOn);
    }
  }