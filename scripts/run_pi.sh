#!/usr/bin/env bash
# Run the Osprey ground processor on the Pi (port 8000). Usage: run_pi.sh [start|stop|restart|status|log]
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p runtime
PIDFILE=runtime/osprey.pid
running() { [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; }
stop() {
  if running; then kill "$(cat "$PIDFILE")"; for _ in $(seq 12); do running || break; sleep 0.25; done; fi
  pkill -9 -f 'uvicorn osprey.app' 2>/dev/null; pkill -9 -f aurora_bridge 2>/dev/null; rm -f "$PIDFILE"
  sleep 0.3
}
start() {
  running && { echo "already running (pid $(cat $PIDFILE))"; return; }
  nohup .venv/bin/uvicorn osprey.app:app --host 0.0.0.0 --port 8000 --log-level warning --loop asyncio \
    >> runtime/osprey.log 2>&1 &
  echo $! > "$PIDFILE"
  for _ in $(seq 40); do curl -fs localhost:8000/health >/dev/null && { echo "up (pid $(cat $PIDFILE))"; return; }; sleep 0.25; done
  echo "did not answer /health; tail runtime/osprey.log"; tail -20 runtime/osprey.log; return 1
}
case "${1:-start}" in
  start) start ;;
  stop) stop; echo stopped ;;
  restart) stop; start ;;
  status) running && echo "running (pid $(cat $PIDFILE))" || echo "not running" ;;
  log) tail -n 50 -f runtime/osprey.log ;;
esac
