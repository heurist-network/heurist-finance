# Architecture

## System overview

```
  +--------------------------------------------------------------+
  |                        Agent Host                            |
  |  (Claude Code / OpenCode / Codex CLI)                       |
  |                                                              |
  |  SKILL.md --> routes query to sub-skill                     |
  |  Sub-skill --> fetches data via MCP tools                   |
  |  Sub-skill --> POSTs panels to TUI server                   |
  +----------+------------------------------------+--------------+
             | MCP (Streamable HTTP)              | HTTP POST /render
             v                                    v
  +--------------------+             +----------------------+
  |  Heurist Mesh      |             |  TUI Server          |
  |  mesh.heurist.xyz  |             |  localhost:7707      |
  |  /mcp/heurist-     |             |                      |
  |                    |             |  Plain JS TUI        |
  |  Yahoo Finance    |             |  20 components       |
  |  FRED Macro       |             |  Block engine (7 types) |
  |  SEC EDGAR        |             |  Progressive render  |
  |  Exa Search       |             |  Request analytics   |
  +--------------------+             +----------------------+
```

## Directory structure

```
heurist-finance/
+-- SKILL.md              # Main skill - routing + MCP tool reference
+-- skills/               # Sub-skills (one per research mode)
|   +-- analyst/          # Single-ticker analysis
|   +-- compare/          # Multi-ticker comparison
|   +-- macro/            # Macro/strategy
|   +-- sector/           # Sector/thematic
|   +-- desk/             # Broad market snapshot
|   +-- risk/             # Risk/event impact
|   +-- options/          # Single-ticker options analysis
|   +-- futures/          # Futures & commodities
|   +-- watch/            # Tracked tickers
+-- src/                  # Component library
|   +-- components/       # 20 terminal widgets + tests + snapshots
|   +-- ansi.js           # ANSI escape utilities
|   +-- formatters.js     # Number/currency/percent formatting
|   +-- themes.js         # Color themes (heurist default)
|   +-- index.js          # Public exports
+-- terminal/             # TUI server (plain Node.js event loop)
|   +-- app.js            # Event loop, keyboard input, splash/live phases
|   +-- splash.js         # Splash screen rendering
|   +-- render.js         # Render loop and output
|   +-- scroll.js         # Scroll state and keyboard handler
|   +-- io.js             # Raw terminal I/O
|   +-- state.js          # TUI state management + patch merging
|   +-- cost.js           # Cost tracking display
|   +-- logo.js           # ASCII logo
|   +-- version.js        # Version display
|   +-- engine.js         # Block-based layout engine (7 block types)
|   +-- panels.js         # Panel adapter + presetToBlocks backward compat
|   +-- server.js         # HTTP server - POST /render, GET /health, GET /stats
|   +-- debugLog.js       # Opt-in debug logging (schema, render, state)
|   +-- schemas/          # Panel payload schemas (20 validators)
+-- bin/                  # Shell scripts and launchers
|   +-- hf               # Main launcher
|   +-- hf-post          # Post panels from CLI
|   +-- hf-chart         # Chart rendering helper
|   +-- hf-config        # Config manager (get/set telemetry, debug_log)
|   +-- hf-telemetry-log # Session telemetry logger
|   +-- hf-telemetry-sync # Background sync to remote endpoint
|   +-- check-update.sh  # Update check
|   +-- screenshot.js    # Screenshot utility
|   +-- start.sh         # Start TUI
|   +-- stop.sh          # Stop TUI (clean shutdown)
|   +-- render.sh        # CLI render helper
+-- telemetry-server/     # Telemetry receiver (dev repo only, not public)
|   +-- index.js          # HTTP server - POST /ingest, GET /stats
+-- setup.sh              # Onboarding - agent detection, MCP config, deps
```

## Data flow

```
  User query
       |
       v
  SKILL.md classifies --> sub-skill SKILL.md
       |
       v
  MCP tool calls (parallel)
  +------------------------------------+
  | quote_snapshot    price_history     |
  | technical_snapshot analyst_snapshot |
  | macro_regime_context news_search   |
  +------------------------------------+
       |
       v
  Sub-skill maps responses to panel shapes
       |
       v
  Write to /tmp/hf-render.json
  +------------------------------------+
  | {                                  |
  |   "blocks": [...],                |
  |   "patch": true,                  |
  |   "_state": {                     |
  |     "stage": "gathering",         |
  |     "skill": "analyst",           |
  |     "tools": { "called": 4 }      |
  |   }                               |
  | }                                  |
  +------------------------------------+
       |
       v
  POST /render {"action":"render","file":"/tmp/hf-render.json"}
       |
       v
  app.js receives event --> block engine renders layout
       |                          |
       v                          v
  panels.js adapts shapes    Engine renders block tree
       |
       v
  Component functions produce ANSI strings
       |
       v
  Terminal output
```

