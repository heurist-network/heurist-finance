#!/bin/bash
# setup.sh — Heurist Finance onboarding (headless)
# Outputs a single JSON line for agent consumption.
# Idempotent: safe to run multiple times.
set -uo pipefail

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_URL="https://mesh.heurist.xyz/mcp/heurist-finance"
HEURIST_DIR="${HOME}/.heurist"
REPORTS_DIR="${HOME}/.agents/reports"
CC_MCP_JSON="$(pwd)/.mcp.json"
OC_CONFIG_JSON="${HOME}/.config/opencode/opencode.json"
CODEX_DIR="${HOME}/.codex"

ERRORS=()

# ---------------------------------------------------------------------------
# Helper: resolve API key
# ---------------------------------------------------------------------------
resolve_api_key() {
  local config_file="${HEURIST_DIR}/config.yaml"
  local key

  if [ -f "$config_file" ]; then
    key="$(grep -E '^api_key:' "$config_file" 2>/dev/null | sed 's/^api_key:[[:space:]]*//' | tr -d '"'"'" || true)"
    if [ -n "$key" ]; then
      echo "$key"
      return 0
    fi
  fi

  if [ -n "${HEURIST_API_KEY:-}" ]; then
    echo "${HEURIST_API_KEY}"
    return 0
  fi

  return 1
}

# ---------------------------------------------------------------------------
# Helper: JSON manipulation (prefer jq, fall back to python3)
# ---------------------------------------------------------------------------
HAS_JQ=false
if command -v jq &>/dev/null; then
  HAS_JQ=true
fi

# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------
NODE_OK=false
DEPS_OK=false
API_KEY_OK=false
MCP_CONFIGURED=false
HF_COMMAND=false
MCP_REACHABLE=false

# ---------------------------------------------------------------------------
# 1. Node.js version check (>= 18 required)
# ---------------------------------------------------------------------------
if ! command -v node &>/dev/null; then
  ERRORS+=("node_missing")
elif [ "$(node --version | sed 's/v//' | cut -d. -f1)" -lt 18 ]; then
  ERRORS+=("node_outdated")
else
  NODE_OK=true
fi

# If Node is missing, nothing else will work — bail early.
if [ "$NODE_OK" != "true" ]; then
  printf '{"status":"error","errors":["%s"],"agent":"unknown"}\n' "$(IFS='","'; echo "${ERRORS[*]}")"
  exit 0
fi

# ---------------------------------------------------------------------------
# 2. npm install --production
# ---------------------------------------------------------------------------
if [ -d "${SKILL_DIR}/node_modules" ]; then
  DEPS_OK=true
else
  if npm install --production --prefix "${SKILL_DIR}" >/dev/null 2>&1; then
    DEPS_OK=true
  else
    ERRORS+=("npm_install_failed")
  fi
fi

# ---------------------------------------------------------------------------
# 3. Detect agent, get API key, inject MCP config
# ---------------------------------------------------------------------------
AGENTS=()
command -v claude &>/dev/null   && AGENTS+=(claude-code)
command -v opencode &>/dev/null && AGENTS+=(opencode)
command -v codex &>/dev/null    && AGENTS+=(codex)

if [ -n "${TERMINAL_AGENT:-}" ]; then
  DETECTED_AGENT="${TERMINAL_AGENT}"
