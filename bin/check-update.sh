#!/bin/bash
# bin/check-update.sh — Check if a newer version is available on the remote.
#
# Compares local package.json version against latest git tag on origin.
# Outputs JSON: {"current":"0.9.1","latest":"0.9.11","update_available":true}
#
# Exit codes:
#   0 — check completed (regardless of whether update is available)
#   1 — check failed (network, no remote, etc.)
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && cd .. && pwd)"
CONFIG_FILE="${HOME}/.heurist/config.yaml"

# ── Check if auto-update is disabled ────────────────────────────────────────
if [ -f "$CONFIG_FILE" ]; then
  # Parse auto_update_check from YAML (simple grep, no YAML parser needed)
  AUTO_CHECK=$(grep -E '^auto_update_check:' "$CONFIG_FILE" 2>/dev/null | awk '{print $2}' || echo "true")
  if [ "$AUTO_CHECK" = "false" ]; then
    echo '{"skipped":true,"reason":"auto_update_check disabled in config"}'
    exit 0
  fi
fi

# ── Get local version ───────────────────────────────────────────────────────
LOCAL_VERSION=$(node -e "console.log(require('${SKILL_DIR}/package.json').version)" 2>/dev/null || echo "unknown")
if [ "$LOCAL_VERSION" = "unknown" ]; then
  echo '{"error":"Could not read local version from package.json"}'
  exit 1
fi

# ── Get latest tag from remote ──────────────────────────────────────────────
# Timeout after 5 seconds to avoid blocking the agent
LATEST_TAG=$(cd "$SKILL_DIR" && git ls-remote --tags --sort=-v:refname origin 2>/dev/null \
  | head -1 \
  | sed 's/.*refs\/tags\///' \
  | sed 's/\^{}//' \
  | sed 's/^v//' \
  || echo "")

if [ -z "$LATEST_TAG" ]; then
  # No tags or no remote — can't check
  echo "{\"current\":\"${LOCAL_VERSION}\",\"latest\":null,\"update_available\":false,\"reason\":\"no remote tags found\"}"
  exit 0
fi

# ── Compare versions ────────────────────────────────────────────────────────
if [ "$LOCAL_VERSION" = "$LATEST_TAG" ]; then
  UPDATE="false"
else
  # Simple comparison: if latest != current, update available
  # (assumes tags are always forward — no downgrades)
  UPDATE="true"
fi

echo "{\"current\":\"${LOCAL_VERSION}\",\"latest\":\"${LATEST_TAG}\",\"update_available\":${UPDATE}}"
