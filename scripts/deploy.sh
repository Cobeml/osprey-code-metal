#!/usr/bin/env bash
# Sync this repo to the Pi and install it into the Pi venv.
# Usage: scripts/deploy.sh [--restart]
set -euo pipefail
cd "$(dirname "$0")/.."
HOST="${OSPREY_HOST:-mob-pi}"
rsync -az --delete \
  --exclude .venv --exclude .git --exclude hardware-checks --exclude runtime \
  --exclude __pycache__ --exclude '*.egg-info' --exclude .pytest_cache \
  --exclude native/aurora/aurora_probe --exclude native/aurora/aurora_bridge \
  ./ "$HOST:osprey/"
ssh "$HOST" 'set -e; cd ~/osprey
  [ -d .venv ] || python3 -m venv --system-site-packages .venv
  .venv/bin/pip install -q -e . 2>&1 | grep -v "^\[notice\]" || true'
echo "deployed to $HOST:~/osprey"
if [ "${1:-}" = "--restart" ]; then ssh "$HOST" '~/osprey/scripts/run_pi.sh restart'; fi
