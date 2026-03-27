#!/bin/bash
# bin/check-update.sh — Periodic version check with snooze and auto-upgrade.
#
# Compares local package.json version against latest git tag on the public repo.
# Uses live remote tag checks on every run, with escalating snooze and auto-upgrade.
#
# Outputs JSON (one line):
#   {"just_upgraded":true,"from":"0.9.1","to":"0.9.11"}
#   {"current":"0.9.1","latest":"0.9.11","update_available":true}
#   {"current":"0.9.11","latest":"0.9.11","update_available":false}
#   {"skipped":true,"reason":"..."}
#
# Exit codes:
#   0 — check completed (regardless of result)
#   1 — check failed (network, no remote, etc.)
#
# Flags:
#   --force    compatibility no-op; always fetches from remote
#   --snooze   write snooze file (called by SKILL.md after user picks snooze)
#   --auto     set auto_upgrade: true in config (called by SKILL.md)
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && cd .. && pwd)"
STATE_DIR="${HOME}/.heurist"
CONFIG_FILE="${STATE_DIR}/config.yaml"
SNOOZE_FILE="${STATE_DIR}/update-snoozed"
MARKER_FILE="${STATE_DIR}/just-upgraded-from"
PUBLIC_REPO="https://github.com/heurist-network/heurist-finance.git"

mkdir -p "$STATE_DIR"

# ── Sub-commands ──────────────────────────────────────────────────────────────

if [ "${1:-}" = "--snooze" ]; then
  # Write/escalate snooze. Usage: check-update.sh --snooze <version>
  VER="${2:-unknown}"
  if [ -f "$SNOOZE_FILE" ]; then
    OLD_LEVEL=$(awk '{print $2}' "$SNOOZE_FILE" 2>/dev/null || echo "0")
    case "$OLD_LEVEL" in *[!0-9]*) OLD_LEVEL=0 ;; esac
    NEW_LEVEL=$(( OLD_LEVEL + 1 ))
  else
    NEW_LEVEL=1
  fi
  echo "$VER $NEW_LEVEL $(date +%s)" > "$SNOOZE_FILE"
  case "$NEW_LEVEL" in
    1) echo '{"snoozed":true,"duration":"24h"}' ;;
    2) echo '{"snoozed":true,"duration":"48h"}' ;;
    *) echo '{"snoozed":true,"duration":"7d"}' ;;
  esac
  exit 0
fi

if [ "${1:-}" = "--auto" ]; then
  # Set auto_upgrade: true in config.yaml
  if [ -f "$CONFIG_FILE" ] && grep -q '^auto_upgrade:' "$CONFIG_FILE" 2>/dev/null; then
    sed -i 's/^auto_upgrade:.*/auto_upgrade: true/' "$CONFIG_FILE"
  else
    echo "auto_upgrade: true" >> "$CONFIG_FILE"
  fi
  echo '{"auto_upgrade":true}'
  exit 0
fi

if [ "${1:-}" = "--mark-upgraded" ]; then
  # Write just-upgraded marker. Usage: check-update.sh --mark-upgraded <old-version>
  echo "${2:-unknown}" > "$MARKER_FILE"
  rm -f "$SNOOZE_FILE"
  exit 0
fi

# ── Check if auto-update check is disabled ────────────────────────────────────
if [ -f "$CONFIG_FILE" ]; then
  AUTO_CHECK=$(grep -E '^auto_update_check:' "$CONFIG_FILE" 2>/dev/null | awk '{print $2}' || echo "true")
  if [ "$AUTO_CHECK" = "false" ]; then
    echo '{"skipped":true,"reason":"auto_update_check disabled in config"}'
    exit 0
  fi
fi

# ── Get local version ────────────────────────────────────────────────────────
LOCAL=$(node -e "console.log(require('${SKILL_DIR}/package.json').version)" 2>/dev/null || echo "unknown")
if [ "$LOCAL" = "unknown" ]; then
  echo '{"error":"Could not read local version from package.json"}'
  exit 1
