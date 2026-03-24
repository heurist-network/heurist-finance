#!/bin/bash
# render.sh — Send render command to TUI
#
# Usage: bin/render.sh '{"action":"render","layout":"deep-dive","panels":{...}}'

set -euo pipefail

STATE_FILE="$HOME/.heurist/tui.json"

if [ ! -f "$STATE_FILE" ]; then
  echo "Error: TUI not running. Start with: bin/start.sh" >&2
  exit 1
fi

PORT=$(grep -o '"port":[[:space:]]*[0-9]*' "$STATE_FILE" | grep -o '[0-9]*')

if [ -z "$PORT" ]; then
  echo "Error: Could not read port from $STATE_FILE" >&2
  exit 1
fi

# Verify TUI is alive
if ! curl -sf "http://127.0.0.1:${PORT}/health" > /dev/null 2>&1; then
  echo "Error: TUI not responding on port $PORT. Try: bin/stop.sh && bin/start.sh" >&2
  exit 1
fi

# Send render command
if [ $# -eq 0 ]; then
  echo "Usage: bin/render.sh '{\"action\":\"render\",\"layout\":\"...\",\"panels\":{...}}'" >&2
  exit 1
fi

curl -sf "http://127.0.0.1:${PORT}/render" \
  -H 'Content-Type: application/json' \
  -d "$1"
