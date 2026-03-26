# Heurist Finance

Agent-driven financial research terminal. A Heurist Mesh marketplace skill that
turns any AI agent into a sell-side research desk with a Bloomberg-style TUI.

## System Shape

```
┌─────────────────────────────────────────────────────────────────────┐
│  AI Agent (Claude Code / Codex / OpenCode)                         │
│  Loads SKILL.md → routes query → calls MCP tools → POSTs to TUI   │
├─────────────────────────────────────────────────────────────────────┤
│  SKILL.md (main)          skills/*/SKILL.md (sub-skills)           │
│  Identity, setup,         analyst, compare, macro, sector,         │
│  routing, render          desk, risk, watch                        │
│  protocol, shapes                                                  │
├─────────────────────────────────────────────────────────────────────┤
│  Heurist Mesh MCP                                                  │
│  https://mesh.heurist.xyz/mcp/heurist-finance                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│  │Yahoo Finance │ │ SEC EDGAR    │ │ FRED Macro   │  + Exa Search  │
│  │Agent         │ │ Agent        │ │ Agent        │                │
│  └──────────────┘ └──────────────┘ └──────────────┘               │
├─────────────────────────────────────────────────────────────────────┤
│  TUI Server (terminal/)          Research Mode (markdown fallback) │
│  localhost:7707                   No TUI required — same analysis  │
│  Receives render POSTs            output as inline markdown        │
│  Full-screen alt-screen                                            │
└─────────────────────────────────────────────────────────────────────┘
```

The agent is the orchestrator. It reads SKILL.md for identity and protocol,
routes to a sub-skill, calls MCP tools for live data, and either POSTs
rendered blocks to the TUI or outputs markdown directly.

## Boundaries

**What this repo contains:**
- Skill instructions that control agent behavior (`SKILL.md`, `skills/*/SKILL.md`)
- TUI server and renderer (`terminal/`)
- Visual components — pure functions that produce ANSI output (`src/components/`)
- Data shape schemas for panel validation (`terminal/schemas/`)
- ANSI primitives, formatters, themes, markdown renderer (`src/`)
- CLI tools (`bin/`)
- Tests (colocated `*.test.js` files, run with `vitest`)

**What this repo does NOT contain:**
- The MCP tools themselves — those live in `heurist-agent-framework/mesh/agents/`
- Agent runtime or LLM — the host agent (Claude Code, Codex, etc.) provides this
- Market data — all data comes from MCP tool responses at runtime

## Sub-skills

The main `SKILL.md` routes queries to one of seven sub-skills. Each sub-skill
defines its own interactive flow, data pipeline, render dispatch, and verdict
rules.

| Sub-skill | Directory | Purpose |
|-----------|-----------|---------|
| `analyst` | `skills/analyst/` | Single-ticker deep dive. Fundamentals, technicals, SEC filings, insiders, macro overlay, options overlay (Deep mode), verdict. |
| `compare` | `skills/compare/` | Head-to-head comparison of 2-5 tickers. Ranked by conviction. |
| `macro` | `skills/macro/` | Macro regime analysis. Inflation, rates, growth, labor, credit, release calendar, commodity futures overlay. |
| `sector` | `skills/sector/` | Sector and thematic landscape. Leaders, laggards, rotation trades. |
| `desk` | `skills/desk/` | Fast market pulse. Indices, macro regime, commodity futures. Under 5 seconds. |
| `risk` | `skills/risk/` | Event and catalyst impact. Priced-in assessment, winners/losers, trade call. |
| `options` | `skills/options/` | Single-ticker options analysis. Chain discovery, OI/volume skew, P/C ratio, max pain, implied move, structure suggestions. |
| `futures` | `skills/futures/` | Futures and commodities dashboard. Energy, metals, rates, index futures with macro overlay and cross-asset signals. |
| `watch` | `skills/watch/` | Persistent watchlist. Movers, status changes, alerts. |

## Directory Layout