fi

# ── Check "just upgraded" marker ──────────────────────────────────────────────
if [ -f "$MARKER_FILE" ]; then
  OLD=$(cat "$MARKER_FILE" 2>/dev/null | tr -d '[:space:]')
  rm -f "$MARKER_FILE" "$SNOOZE_FILE"
  if [ -n "$OLD" ]; then
    echo "{\"just_upgraded\":true,\"from\":\"${OLD}\",\"to\":\"${LOCAL}\"}"
    exit 0
  fi
fi

# ── Snooze helper ─────────────────────────────────────────────────────────────
# check_snooze <remote_version>
#   Returns 0 if snoozed (should stay quiet), 1 if not snoozed.
#   Snooze file format: <version> <level> <epoch>
#   Level durations: 1=24h, 2=48h, 3+=7d
#   New version resets snooze.
check_snooze() {
  local remote_ver="$1"
  [ -f "$SNOOZE_FILE" ] || return 1

  local snoozed_ver snoozed_level snoozed_epoch
  snoozed_ver="$(awk '{print $1}' "$SNOOZE_FILE" 2>/dev/null || true)"
  snoozed_level="$(awk '{print $2}' "$SNOOZE_FILE" 2>/dev/null || true)"
  snoozed_epoch="$(awk '{print $3}' "$SNOOZE_FILE" 2>/dev/null || true)"

  # Validate fields
  [ -z "$snoozed_ver" ] || [ -z "$snoozed_level" ] || [ -z "$snoozed_epoch" ] && return 1
  case "$snoozed_level" in *[!0-9]*) return 1 ;; esac
  case "$snoozed_epoch" in *[!0-9]*) return 1 ;; esac

  # New version resets snooze
  [ "$snoozed_ver" != "$remote_ver" ] && return 1

  # Compute duration
  local duration
  case "$snoozed_level" in
    1) duration=86400 ;;   # 24h
    2) duration=172800 ;;  # 48h
    *) duration=604800 ;;  # 7d
  esac

  local now expires
  now="$(date +%s)"
  expires=$(( snoozed_epoch + duration ))
  [ "$now" -lt "$expires" ] && return 0  # still snoozed
  return 1  # expired
}

# ── Fetch remote version ──────────────────────────────────────────────────────
LATEST_TAG=$(git ls-remote --tags --sort=-v:refname "$PUBLIC_REPO" 2>/dev/null \
  | head -1 \
  | sed 's/.*refs\/tags\///' \
  | sed 's/\^{}//' \
  | sed 's/^v//' \
  || echo "")

if [ -z "$LATEST_TAG" ]; then
  echo "{\"current\":\"${LOCAL}\",\"latest\":null,\"update_available\":false,\"reason\":\"no remote tags found\"}"
  exit 0
fi

if [ "$LOCAL" = "$LATEST_TAG" ]; then
  echo "{\"current\":\"${LOCAL}\",\"latest\":\"${LATEST_TAG}\",\"update_available\":false}"
  exit 0
fi

# Versions differ — upgrade available
# Check auto_upgrade config
if [ -f "$CONFIG_FILE" ]; then
  AUTO_UP=$(grep -E '^auto_upgrade:' "$CONFIG_FILE" 2>/dev/null | awk '{print $2}' || echo "false")
  if [ "$AUTO_UP" = "true" ]; then
    echo "{\"current\":\"${LOCAL}\",\"latest\":\"${LATEST_TAG}\",\"update_available\":true,\"auto_upgrade\":true}"
    exit 0
  fi
fi

if check_snooze "$LATEST_TAG"; then
  echo '{"skipped":true,"reason":"snoozed"}'
  exit 0
fi

echo "{\"current\":\"${LOCAL}\",\"latest\":\"${LATEST_TAG}\",\"update_available\":true}"
