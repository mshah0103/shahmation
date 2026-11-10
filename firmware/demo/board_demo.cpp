// lets me type commands to the Board code on my laptop when the pico isn't plugged in
// it's the exact same Board.cpp the firmware uses, this just swaps Serial for the keyboard
#include <chrono>
#include <cstdio>
#include <cstring>
#include "Board.h"

unsigned long millisNow() {
  static auto start = std::chrono::steady_clock::now();
  auto gone = std::chrono::steady_clock::now() - start;
  return std::chrono::duration_cast<std::chrono::milliseconds>(gone).count();
}

void showOnScreen(Board& board, const char* command, const char* reply) {
  fprintf(stderr, "%-12s %-24s ", command, reply);
  for (int note = FIRST_NOTE; note <= LAST_NOTE; note++) {
    fputc(board.isOn(note) ? '#' : '.', stderr);
  }
  fprintf(stderr, "\n");
}

int main() {
  Board board;
  char command[MAX_LINE + 1];
  int length = 0;
  board.allOff();
  printf("Board ready, type a command (Ctrl+C to quit)\n");
  fflush(stdout);

  int c;
  while ((c = getchar()) != EOF) {
    board.update(millisNow());
    if (c != '\n' && c != '\r' && length < MAX_LINE) {
      command[length] = (char)c;
      length++;
    }
    const char* reply = board.feed((char)c);
    if (c == '\n') {
      command[length] = '\0';
      length = 0;
    }
    if (reply) {
      showOnScreen(board, command, reply);
      printf("%s\n", reply);
      fflush(stdout);
    }
  }
  return 0;
}
