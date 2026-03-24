#!/bin/bash
# setup.sh — Heurist Finance onboarding
# Idempotent: safe to run multiple times.
set -euo pipefail

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_SSE_URL="https://mcp.mesh.heurist.xyz/toolaac6abd2/sse"
HEURIST_DIR="${HOME}/.heurist"
REPORTS_DIR="${HOME}/.agents/reports"
CC_MCP_JSON="${HOME}/.mcp.json"
OC_CONFIG_JSON="${HOME}/.config/opencode/opencode.json"
CODEX_DIR="${HOME}/.codex"

# ---------------------------------------------------------------------------
# Colors & helpers
# ---------------------------------------------------------------------------
BRAND='\033[38;2;192;255;0m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
DIM='\033[2m'
BOLD='\033[1m'
RESET='\033[0m'

ok()   { printf "  ${GREEN}✓${RESET} %s\n" "$*"; }
fail() { printf "  ${RED}✗${RESET} %s\n" "$*"; }
info() { printf "  ${BRAND}→${RESET} %s\n" "$*"; }
warn() { printf "  ${YELLOW}!${RESET} %s\n" "$*"; }

TOTAL_STEPS=8
step() {
  local n=$1; shift
  local pct=$(( n * 100 / TOTAL_STEPS ))
  local filled=$(( pct / 5 ))
  local empty=$(( 20 - filled ))
  local bar="${BRAND}${BOLD}"
  for ((i=0; i<filled; i++)); do bar+="█"; done
  bar+="${DIM}"
  for ((i=0; i<empty; i++)); do bar+="░"; done
  bar+="${RESET}"
  printf "\n  ${bar} ${BOLD}%d/%d${RESET} ${DIM}%s${RESET}\n" "$n" "$TOTAL_STEPS" "$*"
}

# ---------------------------------------------------------------------------
# Wordmark
# ---------------------------------------------------------------------------
printf "\n"
printf "${BRAND}${BOLD}"
printf "  __    __   _______  __    __  .______       __       _______.___________.\n"
printf "  |  |  |  | |   ____||  |  |  | |   _  \\     |  |     /       |           |\n"
printf "  |  |__|  | |  |__   |  |  |  | |  |_)  |    |  |    |   (----\`---|  |----\`\n"
printf "  |   __   | |   __|  |  |  |  | |      /     |  |     \\   \\       |  |\n"
printf "  |  |  |  | |  |____ |  \`--'  | |  |\\  \\----.|  | .----)   |      |  |\n"
printf "  |__|  |__| |_______| \\______/  | _| \`._____||__| |_______/       |__|\n"
printf "\n"
printf "  _______  __  .__   __.      ___      .__   __.   ______  _______\n"
printf "  |   ____||  | |  \\ |  |     /   \\     |  \\ |  |  /      ||   ____|\n"
printf "  |  |__   |  | |   \\|  |    /  ^  \\    |   \\|  | |  ,----'|  |__\n"
printf "  |   __|  |  | |  . \`  |   /  /_\\  \\   |  . \`  | |  |     |   __|\n"
printf "  |  |     |  | |  |\\   |  /  _____  \\  |  |\\   | |  \`----.|  |____\n"
printf "  |__|     |__| |__| \\__| /__/     \\__\\ |__| \\__|  \\______||_______|\n"
printf "\n"
printf "       _______. __  ___  __   __       __\n"
printf "      /       ||  |/  / |  | |  |     |  |\n"
printf "     |   (----\`|  '  /  |  | |  |     |  |\n"
printf "      \\   \\    |    <   |  | |  |     |  |\n"
printf "  .----)   |   |  .  \\  |  | |  \`----.|  \`----.\n"
printf "  |_______/    |__|\\__\\ |__| |_______||_______|\n"
printf "${RESET}\n"

ERRORS=0

# ---------------------------------------------------------------------------
# 1. Node.js version check (>= 18 required)
# ---------------------------------------------------------------------------
step 1 "Checking Node.js"

