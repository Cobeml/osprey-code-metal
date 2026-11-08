#!/usr/bin/env bash
# Start a Cloudflare quick tunnel to the ground processor and print the scout URL.
# Runs on the Pi. Usage: scripts/tunnel.sh [start|stop|url|view]
# view: the view-only dashboard link (needs the ground server running)
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
  view) k=$(curl -s localhost:8000/api/view_link | sed -n 's/.*"key":"\([^"]*\)".*/\1/p')
    [ -n "$k" ] && echo "$(url)/v/$k" || { echo "ground server not answering"; exit 1; } ;;
esac
