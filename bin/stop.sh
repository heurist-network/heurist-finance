#!/bin/bash
# bin/stop.sh — Stop the Heurist Finance TUI.
#
# Usage: bin/stop.sh
#
# Behaviour:
#   - Read ~/.heurist/tui.json for PID.
#   - If no state file: print "TUI not running" and exit.
#   - Send SIGTERM; poll for state file disappearance (100 ms, 5 s timeout).
#   - If still alive after timeout: SIGKILL.
#   - Remove state file if still present.
#   - Print "TUI stopped".

set -euo pipefail

STATE_FILE="${HOME}/.heurist/tui.json"
POLL_INTERVAL=0.1  # seconds
STOP_TIMEOUT=5     # seconds

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

get_field() {
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$1',''))"
}

pid_alive() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

# ---------------------------------------------------------------------------
# Read state file
# ---------------------------------------------------------------------------

if [[ ! -f "$STATE_FILE" ]]; then
  echo "TUI not running"
  exit 0
fi

STATE="$(cat "$STATE_FILE")"
PID="$(echo "$STATE" | get_field pid)"

if [[ -z "$PID" ]]; then
  echo "Error: State file present but PID field missing." >&2
  rm -f "$STATE_FILE"
  exit 1
fi

# If PID is already dead, just clean up.
if ! pid_alive "$PID"; then
  echo "TUI not running (stale state file cleaned up)"
  rm -f "$STATE_FILE"
  exit 0
fi

# ---------------------------------------------------------------------------
# SIGTERM
# ---------------------------------------------------------------------------

echo "Stopping TUI (PID ${PID})..."
kill -TERM "$PID" 2>/dev/null || true

# ---------------------------------------------------------------------------
# Poll for state file disappearance (100 ms, 5 s timeout)
# ---------------------------------------------------------------------------

elapsed=0
while [[ -f "$STATE_FILE" ]]; do
  sleep "$POLL_INTERVAL"
  elapsed=$(python3 -c "print(${elapsed} + ${POLL_INTERVAL})")

  if (( $(echo "$elapsed >= $STOP_TIMEOUT" | bc -l) )); then
    break
  fi
done

# ---------------------------------------------------------------------------
# Force-kill if still alive
# ---------------------------------------------------------------------------

if pid_alive "$PID"; then
  echo "Process did not exit after ${STOP_TIMEOUT}s — sending SIGKILL..."
  kill -KILL "$PID" 2>/dev/null || true
fi

# ---------------------------------------------------------------------------
# Clean up state file if still present
# ---------------------------------------------------------------------------

rm -f "$STATE_FILE"

echo "TUI stopped"