if ! command -v node &>/dev/null; then
  fail "Node.js not found. Install Node.js >= 18 from https://nodejs.org/"
  ERRORS=$((ERRORS + 1))
else
  NODE_VERSION="$(node --version | sed 's/v//')"
  NODE_MAJOR="$(echo "$NODE_VERSION" | cut -d. -f1)"
  if [ "$NODE_MAJOR" -lt 18 ]; then
    fail "Node.js ${NODE_VERSION} found, but >= 18 is required."
    ERRORS=$((ERRORS + 1))
  else
    ok "Node.js ${NODE_VERSION}"
  fi
fi

# If Node is missing, nothing else will work — bail early.
if [ "$ERRORS" -gt 0 ]; then
  fail "Fatal: Node.js >= 18 required. Aborting."
  exit 1
fi

# ---------------------------------------------------------------------------
# 2. npm install --production
# ---------------------------------------------------------------------------
step 2 "Installing dependencies"

if [ -d "${SKILL_DIR}/node_modules/@modelcontextprotocol" ]; then
  ok "Dependencies already installed (node_modules present)"
else
  info "Running npm install --production in ${SKILL_DIR}"
  if npm install --production --prefix "${SKILL_DIR}" 2>&1; then
    ok "npm install complete"
  else
    fail "npm install failed"
    ERRORS=$((ERRORS + 1))
  fi
fi

# ---------------------------------------------------------------------------
# Helper: JSON manipulation (prefer jq, fall back to python3)
# ---------------------------------------------------------------------------
HAS_JQ=false
if command -v jq &>/dev/null; then
  HAS_JQ=true
fi

# Add heurist-finance SSE entry to a JSON config file.
# Usage: inject_mcp_entry <file> <agent-label>
inject_mcp_entry() {
  local file="$1"
  local label="$2"

  if [ ! -f "$file" ]; then
    info "Creating ${file}"
    echo '{}' > "$file"
  fi

  # Check if already present
  if $HAS_JQ; then
    if jq -e '.mcpServers["heurist-finance"]' "$file" &>/dev/null; then
      ok "heurist-finance already configured in ${file}"
      return 0
    fi
    # Inject
    local tmp
    tmp="$(mktemp)"
    jq '.mcpServers |= (. // {}) | .mcpServers["heurist-finance"] = {"type":"sse","url":"'"${MCP_SSE_URL}"'"}' \
      "$file" > "$tmp" && mv "$tmp" "$file"
    ok "Added heurist-finance SSE entry to ${file} (${label})"
  else
    # python3 fallback
    if python3 - <<PYEOF
import json, sys
with open('${file}') as f:
    data = json.load(f)
if data.get('mcpServers', {}).get('heurist-finance'):
    sys.exit(1)  # already present
sys.exit(0)
PYEOF
    then
      python3 - <<PYEOF
import json
with open('${file}') as f:
    data = json.load(f)
data.setdefault('mcpServers', {})['heurist-finance'] = {'type': 'sse', 'url': '${MCP_SSE_URL}'}
with open('${file}', 'w') as f:
    json.dump(data, f, indent=2)
PYEOF
      ok "Added heurist-finance SSE entry to ${file} (${label})"
    else
      ok "heurist-finance already configured in ${file}"
    fi
  fi
}

# ---------------------------------------------------------------------------
# 3. Detect agent and inject MCP config
# ---------------------------------------------------------------------------
step 3 "Detecting agent"

# Detect ALL installed agents, then pick the active one.
AGENTS=()
command -v claude &>/dev/null   && AGENTS+=(claude-code)
command -v opencode &>/dev/null && AGENTS+=(opencode)
command -v codex &>/dev/null    && AGENTS+=(codex)

# Env-var override takes priority
if [ -n "${HEURIST_AGENT:-}" ]; then
  DETECTED_AGENT="${HEURIST_AGENT}"
