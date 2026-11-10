#include "SafetyTimer.h"

SafetyTimer::SafetyTimer() {
  lastMessage = 0;
}

void SafetyTimer::reset(unsigned long now) {
  lastMessage = now;
}

bool SafetyTimer::expired(unsigned long now) {
  return now - lastMessage >= TIMEOUT_MS;
}
