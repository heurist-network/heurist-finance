# Architecture

## System overview

```
  ┌──────────────────────────────────────────────────────────────┐
  │                        Agent Host                            │
  │  (Claude Code / OpenCode / Codex CLI)                       │
  │                                                              │
  │  SKILL.md ──▶ routes query to sub-skill                     │
  │  Sub-skill ──▶ fetches data via MCP tools                   │
  │  Sub-skill ──▶ POSTs panels to TUI server                  │
  └──────────┬────────────────────────────────┬──────────────────┘
             │ MCP (SSE or bridge)            │ HTTP POST /render
             ▼                                ▼
  ┌──────────────────┐             ┌──────────────────────┐
  │  Heurist Mesh    │             │  TUI Server          │
  │  mcp.mesh.       │             │  localhost:7707      │
  │  heurist.xyz     │             │                      │
  │                  │             │  Plain JS TUI         │
  │  Yahoo Finance   │             │  17 components       │
  │  FRED Macro      │             │  Block engine (7 types) │
  │  SEC EDGAR       │             │  Progressive render  │
  │  Exa Search      │             │                      │
  └──────────────────┘             └──────────────────────┘
```

## Directory structure

```
heurist-finance/
├── SKILL.md              # Main skill — routing + MCP tool reference
├── skills/               # Sub-skills (one per research mode)
│   ├── analyst/          # Single-ticker analysis
│   ├── pm/               # Portfolio manager view
│   ├── strategist/       # Macro/strategy
│   ├── sector-head/      # Sector/thematic
│   ├── desk/             # Broad market snapshot
│   ├── risk/             # Risk/event impact
│   └── watch/            # Tracked tickers
├── src/                  # Component library
│   ├── components/       # 17 terminal widgets + tests + snapshots
│   ├── ansi.js           # ANSI escape utilities
│   ├── formatters.js     # Number/currency/percent formatting
│   ├── themes.js         # Color themes (heurist default)
│   └── index.js          # Public exports
├── terminal/               # TUI server (plain Node.js event loop)
│   ├── app.js            # Event loop, keyboard input, splash/live phases
│   ├── splash.js         # Splash screen rendering
│   ├── render.js         # Render loop and output
│   ├── scroll.js         # Scroll state and keyboard handler
│   ├── io.js             # Raw terminal I/O
│   ├── state.js          # TUI state management
│   ├── cost.js           # Cost tracking display
│   ├── logo.js           # ASCII logo
│   ├── version.js        # Version display
│   ├── engine.js         # Block-based layout engine (7 block types)
│   ├── panels.js         # Panel adapter + presetToBlocks backward compat
│   ├── server.js         # HTTP server — POST /render, GET /health
│   └── schemas/          # Panel payload schemas
├── bridge/               # MCP bridge (SSE → Streamable HTTP)
│   └── index.js          # Proxy + local resources (heurist://skill, tools, layouts)
├── bin/                  # Shell scripts and launchers
│   ├── hf               # Main launcher
│   ├── hf-post          # Post panels from CLI
│   ├── hf-chart         # Chart rendering helper
│   ├── check-update.sh  # Update check
│   ├── screenshot.js    # Screenshot utility
│   ├── start.sh          # Start TUI
│   ├── stop.sh           # Stop TUI (clean shutdown)
│   └── render.sh         # CLI render helper
└── setup.sh              # Onboarding — agent detection, MCP config, deps
```

## Data flow

```
  User query
       │
       ▼
  SKILL.md classifies ──▶ sub-skill SKILL.md
       │
       ▼
  MCP tool calls (parallel)
  ┌────────────────────────────────────┐
  │ quote_snapshot    price_history    │
  │ technical_snapshot analyst_snapshot│
  │ macro_regime_context news_search  │
  └────────────────────────────────────┘
       │
       ▼
  Sub-skill maps responses to panel shapes
       │
       ▼
  POST /render → TUI server
  ┌────────────────────────────────────┐
  │ {                                  │
  │   action: "render",               │
  │   blocks: [                       │
  │     { type: "panel", ... },       │
  │     { type: "table", ... },       │
  │     { type: "row", children: [] } │
  │   ]                               │
  │ }                                  │
  └────────────────────────────────────┘
       │
       ▼
  app.js receives event ──▶ block engine renders layout
       │                          │
       ▼                          ▼
  panels.js adapts shapes    Engine renders block tree
       │
       ▼
  Component functions produce ANSI strings
       │
       ▼
  Terminal output
```

## Component library (src/components/)

All components are pure functions: `(props) → string` (ANSI-formatted).

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
| Verdict | Signal badge + thesis text |
| CorrelationMatrix | Pairwise correlation grid |
| EarningsSurprise | Beat/miss history plot |
| FilingTimeline | SEC filing event timeline |
| FlowSankey | Flow diagram (fund flows, sector rotation) |
| HolderBar | Institutional ownership bar |
| InsiderTimeline | Insider buy/sell activity |
| TreeMap | Proportional area visualization |
| WaterfallChart | Cumulative change waterfall |

## Panel adapter pattern (terminal/panels.js)

SKILL.md documents flat payload shapes (e.g., `{symbol, buy, hold, sell}`).
Components expect specific prop structures (e.g., `{ticker, ratings: {buy, hold, sell}}`).

`panels.js` is the adapter layer that bridges the gap. Each panel case normalizes
the incoming data to match what the component function expects.

`presetToBlocks()` in `panels.js` provides backward compatibility — it converts legacy `layout + panels` payloads into the blocks array format.

## TUI server (terminal/server.js)

- HTTP server on port 7707 (configurable via env)
- State file at `~/.heurist/tui.json` — PID, port, start time
- Actions: `render`, `focus`, `layout`, `clear`
- Progressive rendering: POST partial data as it arrives, panels update incrementally
- Scroll support: keyboard (j/k/↑↓/PgUp/PgDn/g/G) + mouse wheel (SGR mode)
- Block engine: 7 types — panel, table, row, stack, divider, text, spacer

## MCP bridge (bridge/index.js)

Proxies the Heurist Mesh SSE server into Streamable HTTP at localhost:3100.

- `POST /mcp` — Streamable HTTP endpoint (JSON-RPC)
- `GET /sse` — Legacy SSE passthrough
- `GET /health` — Status check

Local resources (served by bridge, not upstream):
- `heurist://skill` — SKILL.md content
- `heurist://tools` — Tool reference table
- `heurist://layouts` — Layout schemas

## Config directory (~/.heurist/)

```
~/.heurist/
├── config.yaml    — User preferences (theme, depth, output_dir, watchlist)
├── tui.json       — TUI state (pid, port, startedAt) — written by terminal/server.js
├── bridge.json    — Bridge state (pid, port, startedAt) — written by bridge/index.js
└── plans/         — Session plans
```

Created on first run. State files use atomic tmp+rename writes, mode 0o600.

## Test coverage

741+ tests across 28 test files. Primarily unit tests for components (snapshot-based)
and integration tests for the TUI server and MCP bridge.

```bash
npm test        # vitest run, ~2s
```