elif [ ${#AGENTS[@]} -eq 0 ]; then
  DETECTED_AGENT="unknown"
elif [ ${#AGENTS[@]} -eq 1 ]; then
  DETECTED_AGENT="${AGENTS[0]}"
else
  # Multiple agents installed — infer from session context:
  # 1. CLAUDE_CODE env var → Claude Code is the active session
  # 2. Parent process name heuristic
  # 3. Default to claude-code (most common)
  if [ -n "${CLAUDE_CODE:-}" ]; then
    DETECTED_AGENT="claude-code"
  elif ps -o comm= -p "$PPID" 2>/dev/null | grep -qi "opencode"; then
    DETECTED_AGENT="opencode"
  elif ps -o comm= -p "$PPID" 2>/dev/null | grep -qi "codex"; then
    DETECTED_AGENT="codex"
  else
    DETECTED_AGENT="claude-code"
  fi
  info "Found ${#AGENTS[@]} agents (${AGENTS[*]}), using ${DETECTED_AGENT}"
fi

info "Detected agent: ${DETECTED_AGENT}"

case "$DETECTED_AGENT" in
  claude-code)
    if [ -f "${CC_MCP_JSON}" ] && ($HAS_JQ && jq -e '.mcpServers["heurist-finance"]' "$CC_MCP_JSON" &>/dev/null); then
      ok "heurist-finance already configured in ${CC_MCP_JSON}"
    else
      printf "\n  ${BOLD}Claude Code detected.${RESET}\n"
      printf "  This will add the Heurist Mesh MCP server to %s\n\n" "${CC_MCP_JSON}"
      printf "  ${BOLD}Configure MCP now? [Y/n]${RESET} "
      read -r REPLY
      if [[ "$REPLY" =~ ^[Nn] ]]; then
        warn "Skipped. Add manually to ${CC_MCP_JSON}:"
        printf '    {"mcpServers":{"heurist-finance":{"type":"sse","url":"%s"}}}\n\n' "${MCP_SSE_URL}"
      else
        inject_mcp_entry "${CC_MCP_JSON}" "Claude Code"
      fi
    fi
    ;;
  opencode)
    if [ -f "${OC_CONFIG_JSON}" ] && grep -q 'heurist-finance' "$OC_CONFIG_JSON" 2>/dev/null; then
      ok "heurist-finance already configured in ${OC_CONFIG_JSON}"
    else
      printf "\n  ${BOLD}OpenCode detected.${RESET}\n"
      printf "  OpenCode connects via the MCP bridge at localhost:3100.\n"
      printf "  This will add heurist-finance to %s\n\n" "${OC_CONFIG_JSON}"
      printf "  ${BOLD}Configure MCP now? [Y/n]${RESET} "
      read -r REPLY
      if [[ "$REPLY" =~ ^[Nn] ]]; then
        warn "Skipped. Add manually to ${OC_CONFIG_JSON}:"
        printf '    "mcp": {"heurist-finance": {"type": "remote", "url": "http://localhost:3100/mcp"}}\n\n'
      else
        mkdir -p "$(dirname "${OC_CONFIG_JSON}")"
        if [ ! -f "$OC_CONFIG_JSON" ]; then
          echo '{}' > "$OC_CONFIG_JSON"
        fi
        if $HAS_JQ; then
          local tmp
          tmp="$(mktemp)"
          jq '.mcp |= (. // {}) | .mcp["heurist-finance"] = {"type":"remote","url":"http://localhost:3100/mcp"}' \
            "$OC_CONFIG_JSON" > "$tmp" && mv "$tmp" "$OC_CONFIG_JSON"
        else
          python3 - <<PYEOF
import json
with open('${OC_CONFIG_JSON}') as f:
    data = json.load(f)
data.setdefault('mcp', {})['heurist-finance'] = {'type': 'remote', 'url': 'http://localhost:3100/mcp'}
with open('${OC_CONFIG_JSON}', 'w') as f:
    json.dump(data, f, indent=2)
PYEOF
        fi
        ok "Added heurist-finance to ${OC_CONFIG_JSON}"
        info "Start the bridge before using OpenCode: node ${SKILL_DIR}/bridge/index.js &"
      fi
    fi
    ;;
  codex)
    CODEX_TOML="${HOME}/.codex/config.toml"
    if [ -f "$CODEX_TOML" ] && grep -q 'heurist-finance' "$CODEX_TOML" 2>/dev/null; then
      ok "heurist-finance already configured in ${CODEX_TOML}"
    else
      printf "\n  ${BOLD}Codex CLI detected.${RESET}\n"
      printf "  Heurist Finance uses an MCP bridge at localhost:3100.\n"
      printf "  This will add the MCP server config to %s\n\n" "${CODEX_TOML}"
      printf "  ${BOLD}Configure Codex MCP now? [Y/n]${RESET} "
      read -r REPLY
      if [[ "$REPLY" =~ ^[Nn] ]]; then
        warn "Skipped. To configure manually, add to ${CODEX_TOML}:"
        printf "    [mcp_servers.heurist-finance]\n"
        printf "    type = \"http\"\n"
        printf "    url = \"http://localhost:3100/mcp\"\n\n"
      else
        mkdir -p "$(dirname "${CODEX_TOML}")"
        if [ ! -f "$CODEX_TOML" ]; then
          echo "" > "$CODEX_TOML"
        fi
        # Append MCP config
        cat >> "$CODEX_TOML" <<'TOML'

[mcp_servers.heurist-finance]
type = "http"
url = "http://localhost:3100/mcp"
TOML
        ok "Added heurist-finance to ${CODEX_TOML}"
        info "Start the bridge before using Codex: node ${SKILL_DIR}/bridge/index.js &"
      fi
    fi
    ;;
  unknown)
    warn "Could not detect agent. Attempting Claude Code config as default."
    info "Configuring ~/.mcp.json (Claude Code default)"
    inject_mcp_entry "${CC_MCP_JSON}" "Claude Code (default)"
    warn "If using OpenCode, also update ~/.config/opencode/opencode.json manually."
    ;;