## Component library (src/components/)

All components are pure functions: `(props) - string` (ANSI-formatted).

| Component | What it renders |
|-----------|----------------|
| QuoteHeader | Ticker, price, change%, volume, market cap |
| BrailleChart | Sparkline using braille unicode characters |
| CandlestickChart | OHLC candlestick bars |
| AnalystBar | Buy/hold/sell consensus bar |
| GaugeBar | Min-max gauge with current value marker |
| HeatMap | Grid of colored cells by value |
| MacroDashboard | Multi-pillar regime summary |
| NewsStream | Headline list with source and time |
| Verdict | Conviction badge + thesis text |
| CorrelationMatrix | Pairwise correlation grid |
| EarningsSurprise | Beat/miss history plot |
| FilingTimeline | SEC filing event timeline |
| FlowSankey | Flow diagram (fund flows, sector rotation) |
| HolderBar | Institutional ownership bar |
| InsiderTimeline | Insider buy/sell activity |
| TreeMap | Proportional area visualization |
| WaterfallChart | Cumulative change waterfall |
| RSI | RSI gauge with overbought/oversold zones |
| Technical | Section-based technical analysis panel |
| Gauges | Multi-gauge dashboard (grouped indicators) |

## Panel adapter pattern (terminal/panels.js)

SKILL.md documents flat payload shapes (e.g., `{symbol, buy, hold, sell}`).
Components expect specific prop structures (e.g., `{ticker, ratings: {buy, hold, sell}}`).

`panels.js` is the adapter layer that bridges the gap. Each panel case normalizes
the incoming data to match what the component function expects.

`presetToBlocks()` in `panels.js` provides backward compatibility - it converts legacy `layout + panels` payloads into the blocks array format.

## TUI server (terminal/server.js)

- HTTP server on port 7707 (configurable via env)
- State file at `~/.heurist/tui.json` - PID, port, start time
- Actions: `render`, `focus`, `layout`, `clear`
- File-based POST protocol - inline blocks rejected with 400
- Progressive rendering via `patch: true` - panels accumulate incrementally
- `_state` protocol - stage, skill, tools progress, follow-ups
- Request analytics logged to `~/.heurist/analytics/requests.jsonl`
- GET /stats endpoint for session analytics
- Scroll support: keyboard (j/k/up/down/PgUp/PgDn/g/G) + mouse wheel (SGR mode)
- Block engine: 7 types - panel, table, row, stack, divider, text, spacer

## MCP connection

All agents connect directly to Heurist Mesh via Streamable HTTP:

```
Endpoint: https://mesh.heurist.xyz/mcp/heurist-finance
Auth:     Authorization: Bearer <api-key>
```

No bridge or local proxy needed. Claude Code, OpenCode, and Codex CLI all
support Streamable HTTP natively.

## Config directory (~/.heurist/)

```
~/.heurist/
+-- config.yaml    - User preferences (theme, api_key, telemetry, debug_log)
+-- tui.json       - TUI state (pid, port, startedAt) - written by server.js
+-- sessions/      - Agent session memory (conviction tracking)
+-- analytics/     - Request and session telemetry (JSONL, local-only)
+-- debug.log      - Opt-in debug log (schema coercions, render events)
```

Created on first run. State files use atomic tmp+rename writes, mode 0o600.

## Telemetry

Three tiers (user chooses on first run):
- **Community** - hashed device ID, skill usage, duration, outcome. Syncs to heurist.xyz.
- **Anonymous** - same data, no device ID.
- **Off** - nothing collected or sent.

Server-side request logging (`analytics/requests.jsonl`) is always local-only.
Session telemetry (`analytics/sessions.jsonl`) respects the user's consent tier.

Sensitive fields (query text, tickers, thesis) are never included in telemetry.

## Test coverage

779 tests across 28 test files. Primarily unit tests for components (snapshot-based)
and integration tests for the TUI server and schema validators.

```bash
npm test        # vitest run, ~3s
```