elif [ ${#AGENTS[@]} -eq 0 ]; then
  DETECTED_AGENT="unknown"
elif [ ${#AGENTS[@]} -eq 1 ]; then
  DETECTED_AGENT="${AGENTS[0]}"
else
  if [ -n "${CLAUDE_CODE:-}" ]; then
    DETECTED_AGENT="claude-code"
  elif ps -o comm= -p "$PPID" 2>/dev/null | grep -qi "opencode"; then
    DETECTED_AGENT="opencode"
  elif ps -o comm= -p "$PPID" 2>/dev/null | grep -qi "codex"; then
    DETECTED_AGENT="codex"
  else
    DETECTED_AGENT="claude-code"
  fi
fi

# Resolve API key
API_KEY="$(resolve_api_key)" || true
if [ -z "${API_KEY:-}" ]; then
  ERRORS+=("api_key_missing")
else
  API_KEY_OK=true
fi

# Inject MCP config (only if we have an API key)
if [ "$API_KEY_OK" = "true" ]; then
  case "$DETECTED_AGENT" in
    claude-code)
      if [ -f "${CC_MCP_JSON}" ] && ($HAS_JQ && jq -e '.mcpServers["heurist-finance"]' "$CC_MCP_JSON" &>/dev/null); then
        MCP_CONFIGURED=true
      else
        if [ ! -f "$CC_MCP_JSON" ]; then
          echo '{}' > "$CC_MCP_JSON"
        fi
        if $HAS_JQ; then
          tmp="$(mktemp)"
          jq --arg url "$MCP_URL" --arg key "${API_KEY}" \
            '.mcpServers |= (. // {}) | .mcpServers["heurist-finance"] = {"type":"http","url":$url,"headers":{"Authorization":("Bearer " + $key)}}' \
            "$CC_MCP_JSON" > "$tmp" && mv "$tmp" "$CC_MCP_JSON"
          MCP_CONFIGURED=true
        else
          python3 - <<PYEOF && MCP_CONFIGURED=true
import json
with open('${CC_MCP_JSON}') as f:
    data = json.load(f)
data.setdefault('mcpServers', {})['heurist-finance'] = {
    'type': 'http',
    'url': '${MCP_URL}',
    'headers': {'Authorization': 'Bearer ${API_KEY}'}
}
with open('${CC_MCP_JSON}', 'w') as f:
    json.dump(data, f, indent=2)
PYEOF
        fi
      fi
      ;;
    opencode)
      if [ -f "${OC_CONFIG_JSON}" ] && grep -q 'heurist-finance' "$OC_CONFIG_JSON" 2>/dev/null; then
        MCP_CONFIGURED=true
      else
        mkdir -p "$(dirname "${OC_CONFIG_JSON}")"
        if [ ! -f "$OC_CONFIG_JSON" ]; then
          echo '{}' > "$OC_CONFIG_JSON"
        fi
        if $HAS_JQ; then
          tmp="$(mktemp)"
          jq --arg url "$MCP_URL" --arg key "${API_KEY}" \
            '.mcp |= (. // {}) | .mcp["heurist-finance"] = {"type":"remote","url":$url,"headers":{"Authorization":("Bearer " + $key)}}' \
            "$OC_CONFIG_JSON" > "$tmp" && mv "$tmp" "$OC_CONFIG_JSON"
          MCP_CONFIGURED=true
        else
          python3 - <<PYEOF && MCP_CONFIGURED=true
import json
with open('${OC_CONFIG_JSON}') as f:
    data = json.load(f)
data.setdefault('mcp', {})['heurist-finance'] = {
    'type': 'remote',
    'url': '${MCP_URL}',
    'headers': {'Authorization': 'Bearer ${API_KEY}'}
}
with open('${OC_CONFIG_JSON}', 'w') as f:
    json.dump(data, f, indent=2)
PYEOF
        fi
      fi
      ;;
    codex)
      CODEX_TOML="${HOME}/.codex/config.toml"
      if [ -f "$CODEX_TOML" ] && grep -q 'heurist-finance' "$CODEX_TOML" 2>/dev/null; then
        MCP_CONFIGURED=true
      else
        mkdir -p "$(dirname "${CODEX_TOML}")"
        if [ ! -f "$CODEX_TOML" ]; then
          echo "" > "$CODEX_TOML"
        fi
        cat >> "$CODEX_TOML" <<TOML

[mcp_servers.heurist-finance]
url = "${MCP_URL}"
bearer_token_env_var = "HEURIST_API_KEY"
TOML
        MCP_CONFIGURED=true
      fi
      ;;
    unknown)
      if [ ! -f "$CC_MCP_JSON" ]; then
        echo '{}' > "$CC_MCP_JSON"
      fi
      if $HAS_JQ; then
        tmp="$(mktemp)"
        jq --arg url "$MCP_URL" --arg key "${API_KEY}" \
          '.mcpServers |= (. // {}) | .mcpServers["heurist-finance"] = {"type":"http","url":$url,"headers":{"Authorization":("Bearer " + $key)}}' \
          "$CC_MCP_JSON" > "$tmp" && mv "$tmp" "$CC_MCP_JSON"
        MCP_CONFIGURED=true
      else
        python3 - <<PYEOF && MCP_CONFIGURED=true