esac

# ---------------------------------------------------------------------------
# 4. Create ~/.heurist config directory
# ---------------------------------------------------------------------------
step 4 "Config directory"

if mkdir -p "${HEURIST_DIR}"; then
  ok "Config directory: ${HEURIST_DIR}"
else
  fail "Could not create ${HEURIST_DIR}"
  ERRORS=$((ERRORS + 1))
fi

# ---------------------------------------------------------------------------
# 5. Create default config if missing
# ---------------------------------------------------------------------------
step 5 "Writing config"

CONFIG_FILE="${HEURIST_DIR}/config.yaml"

if [ -f "${CONFIG_FILE}" ]; then
  ok "Config already exists: ${CONFIG_FILE}"
else
  cat > "${CONFIG_FILE}" <<'YAML'
# Heurist Finance configuration
theme: heurist
auto_update_check: true
first_run: true
YAML
  ok "Created default config: ${CONFIG_FILE}"
fi

# ---------------------------------------------------------------------------
# 6. Register `hf` command
# ---------------------------------------------------------------------------
step 6 "Shell command"

LOCAL_BIN="${HOME}/.local/bin"
HF_LINK="${LOCAL_BIN}/hf"
HF_TARGET="${SKILL_DIR}/bin/hf"

if [ -L "$HF_LINK" ] && [ "$(readlink "$HF_LINK")" = "$HF_TARGET" ]; then
  ok "hf command already registered"
elif [ -e "$HF_LINK" ]; then
  warn "~/.local/bin/hf exists but points elsewhere — skipping"
  warn "Remove it manually if you want hf to point to Heurist Finance"
