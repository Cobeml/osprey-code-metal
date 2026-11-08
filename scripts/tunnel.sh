#!/usr/bin/env bash
# Start a Cloudflare quick tunnel to the ground processor and print the scout URL.
# Runs on the Pi. Usage: scripts/tunnel.sh [start|stop|url]
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p runtime
LOG=runtime/tunnel.log
url() { grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$LOG" 2>/dev/null | tail -1; }
case "${1:-start}" in
  start)
    if pgrep -f "cloudflared tunnel .*--url" >/dev/null; then echo "running: $(url)/scout"; exit 0; fi
    : > "$LOG"
    nohup cloudflared tunnel --no-autoupdate --url http://localhost:8000 >> "$LOG" 2>&1 &
    for _ in $(seq 60); do u=$(url); [ -n "$u" ] && { echo "$u/scout"; exit 0; }; sleep 0.5; done
    echo "no URL yet; see $LOG"; exit 1 ;;
  stop) pkill -f "cloudflared tunnel .*--url"; echo stopped ;;
  url) echo "$(url)/scout" ;;
esac
