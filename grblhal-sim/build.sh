#!/usr/bin/env bash
# Build the grblHAL Simulator as a copy of a real machine.
#
#   ./build.sh machines/stefan-altfinity.flags            Linux build
#   ./build.sh machines/stefan-altfinity.flags windows    Windows .exe (needs x86_64-w64-mingw32-gcc)
#
# Fetches grblHAL/Simulator at the commit below, applies virtual-machine.patch
# (limit switches and a probe that work by themselves, see README), and builds it
# with the machine's firmware options and default settings from the .flags file.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
FLAGS_FILE="${1:?usage: build.sh machines/NAME.flags [windows]}"
TARGET="${2:-linux}"
SIM_COMMIT=69ca5198e1697c026049ee74c7d6a124f6d34846
NAME="$(basename "$FLAGS_FILE" .flags)"
WORK="${WORK:-$HERE/.build}"

mkdir -p "$WORK"
if [ ! -d "$WORK/Simulator/.git" ]; then
  git clone -q --recurse-submodules https://github.com/grblHAL/Simulator "$WORK/Simulator"
fi
cd "$WORK/Simulator"
git checkout -q -- . && git checkout -q "$SIM_COMMIT" && git submodule update -q --init --recursive
git apply "$HERE/virtual-machine.patch"

FLAGS="$(grep -v '^#' "$HERE/$FLAGS_FILE" 2>/dev/null || grep -v '^#' "$FLAGS_FILE") "
FLAGS="$(echo "$FLAGS" | tr '\n' ' ') -DVIRTUAL_MACHINE=1"
BUILD="build-$NAME-$TARGET"
rm -rf "$BUILD" && mkdir "$BUILD" && cd "$BUILD"
if [ "$TARGET" = windows ]; then
  cmake .. -DCMAKE_TOOLCHAIN_FILE=../mingw.cmake -DCMAKE_C_FLAGS="$FLAGS" > cmake.log
  make -j"$(nproc)" grblHAL_sim > make.log
  mkdir -p "$HERE/bin" && cp grblHAL_sim.exe "$HERE/bin/grblHAL_sim-$NAME.exe"
  echo "built $HERE/bin/grblHAL_sim-$NAME.exe"
else
  cmake .. -DCMAKE_C_FLAGS="$FLAGS" > cmake.log
  make -j"$(nproc)" grblHAL_sim > make.log
  echo "built $WORK/Simulator/$BUILD/grblHAL_sim"
fi
