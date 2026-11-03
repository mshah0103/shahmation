#include <unity.h>
#include <string.h>
#include <Board.h>

void setUp() {}
void tearDown() {}

// feeds every char and gives back the last reply that wasn't null
const char* send(Board& b, const char* text) {
  const char* last = nullptr;
  for (int i = 0; text[i] != '\0'; i++) {
    const char* r = b.feed(text[i]);
    if (r != nullptr) {
      last = r;
    }
  }
  return last;
}

void test_starts_off() {
  Board b;
  TEST_ASSERT_EQUAL_INT(0, b.onCount());
}

void test_hello_identity_plays_nothing() {
  Board b;
  TEST_ASSERT_EQUAL_STRING("ID SHAHMATION KEY 1 21 108", send(b, "HELLO\n"));
  TEST_ASSERT_EQUAL_INT(0, b.onCount());
}

void test_ping() {
  Board b;
  TEST_ASSERT_EQUAL_STRING("PONG", send(b, "PING\n"));
}

void test_on_off() {
  Board b;
  TEST_ASSERT_EQUAL_STRING("OK", send(b, "ON 60 100\n"));
  TEST_ASSERT_TRUE(b.isOn(60));
  TEST_ASSERT_EQUAL_STRING("OK", send(b, "OFF 60\n"));
  TEST_ASSERT_FALSE(b.isOn(60));
}

void test_alloff() {
  Board b;
  send(b, "ON 60 100\n");
  send(b, "ON 64 100\n");
  TEST_ASSERT_EQUAL_INT(2, b.onCount());
  TEST_ASSERT_EQUAL_STRING("OK", send(b, "ALLOFF\n"));
  TEST_ASSERT_EQUAL_INT(0, b.onCount());
}

// damaged commands do nothing and get an error back
void check_rejected(const char* text, const char* expected) {
  Board b;
  TEST_ASSERT_EQUAL_STRING(expected, send(b, text));
  TEST_ASSERT_EQUAL_INT(0, b.onCount());
}

void test_tc_r16_rejects_damaged() {
  check_rejected("ON 60\n", "ERR bad format");
  check_rejected("ON 60 abc\n", "ERR bad format");
  check_rejected("ON 60 64 9\n", "ERR bad format");
  check_rejected("ON60 64\n", "ERR unknown command");
  check_rejected("ON 20 64\n", "ERR note out of range");
  check_rejected("ON 109 64\n", "ERR note out of range");
  check_rejected("ON 60 0\n", "ERR bad velocity");
  check_rejected("ON 60 128\n", "ERR bad velocity");
  check_rejected("FOO\n", "ERR unknown command");
}

void test_crlf_and_junk() {
  Board b;
  TEST_ASSERT_EQUAL_STRING("PONG", send(b, "PING\r\n"));
  const char* r = send(b, "\x01\xff\x7f\n");
  TEST_ASSERT_NOT_NULL(r);
  TEST_ASSERT_EQUAL_INT(0, strncmp(r, "ERR", 3));
  TEST_ASSERT_EQUAL_STRING("PONG", send(b, "PING\n"));
}

void test_long_line_recovers() {
  Board b;
  int replies = 0;
  const char* last = nullptr;
  for (int i = 0; i < 1000; i++) {
    if (b.feed('A') != nullptr) {
      replies++;
    }
  }
  last = b.feed('\n');
  if (last != nullptr) {
    replies++;
  }
  TEST_ASSERT_EQUAL_INT(1, replies);
  TEST_ASSERT_EQUAL_STRING("ERR line too long", last);
  TEST_ASSERT_EQUAL_STRING("PONG", send(b, "PING\n"));
}

void test_empty_line_ignored() {
  Board b;
  TEST_ASSERT_NULL(b.feed('\n'));
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_starts_off);
  RUN_TEST(test_hello_identity_plays_nothing);
  RUN_TEST(test_ping);
  RUN_TEST(test_on_off);
  RUN_TEST(test_alloff);
  RUN_TEST(test_tc_r16_rejects_damaged);
  RUN_TEST(test_crlf_and_junk);
  RUN_TEST(test_long_line_recovers);
  RUN_TEST(test_empty_line_ignored);
  return UNITY_END();
}
