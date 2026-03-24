# Heurist Finance

Agent-driven financial terminal — a Heurist Mesh marketplace skill that turns
any AI agent into a sell-side research desk.

## Sub-skills

Invoke via `/heurist-finance` (auto-routes) or directly by name.

| Skill | What it does |
|-------|-------------|
| `:analyst` | Single-ticker deep dive. Fundamentals, technicals, insiders, filings. |
| `:pm` | Compare two or more tickers. Side-by-side risk/reward. |
| `:strategist` | Macro regime analysis. Rates, inflation, growth, positioning. |
| `:sector-head` | Map a whole sector. Leaders, laggards, rotation trades. |
| `:desk` | Quick market pulse. What's moving, what's breaking. |
| `:risk` | Event-driven analysis. Specific catalysts and positioning. |
| `:watch` | Saved tickers and watchlist tracking. |

Sub-skill prompts live in `skills/*/SKILL.md`.

## Commands

```bash
bin/hf                    # start the TUI (foreground, alt-screen)
bin/hf-post <file.json>   # send a render payload to the TUI
bin/hf-chart              # standalone braille chart renderer
npm run build             # esbuild bundle → terminal/dist/app.mjs
npm test                  # run all tests (~740)
npx vitest run            # single run, no watch
```

## Key conventions

- **File-based POST protocol.** Never inline JSON in curl. Write render payload to
  `/tmp/hf-render.json`, then POST `{"action":"render","file":"/tmp/hf-render.json"}`.
  The server rejects inline blocks with 400. `bin/hf-post` handles this automatically.
- **esbuild bundle.** `npm run build` produces `terminal/dist/app.mjs` (162K).
  `bin/hf` runs `node terminal/dist/app.mjs` — no vite-node needed in production.
- **Components are pure functions.** `src/components/*.js` — each is `(opts) → ANSI string`,
  matched by data shape, not MCP tool name.
- **Declarative blocks system.** Agent POSTs `{ blocks: [...], _state: {...} }`.
  No fixed layouts. The agent controls all composition.
- **Progressive rendering.** POST partial layouts after each pipeline phase.
  Use `patch: true` to accumulate blocks, not replace.
- **Session locking.** POST `/connect` before any render. One agent per TUI session.
- **6 themes.** Heurist (default), Terminal Cyan, Bloomberg, Monochrome, Solarized, Dracula.
- **Brand color: `#C0FF00`.**

## Config

- `~/.heurist/` — user config directory
- `~/.heurist/config.yaml` — preferences
- `~/.heurist/sessions/` — agent memory (session records)
- Terminal port: 7707
- Bridge port: 3100 (override with `HEURIST_BRIDGE_PORT`)