import json
with open('${CC_MCP_JSON}') as f:
    data = json.load(f)
data.setdefault('mcpServers', {})['heurist-finance'] = {
    'type': 'http',
    'url': '${MCP_URL}',
    'headers': {'Authorization': 'Bearer ${API_KEY}'}
}
with open('${CC_MCP_JSON}', 'w') as f:
    json.dump(data, f, indent=2)
PYEOF
      fi
      ;;
  esac

  # Save API key to config.yaml if not already there
  CONFIG_FILE="${HEURIST_DIR}/config.yaml"
  if [ -f "$CONFIG_FILE" ] && ! grep -qE '^api_key:' "$CONFIG_FILE" 2>/dev/null; then
    echo "api_key: ${API_KEY}" >> "$CONFIG_FILE"
  fi
fi

# ---------------------------------------------------------------------------
# 4. Create ~/.heurist config directory + default config
# ---------------------------------------------------------------------------
mkdir -p "${HEURIST_DIR}" 2>/dev/null || ERRORS+=("config_dir_failed")

CONFIG_FILE="${HEURIST_DIR}/config.yaml"
if [ ! -f "${CONFIG_FILE}" ]; then
  cat > "${CONFIG_FILE}" <<YAML
# Heurist Finance configuration
theme: heurist
auto_update_check: true
first_run: true
YAML
  if [ -n "${API_KEY:-}" ]; then
    echo "api_key: ${API_KEY}" >> "${CONFIG_FILE}"
  fi
fi

# ---------------------------------------------------------------------------
# 5. Register `hf` command
# ---------------------------------------------------------------------------
LOCAL_BIN="${HOME}/.local/bin"
HF_LINK="${LOCAL_BIN}/hf"
HF_TARGET="${SKILL_DIR}/bin/hf"

if [ -L "$HF_LINK" ] && [ "$(readlink "$HF_LINK")" = "$HF_TARGET" ]; then
  HF_COMMAND=true
elif mkdir -p "${LOCAL_BIN}" 2>/dev/null && ln -sf "${HF_TARGET}" "${HF_LINK}" 2>/dev/null; then
  HF_COMMAND=true
fi

# ---------------------------------------------------------------------------
# 6. Create reports directory
# ---------------------------------------------------------------------------
mkdir -p "${REPORTS_DIR}" 2>/dev/null || ERRORS+=("reports_dir_failed")

# ---------------------------------------------------------------------------
# 7. Verify MCP connectivity
# ---------------------------------------------------------------------------
if command -v curl &>/dev/null; then
  HTTP_STATUS="$(curl -s -o /dev/null -w "%{http_code}" \
    --max-time 8 \
    -X POST \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d '{"jsonrpc":"2.0","method":"initialize","id":0,"params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"setup","version":"0.1"}}}' \
    "${MCP_URL}" 2>/dev/null || echo "000")"

  if [[ "$HTTP_STATUS" =~ ^2 ]]; then
    MCP_REACHABLE=true
  else
    ERRORS+=("mcp_unreachable")
  fi
fi

# ---------------------------------------------------------------------------
# Output JSON
# ---------------------------------------------------------------------------
if [ ${#ERRORS[@]} -eq 0 ]; then
  STATUS="ok"
else
  STATUS="error"
fi

# Build errors JSON array
ERR_JSON="[]"
if [ ${#ERRORS[@]} -gt 0 ]; then
  ERR_JSON="["
  for i in "${!ERRORS[@]}"; do
    [ "$i" -gt 0 ] && ERR_JSON+=","
    ERR_JSON+="\"${ERRORS[$i]}\""
  done
  ERR_JSON+="]"
fi

printf '{"status":"%s","errors":%s,"agent":"%s","api_key":%s,"deps_ok":%s,"mcp_configured":%s,"hf_command":%s,"mcp_reachable":%s}\n' \
  "$STATUS" "$ERR_JSON" "$DETECTED_AGENT" "$API_KEY_OK" "$DEPS_OK" "$MCP_CONFIGURED" "$HF_COMMAND" "$MCP_REACHABLE"

exit 0
