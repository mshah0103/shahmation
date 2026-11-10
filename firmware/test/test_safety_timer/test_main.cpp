#include <unity.h>
#include "SafetyTimer.h"

void setUp() {}
void tearDown() {}

void test_expires_after_timeout() {
  SafetyTimer timer;
  timer.reset(500);
  TEST_ASSERT_FALSE(timer.expired(500 + TIMEOUT_MS - 1));
  TEST_ASSERT_TRUE(timer.expired(500 + TIMEOUT_MS));
}

void test_reset_starts_over() {
  SafetyTimer timer;
  timer.reset(0);
  timer.reset(1500);
  TEST_ASSERT_FALSE(timer.expired(2500));
  TEST_ASSERT_TRUE(timer.expired(1500 + TIMEOUT_MS));
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_expires_after_timeout);
  RUN_TEST(test_reset_starts_over);
  return UNITY_END();
}
