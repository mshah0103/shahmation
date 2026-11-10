#include "KeyChannel.h"

KeyChannel::KeyChannel() {
  release();
  startTime = 0;
}

void KeyChannel::strike(int velocity, unsigned long now) {
  currentPower = STRIKE_MIN + (velocity - 1) * (STRIKE_MAX - STRIKE_MIN) / 126;
  on = true;
  striking = true;
  startTime = now;
}

void KeyChannel::update(unsigned long now) {
  if (!on) {
    return;
  }
  if (now - startTime >= MAX_ON_MS) {
    release();
  } else if (striking && now - startTime >= STRIKE_MS) {
    striking = false;
    currentPower = HOLD_POWER;
  }
}

void KeyChannel::release() {
  on = false;
  striking = false;
  currentPower = 0;
}

int KeyChannel::power() {
  return currentPower;
}

bool KeyChannel::isOn() {
  return on;
}
