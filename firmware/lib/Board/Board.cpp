#include "Board.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// reads one number after a space (ex." 60"). gives back false if it isn't a clean number
static bool readNumber(const char* text, long* number, const char** after) {
  if (text[0] != ' ' || text[1] == ' ') {
    return false;
  }
  char* end;
  *number = strtol(text + 1, &end, 10);
  if (end == text + 1) {
    return false;   // no digits at all
  }
  if (*end != ' ' && *end != '\0') {
    return false;   // junk stuck on the end (ex.60abc)
  }
  *after = end;
  return true;
}

Board::Board() {
  length = 0;
  tooLong = false;
  reply[0] = '\0';
  now = 0;
  timer.reset(0);
  allOff();
}

void Board::update(unsigned long time) {
  now = time;
  for (int i = 0; i < NUM_KEYS; i++) {
    keys[i].update(now);
  }
  if (timer.expired(now) && onCount() > 0) {
    allOff();
  }
}

void Board::allOff() {
  for (int i = 0; i < NUM_KEYS; i++) {
    keys[i].release();
  }
}

bool Board::isOn(int note) {
  if (note < FIRST_NOTE || note > LAST_NOTE) {
    return false;
  }
  return keys[note - FIRST_NOTE].isOn();
}

int Board::onCount() {
  int count = 0;
  for (int i = 0; i < NUM_KEYS; i++) {
    if (keys[i].isOn()) {
      count++;
    }
  }
  return count;
}

int Board::power(int channel) {
  if (channel < 0 || channel >= NUM_KEYS) {
    return 0;
  }
  return keys[channel].power();
}

const char* Board::feed(char c) {
  if (c == '\r') {
    return nullptr;   // ignore so PING\r\n works too
  }
  if (c != '\n') {
    if (length < MAX_LINE) {
      line[length] = c;
      length++;
    } else {
      tooLong = true;   // no room left, keep going until the newline
    }
    return nullptr;
  }

  // newline so the line is finished
  line[length] = '\0';
  bool wasTooLong = tooLong;
  int wasLength = length;
  length = 0;
  tooLong = false;

  if (wasTooLong) {
    snprintf(reply, sizeof(reply), "ERR line too long");
    return reply;
  }
  if (wasLength == 0) {
    return nullptr;   // empty line
  }
  return receive(line);
}

const char* Board::receive(const char* text) {
  // command word is everything before the first space
  const char* rest = strchr(text, ' ');
  int wordLength;
  if (rest == nullptr) {
    wordLength = strlen(text);
    rest = text + wordLength;
  } else {
    wordLength = rest - text;
  }

  long note = 0;
  long velocity = 0;
  const char* after;

  if (wordLength == 5 && strncmp(text, "HELLO", 5) == 0) {
    if (*rest != '\0') {
      snprintf(reply, sizeof(reply), "ERR bad format");
    } else {
      snprintf(reply, sizeof(reply), "ID SHAHMATION KEY %d %d %d", BOARD_NUMBER, FIRST_NOTE, LAST_NOTE);
    }
  } else if (wordLength == 4 && strncmp(text, "PING", 4) == 0) {
    if (*rest != '\0') {
      snprintf(reply, sizeof(reply), "ERR bad format");
    } else {
      snprintf(reply, sizeof(reply), "PONG");
    }
  } else if (wordLength == 6 && strncmp(text, "ALLOFF", 6) == 0) {
    if (*rest != '\0') {
      snprintf(reply, sizeof(reply), "ERR bad format");
    } else {
      allOff();
      snprintf(reply, sizeof(reply), "OK");
    }
  } else if (wordLength == 2 && strncmp(text, "ON", 2) == 0) {
    if (!readNumber(rest, &note, &after) || !readNumber(after, &velocity, &after) || *after != '\0') {
      snprintf(reply, sizeof(reply), "ERR bad format");
    } else if (note < FIRST_NOTE || note > LAST_NOTE) {
      snprintf(reply, sizeof(reply), "ERR note out of range");
    } else if (velocity < 1 || velocity > 127) {
      snprintf(reply, sizeof(reply), "ERR bad velocity");
    } else {
      keys[note - FIRST_NOTE].strike(velocity, now);
      snprintf(reply, sizeof(reply), "OK");
    }
  } else if (wordLength == 3 && strncmp(text, "OFF", 3) == 0) {
    if (!readNumber(rest, &note, &after) || *after != '\0') {
      snprintf(reply, sizeof(reply), "ERR bad format");
    } else if (note < FIRST_NOTE || note > LAST_NOTE) {
      snprintf(reply, sizeof(reply), "ERR note out of range");
    } else {
      keys[note - FIRST_NOTE].release();
      snprintf(reply, sizeof(reply), "OK");
    }
  } else {
    snprintf(reply, sizeof(reply), "ERR unknown command");
  }
  if (strncmp(reply, "ERR", 3) != 0) {
    timer.reset(now);
  }
  return reply;
}
