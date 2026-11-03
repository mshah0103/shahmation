// live demo of board firmware on laptop
#include <cstdio>
#include "Board.h"

int main() {
  Board board;
  board.allOff();
  printf("Board ready, type a command (Ctrl+C to quit)\n");

  int c;
  while ((c = getchar()) != EOF) {
    const char* reply = board.feed((char)c);
    if (reply) {
      printf("%s\n", reply);
    }
  }
  return 0;
}
