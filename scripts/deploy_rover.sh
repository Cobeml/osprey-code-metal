#!/usr/bin/env bash
# Deploy and run the rover client on the Hiwonder TurboPi. Run on the Mac, from the repo.
#
#   scripts/deploy_rover.sh                 copy the client + classifier, check Python deps
#   scripts/deploy_rover.sh --install       ... and create a venv and pip-install missing deps
#   scripts/deploy_rover.sh probe           list the Hiwonder SDK's servo/chassis calls (read-only)
#   scripts/deploy_rover.sh selftest [ARGS] guarded chassis/pan moves (interactive, needs a TTY)
#   scripts/deploy_rover.sh start URL [ARGS] run the client in the background, e.g.
#        scripts/deploy_rover.sh start ws://169.254.50.2:8000
#        (pan defaults: servo 1, sign -1, HiwonderSDK.Board:setPWMServoPulse; --pan-call none = body only)
#   scripts/deploy_rover.sh stop            stop the client (SIGTERM; the client stops the wheels)
#   scripts/deploy_rover.sh status | log
#
# SDK elsewhere than /home/pi/TurboPi: TURBOPI_SDK=<folder on the rover> scripts/deploy_rover.sh ...
# Host: ROVER_HOST (default pi@169.254.50.3, the TurboPi on the wired switch). Copy your key first:
#   ssh-copy-id pi@169.254.50.3
# The rover gets ~/osprey-rover/{scout_client.py, ballcolor.py}. Nothing is installed system-wide:
# --install only creates ~/osprey-rover/.venv (with system site packages, so the Hiwonder SDK and
# a system OpenCV stay visible) and pip-installs into it, which needs internet on the rover.
set -euo pipefail
cd "$(dirname "$0")/.."

HOST="${ROVER_HOST:-pi@169.254.50.3}"
DIR="osprey-rover"
SSH=(ssh -o ConnectTimeout=5 "$HOST")

copy() {
  "${SSH[@]}" "mkdir -p ~/$DIR"
  scp -q turbopi/scout_client.py src/osprey/perception/ballcolor.py "$HOST:$DIR/"
  # Pi 5 / ROS 2 image: HiwonderSDK shim over ~/board_demo/ros_robot_controller_sdk.py
  "${SSH[@]}" "mkdir -p ~/$DIR/HiwonderSDK"
  scp -q turbopi/HiwonderSDK/*.py "$HOST:$DIR/HiwonderSDK/"
  echo "copied scout_client.py + ballcolor.py to $HOST:~/$DIR"
}

# Remote helper: pick the venv python when present, else the system python3. TURBOPI_SDK set on
# the Mac is passed through (folder that contains HiwonderSDK/ on the rover).
REMOTE_PY='cd ~/'"$DIR"'; if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=python3; fi'
if [ -n "${TURBOPI_SDK:-}" ]; then REMOTE_PY="export TURBOPI_SDK='$TURBOPI_SDK'; $REMOTE_PY"; fi

check() {
  "${SSH[@]}" "$REMOTE_PY"'
    echo "python: $($PY --version 2>&1) ($PY)"
    $PY -c "import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)" || echo "  !! Python 3.7+ required"
    missing=""
    for m in cv2 numpy websockets; do
      if $PY -c "import $m" 2>/dev/null; then echo "  ok   $m"; else echo "  MISSING $m"; missing="$missing $m"; fi
    done
    if $PY -c "import sys; sys.path[:0]=[\"/home/pi/TurboPi\"]; import HiwonderSDK" 2>/dev/null; then
      echo "  ok   HiwonderSDK"
    else
      echo "  MISSING HiwonderSDK on the default path (set TURBOPI_SDK=<folder>; see: probe)"
    fi
    [ -z "$missing" ] || echo "missing:$missing  -> run with --install, or ask before: sudo apt install python3-opencv python3-numpy python3-websockets"'
}

install() {
  "${SSH[@]}" 'cd ~/'"$DIR"'
    if [ ! -x .venv/bin/python ]; then
      python3 -m venv --system-site-packages .venv || { echo "venv failed (python3-venv missing?)"; exit 1; }
    fi
    PY=.venv/bin/python
    need=""
    $PY -c "import websockets" 2>/dev/null || need="$need websockets"
    $PY -c "import numpy" 2>/dev/null || need="$need numpy"
    $PY -c "import cv2" 2>/dev/null || need="$need opencv-python-headless"
    if [ -n "$need" ]; then
      echo "pip install$need (needs internet on the rover)"
      $PY -m pip install -q $need
    fi'
}

case "${1:-deploy}" in
  deploy|--install)
    copy
    [ "${1:-}" = "--install" ] && install
    check
    cat <<EOF

next:
  scripts/deploy_rover.sh probe
  scripts/deploy_rover.sh selftest            # pan: servo 1 by default (--pan-call none to skip)
  scripts/deploy_rover.sh start ws://169.254.50.2:8000
EOF
    ;;
  probe)
    "${SSH[@]}" "$REMOTE_PY; \$PY scout_client.py --probe" ;;
  selftest)
    shift
    ssh -t -o ConnectTimeout=5 "$HOST" "$REMOTE_PY; \$PY scout_client.py --selftest --hw hiwonder $*" ;;
  start)
    shift
    URL="${1:?usage: deploy_rover.sh start URL [ARGS]}"; shift
    "${SSH[@]}" "$REMOTE_PY"'
      if [ -f rover.pid ] && kill -0 "$(cat rover.pid)" 2>/dev/null; then
        echo "already running (pid $(cat rover.pid))"; exit 0
      fi
      nohup $PY -u scout_client.py '"$URL"' --hw hiwonder '"$*"' < /dev/null >> rover.log 2>&1 &
      echo $! > rover.pid
      sleep 2
      if kill -0 "$(cat rover.pid)" 2>/dev/null; then echo "started (pid $(cat rover.pid))"; tail -5 rover.log
      else echo "exited:"; tail -20 rover.log; exit 1; fi' ;;
  stop)
    "${SSH[@]}" 'cd ~/'"$DIR"'
      if [ -f rover.pid ] && kill -0 "$(cat rover.pid)" 2>/dev/null; then
        kill "$(cat rover.pid)"
        for _ in 1 2 3 4 5 6 7 8 9 10; do kill -0 "$(cat rover.pid)" 2>/dev/null || break; sleep 0.3; done
        kill -0 "$(cat rover.pid)" 2>/dev/null && { echo "still running; kill -9"; kill -9 "$(cat rover.pid)"; }
        rm -f rover.pid; echo stopped
      else echo "not running"; fi' ;;
  status)
    "${SSH[@]}" 'cd ~/'"$DIR"'; if [ -f rover.pid ] && kill -0 "$(cat rover.pid)" 2>/dev/null; then echo "running (pid $(cat rover.pid))"; else echo "not running"; fi' ;;
  log)
    "${SSH[@]}" "tail -n 50 -f ~/$DIR/rover.log" ;;
  *)
    sed -n '2,20p' "$0"; exit 1 ;;
esac
