#!/usr/bin/env bash
# Build Aurora tools on the Pi. Requires the Deptrum SDK extracted under ~/vendor/deptrum (see docs/hardware.md).
set -euo pipefail
cd "$(dirname "$0")"
SDK="${DEPTRUM_SDK:-$HOME/vendor/deptrum/deptrum-ros-driver-aurora930-0.7.4/ext/deptrum-stream-aurora900-linux-aarch64-v1.1.4}"
for src in *.cc; do
  g++ -O2 -std=c++14 -pthread "$src" -I"$SDK/include" -L"$SDK/lib" -ldeptrum_stream_aurora900 \
      -Wl,-rpath,"$SDK/lib" $(pkg-config --cflags --libs opencv4) -o "${src%.cc}"
  echo "built ${src%.cc}"
done
