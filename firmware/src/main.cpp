#include <Arduino.h>
#include <Board.h>

Board board;

void setup() {
  Serial.begin(115200);
  board.allOff();   // everything starts off
}

void loop() {
  // read whatever came in and answer once a full line is there
  while (Serial.available()) {
    const char* r = board.feed(Serial.read());
    if (r) {
      Serial.println(r);
    }
  }
}
