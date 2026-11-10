#include <unity.h>
#include "KeyChannel.h"

void setUp() {}
void tearDown() {}

void test_starts_off() {
  KeyChannel key;
  TEST_ASSERT_FALSE(key.isOn());
  TEST_ASSERT_EQUAL(0, key.power());
}

void test_strike_power_follows_velocity() {
  KeyChannel key;
  key.strike(127, 0);
  TEST_ASSERT_TRUE(key.isOn());
  TEST_ASSERT_EQUAL(255, key.power());
  key.strike(1, 0);
  TEST_ASSERT_EQUAL(90, key.power());
}

void test_goes_to_hold_after_strike_time() {
  KeyChannel key;
  key.strike(100, 1000);
  key.update(1000 + STRIKE_MS - 1);
  TEST_ASSERT_TRUE(key.power() > HOLD_POWER);
  key.update(1000 + STRIKE_MS);
  TEST_ASSERT_EQUAL(HOLD_POWER, key.power());
  TEST_ASSERT_TRUE(key.isOn());
}

void test_release_turns_off() {
  KeyChannel key;
  key.strike(100, 0);
  key.release();
  TEST_ASSERT_FALSE(key.isOn());
  TEST_ASSERT_EQUAL(0, key.power());
  key.update(50);
  TEST_ASSERT_EQUAL(0, key.power());
}

void test_tc_r06_max_on_time() {
  KeyChannel key;
  key.strike(100, 0);
  key.update(MAX_ON_MS - 1);
  TEST_ASSERT_TRUE(key.isOn());
  key.update(MAX_ON_MS);
  TEST_ASSERT_FALSE(key.isOn());
  TEST_ASSERT_EQUAL(0, key.power());
}

void test_restrike_while_holding() {
  KeyChannel key;
  key.strike(100, 0);
  key.update(100);
  TEST_ASSERT_EQUAL(HOLD_POWER, key.power());
  key.strike(127, 200);
  TEST_ASSERT_EQUAL(255, key.power());
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_starts_off);
  RUN_TEST(test_strike_power_follows_velocity);
  RUN_TEST(test_goes_to_hold_after_strike_time);
  RUN_TEST(test_release_turns_off);
  RUN_TEST(test_tc_r06_max_on_time);
  RUN_TEST(test_restrike_while_holding);
  return UNITY_END();
}
