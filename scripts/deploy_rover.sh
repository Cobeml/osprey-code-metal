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
#   scripts/deploy_rover.sh start           ... with the URLs saved in ~/osprey-rover/rover.env
#   scripts/deploy_rover.sh urls [ARGS]     save wired + current Cloudflare tunnel URL (asked from
#        the ground Pi) and ARGS (e.g. "--trace --fps 8") to rover.env; the client tries them in order
#   scripts/deploy_rover.sh autostart on|off  run the client at boot as osprey-rover.service (on also
#        disables Hiwonder's start_node container, which holds the motors and camera; off restores it)
#   scripts/deploy_rover.sh uwb [ARGS]      run uwb_probe.py on the rover (UWB board on its USB), e.g.
#        scripts/deploy_rover.sh uwb auto --send INITF
#   scripts/deploy_rover.sh stop            stop the client (SIGTERM; the client stops the wheels)
#   scripts/deploy_rover.sh status | log
#
# Wi-Fi: the venue isolates Wi-Fi clients, so over Wi-Fi the rover reaches the ground through the
# Cloudflare tunnel (outbound HTTPS). The quick-tunnel URL changes when cloudflared restarts: re-run
# "urls" (over the cable) after that: full steps in docs/rover-reconnect.md. Link drops: the rover keeps searching/approaching on its own
# camera and stops by itself after --autonomy-s (60 s) without the ground.
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
GROUND="${GROUND_HOST:-mob-pi}"
WIRED_URL="${WIRED_URL:-ws://169.254.50.2:8000}"
DIR="osprey-rover"
SSH=(ssh -o ConnectTimeout=5 "$HOST")

