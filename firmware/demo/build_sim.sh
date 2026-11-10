#!/bin/bash
g++ -std=c++17 -D FULL_PIANO -I lib/Board -I lib/KeyChannel -I lib/SafetyTimer \
  demo/board_demo.cpp lib/Board/Board.cpp lib/KeyChannel/KeyChannel.cpp lib/SafetyTimer/SafetyTimer.cpp \
  -o demo/board_sim && echo "Built demo/board_sim"
