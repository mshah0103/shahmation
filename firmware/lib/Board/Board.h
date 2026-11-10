#ifndef BOARD_H
#define BOARD_H

#include "KeyChannel.h"
#include "SafetyTimer.h"

const int BOARD_NUMBER = 1;   // change per board when routing to all boards
#ifdef FULL_PIANO
const int NUM_KEYS = 88;
#else
const int NUM_KEYS = 16;
#endif
const int FIRST_NOTE = 21;    // A0
const int LAST_NOTE = FIRST_NOTE + NUM_KEYS - 1;
const int MAX_LINE = 32;

class Board {
 public:
  Board();                          // everything starts off
  const char* feed(char c);         // returns a reply when a line finishes otherwise nullptr
  const char* receive(const char* line);  // handles one full line (no newline)
  void update(unsigned long now);
  void allOff();
  bool isOn(int note);
  int onCount();
  int power(int channel);

 private:
  KeyChannel keys[NUM_KEYS];
  SafetyTimer timer;
  unsigned long now;
  char reply[48];
  char line[MAX_LINE + 1];
  int length;
  bool tooLong;
};

#endif