```
SKILL.md                    Main skill — identity, routing, render protocol, shapes
skills/
  analyst/SKILL.md          Single-ticker deep dive (options overlay in Deep mode)
  compare/SKILL.md          Multi-ticker comparison
  macro/SKILL.md            Macro regime analysis (commodity futures in Standard+)
  sector/SKILL.md           Sector and thematic analysis
  desk/SKILL.md             Quick market pulse (commodity futures in Market mode)
  risk/SKILL.md             Event-driven analysis
  options/SKILL.md          Single-ticker options chain analysis
  futures/SKILL.md          Futures and commodities dashboard
  watch/SKILL.md            Watchlist dashboard
src/
  components/               17 visual components (pure functions → ANSI strings)
  ansi.js                   ANSI escape primitives (color, cursor, box drawing)
  formatters.js             Number, date, and table formatting
  themes.js                 6 themes (Heurist, Terminal Cyan, Bloomberg, Monochrome, Solarized, Dracula)
  markdown.js               Markdown renderer for Research Mode output
  index.js                  Component registry and public API
terminal/
  app.js                    TUI entry point (full-screen alt-screen)
  server.js                 HTTP server — receives render POSTs from agents
  engine.js                 Layout engine — resolves blocks into positioned panels
  render.js                 Screen renderer — paints panels to terminal
  panels.js                 Panel dispatcher — maps block data to components
  schemas/                  JSON shape validators for each panel type
  state.js                  Session state management
  scroll.js                 Viewport scrolling
  header.js                 Auto-rendered branded header
  cost.js                   Token cost estimation
  io.js                     Terminal I/O (resize, keypress)
bin/
  hf                        Start the TUI (foreground, alt-screen)
  hf-post                   Send a render payload to the TUI server
  hf-chart                  Standalone braille chart renderer
  hf-config                 Read/write ~/.heurist/config.yaml
  check-update.sh           Version check and auto-upgrade
  start.sh / stop.sh        Background TUI management
```

## MCP Tools Available

The agent calls these through the `heurist-finance` MCP server. Tool names
are prefixed `mcp__heurist-finance__<agent>_<tool>`.

**Yahoo Finance Agent** — market data, technicals, fundamentals, derivatives:
`resolve_symbol`, `quote_snapshot`, `price_history`, `technical_snapshot`,
`options_expirations` *(discover available expirations — call before options_chain)*,
`options_chain` *(compact chain snapshot with OI, volume, moneyness filters)*,
`futures_snapshot` *(compact futures quote + recent trend — prefer over quote_snapshot for futures)*,
`news_search`, `market_overview`, `company_fundamentals`, `analyst_snapshot`,
`fund_snapshot`, `equity_screen`

**SEC EDGAR Agent** — regulatory filings, XBRL facts, ownership:
`resolve_company`, `filing_timeline`, `filing_diff`, `xbrl_fact_trends`,
`insider_activity`, `activist_watch`, `institutional_holders`

**FRED Macro Agent** — curated U.S. macro data:
`macro_series_snapshot`, `macro_series_history`, `macro_regime_context`,
`macro_release_calendar`, `macro_release_context`, `macro_vintage_history`

**Exa Search Agent** — web search and digest:
`exa_web_search`

Important: the MCP tool schemas are the source of truth for parameter names.
Sub-skill SKILL.md files show example calls but the agent must use the actual
schema parameters (e.g. `symbols` not `symbol`, `query` not `cik`, `metric`
not `concept`, `limit` not `periods`).

## Key Conventions

- **File-based POST protocol.** Write render payload to `/tmp/hf-render.json`,
  then POST `{"action":"render","file":"/tmp/hf-render.json"}`. The server
  rejects inline blocks with 400. `bin/hf-post` handles this automatically.
- **Progressive rendering.** POST partial layouts after each pipeline phase.
  Use `patch: true` to accumulate blocks without replacing previous ones.
- **Components are pure functions.** `src/components/*.js` — each is
  `(opts) → ANSI string`, matched by data shape, not MCP tool name.
- **Declarative blocks.** Agent POSTs `{ blocks: [...], _state: {...} }`.
  No fixed layouts. The agent controls all composition.
- **Two output modes.** TUI mode (full terminal dashboard) and Research Mode
  (inline markdown). Same data, same personality, same depth.
- **Conviction, not signal.** Verdicts use `conviction` enum:
  `strong_bull | bull | neutral | bear | strong_bear`.
- **Session locking.** POST `/connect` before any render. One agent per session.
- **Brand color: `#C0FF00`.**

## Commands

```bash
bin/hf                    # start the TUI (foreground, alt-screen)
bin/hf-post <file.json>   # send a render payload to the TUI
bin/hf-chart              # standalone braille chart renderer
npm run build             # esbuild bundle → terminal/dist/app.mjs
npm test                  # vitest run (all tests)
```

## Config

- `~/.heurist/config.yaml` — user preferences (theme, first_run flag)
- `~/.heurist/sessions/` — session memory (conviction history per ticker)
- `~/.heurist/watchlist.json` — persistent watchlist
- `~/.heurist/tui.json` — TUI port and state (written by the server)
- `~/.heurist/analytics/` — local request logs (never synced remotely)
- Terminal port: `7707`
- MCP endpoint: `https://mesh.heurist.xyz/mcp/heurist-finance`

## Related Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Main skill instructions — the agent reads this first |
| `SHAPES.md` | Full shape catalog — all 20 panel component specs |
| `ARCHITECTURE.md` | TUI internals — server, engine, renderer |
| `DESIGN.md` | Visual design system — typography, spacing, color |
| `DEV.md` | Developer guide — build, test, debug |
| `CHANGELOG.md` | Version history |
