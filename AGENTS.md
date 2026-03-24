# AGENTS.md — Heurist Finance

Agent-agnostic project config. Works with Claude Code, Codex CLI, OpenCode.

## What This Is

Agent-driven financial terminal — a Heurist Mesh marketplace skill that turns
any AI agent into a sell-side research desk. 7 sub-skills (analyst, pm,
strategist, sector-head, desk, risk, watch) call MCP tools and POST structured
data to a full-screen TUI on port 7707.

## Architecture

```
SKILL.md (intelligence — agent reads this)
    │
    ├── skills/*.md — 7 sub-skill prompts
    │
    ├── bin/ — CLI entry points
    │    ├── hf — start the TUI (always use this)
    │    ├── hf-chart — standalone chart renderer
    │    ├── hf-post — send a POST /render payload
    │    ├── render.sh — shell render helper
    │    ├── start.sh — start TUI in background
    │    ├── stop.sh — stop background TUI
    │    ├── screenshot.js — capture terminal screenshot
    │    └── check-update.sh — check for updates
    │
    ├── bridge/ — SSE→HTTP proxy on port 3100, serves MCP resources
    │
    └── terminal/ — TUI server on port 7707
         ├── server.js — HTTP server, receives POST /render
         ├── app.js — event loop, keyboard input, splash/live phases
         ├── splash.js — branded splash screen (shown until first render)
         ├── render.js — diff-patch renderer, cursor management
         ├── engine.js — free-form block composer (panel, table, row, stack, divider, text, spacer)
         ├── panels.js — maps panel names → component render calls
         ├── scroll.js — scroll state and viewport math
         ├── io.js — raw terminal input, keypress routing
         ├── state.js — shared TUI state (_state.query, _state.skill, etc.)
         ├── cost.js — cost accumulation and formatting
         ├── logo.js — branded logo/wordmark renderer
         ├── version.js — version string export
         ├── header.js — headerBlock() helper (TUI-internal use only)
         └── schemas/ — per-panel validation + coercion
              ├── index.js — validate(name, data) → data | {data, warnings} | null
              ├── verdict.js — thesis/conviction/catalysts/risks schema + warn gates
              └── *.js — quote, chart, technical, macro, news, etc.

src/ — pure component library (17 components)
    ├── components/ — each is (opts) → ANSI string
    ├── ansi.js — color, box-drawing, padding
    ├── themes.js — 6 themes (heurist default)
    └── formatters.js — coloredSignal, trendArrow, etc.
```

## Key Decisions

1. **#C0FF00 IS the brand color.** Not #CDF139. Kevin override.
2. **conviction enum** (strong_bull/bull/neutral/bear/strong_bear) REPLACES signal.
   signal stays as coercion alias in verdict.js for backwards compat.
3. **Heurist theme is install default** — no setup.sh prompt.
4. **Components are MCP-agnostic** — matched by DATA SHAPE, not tool name.
5. **No fixed layouts** — everything through declarative blocks system.
6. **Data-driven composition** — agent composes canvas from data shapes, not templates.
   Never prescribe exact block arrays in SKILL.md.
7. **No grey skeletons** — branded splash until real data arrives.
8. **Dense data-first layouts** — Bloomberg density, not decorative boxes.

## Dev Workflow

```bash
# Start the TUI (foreground, alt-screen)
bin/hf

# NEVER do this:
# node terminal/app.js    ← won't work
# kill the user's hf process ← never

# Test with curl (TUI must be running)
curl -s localhost:7707/render -H 'Content-Type: application/json' -d '{
  "blocks": [
    { "panel": "quote", "data": { "ticker": "AAPL", "price": 150, "changePct": 1.5 } },
    { "panel": "verdict", "data": { "thesis": "Strong thesis here", "conviction": "bull" } }
  ]
}'

# Health check
curl -s localhost:7707/health | jq

# Run tests
npx vitest

# Run specific test file
npx vitest terminal/panels.test.js
```

## Schema Trace

How data flows from agent POST to rendered pixels:

```
POST /render { blocks: [...] }
  → server.js receives JSON
  → for each block: { panel: name, data: {...} }
  → panels.js renderPanel(name, data, width)
    → schemas/index.js validate(name, data) — coercion + warn gates
      → returns data (pass), {data, warnings} (warn), or null (reject)
    → if null → descriptiveFallback()
    → if warnings → render inline ⚠ warnings in dim amber
    → switch(name) → component function from src/components/
    → component returns ANSI string
  → engine.js composes all panel strings into canvas
  → app.js paintScreen() writes to terminal
```

## Schema Gates (v1.1)

Verdict schema has **warn** fields (never hard-block, always render what's available):
- `thesis` — string, min 50 chars
- `conviction` — enum: strong_bull/bull/neutral/bear/strong_bear
- `catalysts` — array, min 1 item
- `risks` — array, min 1 item
- `timeframe` — enum: days/weeks/months/quarters

Missing warn fields → inline `⚠ field missing` in dim amber where the field would render.

## Test Commands

```bash
npx vitest              # all tests (741)
npx vitest --reporter=verbose  # detailed output
npx vitest run          # single run, no watch
```

## Config

- `~/.heurist/` — user config directory
- `~/.heurist/config.yaml` — preferences
- `~/.heurist/sessions/` — agent memory (session records)
- Terminal port: 7707
- Bridge port: 3100 (override with `HEURIST_BRIDGE_PORT`)
