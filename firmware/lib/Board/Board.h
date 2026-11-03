#ifndef BOARD_H
#define BOARD_H

const int BOARD_NUMBER = 1;   // change per board when routing to all boards
const int FIRST_NOTE = 21;    // A0
const int LAST_NOTE = 108;    // C8. one board does the whole range for now
const int MAX_LINE = 32;

class Board {
 public:
  Board();                          // everything starts off
  const char* feed(char c);         // returns a reply when a line finishes otherwise nullptr
  const char* receive(const char* line);  // handles one full line (no newline)
  void allOff();
  bool isOn(int note);
  int onCount();

 private:
  bool on[LAST_NOTE - FIRST_NOTE + 1];
  char reply[48];
  char line[MAX_LINE + 1];
  int length;
  bool tooLong;
};

#endif