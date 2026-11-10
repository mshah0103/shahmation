#ifndef KEY_CHANNEL_H
#define KEY_CHANNEL_H

const int STRIKE_MIN = 90;
const int STRIKE_MAX = 255;
const unsigned long STRIKE_MS = 40;
const int HOLD_POWER = 45;
const unsigned long MAX_ON_MS = 10000;

class KeyChannel {
 public:
  KeyChannel();
  void strike(int velocity, unsigned long now);
  void update(unsigned long now);
  void release();
  int power();
  bool isOn();

 private:
  bool on;
  bool striking;
  int currentPower;
  unsigned long startTime;
};

#endif