copy() {
  "${SSH[@]}" "mkdir -p ~/$DIR"
  scp -q turbopi/scout_client.py turbopi/uwb.py turbopi/uwb_probe.py src/osprey/perception/ballcolor.py "$HOST:$DIR/"
  # Pi 5 / ROS 2 image: HiwonderSDK shim over ~/board_demo/ros_robot_controller_sdk.py
  "${SSH[@]}" "mkdir -p ~/$DIR/HiwonderSDK"
  scp -q turbopi/HiwonderSDK/*.py "$HOST:$DIR/HiwonderSDK/"
  scp -q turbopi/osprey-rover.service "$HOST:$DIR/"
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
  uwb)
    shift
    "${SSH[@]}" "$REMOTE_PY; \$PY uwb_probe.py $*" ;;
  probe)
    "${SSH[@]}" "$REMOTE_PY; \$PY scout_client.py --probe" ;;
  selftest)
    shift
    ssh -t -o ConnectTimeout=5 "$HOST" "$REMOTE_PY; \$PY scout_client.py --selftest --hw hiwonder $*" ;;
  urls)
    shift
    # macOS sometimes routes 169.254/16 over Wi-Fi: retry pinned to the wired port
    T=$(ssh -o ConnectTimeout=4 "$GROUND" '~/osprey/scripts/tunnel.sh url' 2>/dev/null ||
        ssh -o ConnectTimeout=4 -o BindInterface=en10 "$GROUND" '~/osprey/scripts/tunnel.sh url' 2>/dev/null || true)
    T="${T%/scout}"
    case "$T" in https://*) URLS="$WIRED_URL,$T" ;; *) echo "no tunnel URL from $GROUND (scripts/tunnel.sh start on the Pi?): wired only"; URLS="$WIRED_URL" ;; esac
    printf 'ROVER_URLS=%s\nROVER_ARGS=%s\n' "$URLS" "$*" | "${SSH[@]}" "cat > ~/$DIR/rover.env"
    echo "rover.env on $HOST:"; "${SSH[@]}" "cat ~/$DIR/rover.env"
    "${SSH[@]}" 'systemctl is-active -q osprey-rover 2>/dev/null' && { echo "restarting osprey-rover.service"; "${SSH[@]}" 'sudo systemctl restart osprey-rover'; } || true ;;
  autostart)
    case "${2:-}" in
      on) "${SSH[@]}" 'set -e; cd ~/'"$DIR"'
            [ -f rover.env ] || { echo "no rover.env: run deploy_rover.sh urls first"; exit 1; }
            if [ -f rover.pid ] && kill -0 "$(cat rover.pid)" 2>/dev/null; then kill "$(cat rover.pid)"; rm -f rover.pid; fi
            sudo cp osprey-rover.service /etc/systemd/system/
            sudo systemctl daemon-reload
            sudo systemctl disable --now start_node; docker stop turbopi >/dev/null 2>&1 || true
            sudo systemctl enable --now osprey-rover
            sleep 3; systemctl --no-pager -n 0 status osprey-rover | head -3; tail -3 rover.log' ;;
      off) "${SSH[@]}" 'sudo systemctl disable --now osprey-rover 2>/dev/null || true
            sudo systemctl enable start_node; echo "osprey-rover off; start_node re-enabled (Hiwonder app back after reboot)"' ;;
      *) echo "usage: deploy_rover.sh autostart on|off"; exit 1 ;;
    esac ;;
  start)
    shift
    URL="${1:-}"; [ $# -gt 0 ] && shift
    if [ -z "$URL" ]; then
      URL=$("${SSH[@]}" "sed -n 's/^ROVER_URLS=//p' ~/$DIR/rover.env 2>/dev/null")
      [ -n "$URL" ] || { echo "usage: deploy_rover.sh start URL [ARGS]  (or run: deploy_rover.sh urls)"; exit 1; }
      echo "URLs from rover.env: $URL"
    fi
    if "${SSH[@]}" 'systemctl is-active -q osprey-rover 2>/dev/null'; then
      echo "osprey-rover.service is running (autostart on): use autostart off first"; exit 1
    fi
    "${SSH[@]}" "$REMOTE_PY"'
      docker stop turbopi >/dev/null 2>&1 || true   # Hiwonder container holds the motors + camera
      if [ -f rover.pid ] && kill -0 "$(cat rover.pid)" 2>/dev/null; then
        echo "already running (pid $(cat rover.pid))"; exit 0
      fi
      nohup $PY -u scout_client.py '"$URL"' --hw hiwonder '"$*"' < /dev/null >> rover.log 2>&1 &
      echo $! > rover.pid
      sleep 2
      if kill -0 "$(cat rover.pid)" 2>/dev/null; then echo "started (pid $(cat rover.pid))"; tail -5 rover.log
      else echo "exited:"; tail -20 rover.log; exit 1; fi' ;;
  stop)
    "${SSH[@]}" 'systemctl is-active -q osprey-rover 2>/dev/null && { sudo systemctl stop osprey-rover; echo "stopped osprey-rover.service (starts again at boot: autostart off to disable)"; }' || true
    "${SSH[@]}" 'cd ~/'"$DIR"'
      if [ -f rover.pid ] && kill -0 "$(cat rover.pid)" 2>/dev/null; then
        kill "$(cat rover.pid)"
        for _ in 1 2 3 4 5 6 7 8 9 10; do kill -0 "$(cat rover.pid)" 2>/dev/null || break; sleep 0.3; done
        kill -0 "$(cat rover.pid)" 2>/dev/null && { echo "still running; kill -9"; kill -9 "$(cat rover.pid)"; }
        rm -f rover.pid; echo stopped
      else echo "not running"; fi' ;;
  status)
    "${SSH[@]}" 'echo "service: $(systemctl is-active osprey-rover 2>/dev/null) / $(systemctl is-enabled osprey-rover 2>/dev/null || echo not-installed)"; echo "wifi: $(nmcli -t -f DEVICE,STATE,CONNECTION device | grep ^wlan0)"; [ -f ~/'"$DIR"'/rover.env ] && sed -n "s/^/env: /p" ~/'"$DIR"'/rover.env'
    "${SSH[@]}" 'cd ~/'"$DIR"'; if [ -f rover.pid ] && kill -0 "$(cat rover.pid)" 2>/dev/null; then echo "running (pid $(cat rover.pid))"; else echo "not running"; fi' ;;
  log)
    "${SSH[@]}" "tail -n 50 -f ~/$DIR/rover.log" ;;
  *)
    sed -n '2,32p' "$0"; exit 1 ;;
esac