else
  printf "\n  ${BOLD}Register 'hf' as a shell command?${RESET}\n"
  printf "  This creates a symlink: %s → %s\n\n" "${HF_LINK}" "${HF_TARGET}"
  printf "  ${BOLD}Install hf command? [Y/n]${RESET} "
  read -r REPLY
  if [[ "$REPLY" =~ ^[Nn] ]]; then
    warn "Skipped. Run the TUI manually: ${HF_TARGET}"
  else
    mkdir -p "${LOCAL_BIN}"
    ln -sf "${HF_TARGET}" "${HF_LINK}"
    ok "hf command installed → ${HF_LINK}"
    # Check if ~/.local/bin is in PATH
    if ! echo "$PATH" | tr ':' '\n' | grep -qx "${LOCAL_BIN}"; then
      warn "~/.local/bin is not in your PATH"
      info "Add to your shell profile: export PATH=\"\${HOME}/.local/bin:\${PATH}\""
    fi
  fi
fi

# ---------------------------------------------------------------------------
# 7. Create reports directory
# ---------------------------------------------------------------------------
step 7 "Reports directory"

if mkdir -p "${REPORTS_DIR}"; then
  ok "Reports directory: ${REPORTS_DIR}"
else
  fail "Could not create ${REPORTS_DIR}"
  ERRORS=$((ERRORS + 1))
fi

# ---------------------------------------------------------------------------
# 8. Verify MCP connectivity
# ---------------------------------------------------------------------------
step 8 "MCP connectivity"

if ! command -v curl &>/dev/null; then
  warn "curl not found — skipping connectivity check."
else
  info "Probing SSE endpoint: ${MCP_SSE_URL}"
  HTTP_STATUS="$(curl -s -o /dev/null -w "%{http_code}" \
    --max-time 8 \
    -H "Accept: text/event-stream" \
    "${MCP_SSE_URL}" 2>/dev/null || echo "000")"

  # SSE endpoints return 200 and stream; any 2xx is a pass.
  if [[ "$HTTP_STATUS" =~ ^2 ]]; then
    ok "MCP endpoint reachable (HTTP ${HTTP_STATUS})"
  elif [ "$HTTP_STATUS" = "000" ]; then
    fail "MCP endpoint unreachable (connection error or timeout)"
    warn "Check your network. URL: ${MCP_SSE_URL}"
    ERRORS=$((ERRORS + 1))
  else
    warn "MCP endpoint returned HTTP ${HTTP_STATUS} — may still be functional"
    warn "URL: ${MCP_SSE_URL}"
  fi
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
printf "\n${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}\n"
printf "${BOLD}  Heurist Finance v1 — Setup Summary${RESET}\n"
printf "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}\n"
printf "  Skill dir  : %s\n"   "${SKILL_DIR}"
printf "  Config     : %s\n"   "${CONFIG_FILE}"
printf "  Reports    : %s\n"   "${REPORTS_DIR}"
printf "  Agent      : %s\n"   "${DETECTED_AGENT}"
printf "  MCP URL    : %s\n"   "${MCP_SSE_URL}"

case "$DETECTED_AGENT" in
  claude-code) printf "  MCP config : %s\n" "${CC_MCP_JSON}" ;;
  opencode)    printf "  MCP config : %s\n" "${OC_CONFIG_JSON}" ;;
  codex)       printf "  MCP config : %s (manual — see instructions above)\n" "${CODEX_DIR}" ;;
  *)           printf "  MCP config : %s (default)\n" "${CC_MCP_JSON}" ;;
esac

if [ "$ERRORS" -eq 0 ]; then
  printf "\n${GREEN}${BOLD}  All checks passed. Heurist Finance is ready.${RESET}\n"
  if [ "$DETECTED_AGENT" != "codex" ]; then
    printf "${YELLOW}  Restart your agent if you just added the MCP config.${RESET}\n"
  fi
  # tmux hyperlink tip
  if [ -n "${TMUX:-}" ]; then
    printf "\n${DIM}  tmux tip: for clickable news links, add to tmux.conf:${RESET}\n"
    printf "${DIM}  set -ga terminal-features \",xterm*:hyperlinks\"${RESET}\n"
    printf "${DIM}  then start a new tmux session.${RESET}\n"
  fi
  printf "\n"
  exit 0
else
  printf "\n${RED}${BOLD}  Setup completed with ${ERRORS} error(s). Review output above.${RESET}\n\n"
  exit 1
fi
