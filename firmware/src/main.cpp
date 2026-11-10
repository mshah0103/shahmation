#include <Arduino.h>
#include <Board.h>

const int KEY_PINS[NUM_KEYS] = {1, 3, 5, 7, 9, 11, 13, 15, 14, 12, 10, 8, 6, 4, 2, 0};

Board board;
int lastPower[NUM_KEYS];

void setup() {
  analogWriteFreq(20000);
  analogWriteRange(255);
  for (int i = 0; i < NUM_KEYS; i++) {
    pinMode(KEY_PINS[i], OUTPUT);
    analogWrite(KEY_PINS[i], 0);   // everything starts off (TC-R16)
    lastPower[i] = 0;
  }
  Serial.begin(115200);
  board.allOff();
}

void loop() {
  board.update(millis());

  // read whatever came in and answer once a full line is there
  while (Serial.available()) {
    const char* r = board.feed(Serial.read());
    if (r) {
      Serial.println(r);
    }
  }

  for (int i = 0; i < NUM_KEYS; i++) {
    int p = board.power(i);
    if (p != lastPower[i]) {
      analogWrite(KEY_PINS[i], p);
      lastPower[i] = p;
    }
  }
}
