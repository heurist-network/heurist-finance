#!/bin/bash
# bin/start.sh — Launch the Heurist Finance TUI canvas + bridge server.
#
# Usage: bin/start.sh
#
# Behaviour:
#   - If TUI is already running (live PID + healthy HTTP): print port and exit.
#   - If state file exists but PID is dead (stale): clean up and restart.
#   - Otherwise: start node terminal/app.js in background, wait for state file.
#   - If running inside tmux: offer to split the pane.

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STATE_FILE="${HOME}/.heurist/tui.json"
POLL_INTERVAL=0.1   # seconds
STARTUP_TIMEOUT=10  # seconds

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

read_state() {
  if [[ -f "$STATE_FILE" ]]; then
    cat "$STATE_FILE"
  fi
}

get_field() {
  # $1 = field name, read from stdin
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$1',''))"
}

pid_alive() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

health_check() {
  local port="$1"
  curl -sf --max-time 2 "http://127.0.0.1:${port}/health" > /dev/null 2>&1
}

cleanup_stale() {
  echo "Removing stale state file..."
  rm -f "$STATE_FILE"
}

# ---------------------------------------------------------------------------
# Check if already running
# ---------------------------------------------------------------------------

if [[ -f "$STATE_FILE" ]]; then
  STATE="$(read_state)"
  PID="$(echo "$STATE" | get_field pid)"
  PORT="$(echo "$STATE" | get_field port)"

  if pid_alive "$PID" && health_check "$PORT"; then
    echo "TUI running on port ${PORT}"
    exit 0
  else
    cleanup_stale
  fi
fi

# ---------------------------------------------------------------------------
# Start the TUI
# ---------------------------------------------------------------------------

APP="${SKILL_DIR}/terminal/dist/app.mjs"
if [[ ! -f "$APP" ]]; then
  echo "Error: bundle not found at ${APP}. Run: cd ${SKILL_DIR} && npm run build" >&2
  exit 1
fi

echo "Starting TUI..."
node "$APP" &
TUI_PID=$!

# ---------------------------------------------------------------------------
# Wait for state file to appear (poll 100 ms, timeout 10 s)
# ---------------------------------------------------------------------------

elapsed=0
while [[ ! -f "$STATE_FILE" ]]; do
  sleep "$POLL_INTERVAL"
  elapsed=$(python3 -c "print(${elapsed} + ${POLL_INTERVAL})")

  # Check if background process died early
  if ! kill -0 "$TUI_PID" 2>/dev/null; then
    echo "Error: TUI process exited unexpectedly (PID ${TUI_PID})" >&2
    exit 1
  fi

  if (( $(echo "$elapsed >= $STARTUP_TIMEOUT" | bc -l) )); then
    echo "Error: Timed out waiting for TUI to start (${STARTUP_TIMEOUT}s)" >&2
    kill "$TUI_PID" 2>/dev/null || true
    exit 1
  fi
done

# ---------------------------------------------------------------------------
# Read port from state file
# ---------------------------------------------------------------------------

STATE="$(read_state)"
PORT="$(echo "$STATE" | get_field port)"

# ---------------------------------------------------------------------------
# tmux pane split offer
# ---------------------------------------------------------------------------

if [[ -n "${TMUX:-}" ]]; then
  echo ""
  echo "You are inside tmux. Split pane? [y/N]"
  read -r -t 5 ANSWER || ANSWER="n"
  if [[ "${ANSWER,,}" == "y" ]]; then
    # Split: top = TUI output (attach to its fd), bottom = current shell
    # We can't easily reattach to the background node process stdout, so we
    # open a new pane showing the state file for informational purposes.
    tmux split-window -v "tail -f /dev/null"
    tmux select-pane -t top
  fi
fi

echo "TUI running on port ${PORT}"
