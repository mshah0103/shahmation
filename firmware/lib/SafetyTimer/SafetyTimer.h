#ifndef SAFETY_TIMER_H
#define SAFETY_TIMER_H

const unsigned long TIMEOUT_MS = 2000;

class SafetyTimer {
 public:
  SafetyTimer();
  void reset(unsigned long now);
  bool expired(unsigned long now);

 private:
  unsigned long lastMessage;
};

#endif
