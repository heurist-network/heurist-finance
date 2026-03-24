---
name: watch
description: |
  Dashboard for the user's saved and tracked tickers. Loads a persistent
  watchlist from ~/.heurist/watchlist.json, fetches live quotes and optionally
  deep technicals/analyst data for each ticker, then renders a multi-ticker
  summary on the Ink TUI canvas or as markdown fallback. Supports add/remove,
  quick-status, detailed per-ticker panels, and movers-sorted views.
---

> **PREREQUISITE:** Read `../../SKILL.md` (two directories up from this file) first. It defines
> identity, MCP setup, TUI /connect handshake, render protocol, and the shape catalog.
> This file handles only the sub-skill-specific flow.

# /heurist-finance:watch — Heurist Finance Tracked Tickers Dashboard

*What changed? Flag the movers.*

This sub-skill is loaded by the main `/heurist-finance` router when the user
requests their Heurist Finance watchlist. MCP setup, tool tables, TUI detection, and render
dispatch protocol are already established by the parent SKILL.md — do not
repeat them here.

All MCP tools are prefixed `mcp__heurist-finance__`.

## Watch Posture

Flag what's changed since last check, not just current state. The user doesn't
need to see that AAPL is at $211 — they need to know it dropped 3% since
yesterday on services revenue miss guidance.

For any mover >3%, state whether the move is noise or signal. A 3% drop on
10x average volume after an 8-K filing is signal. A 3% drop on normal volume
in a sector-wide rotation is noise. Name it.

---

## Session Memory

**Before any MCP calls**: read `~/.heurist/sessions/*.json`. Filter by
`tickers[]` overlap with the current watchlist symbols. Sort by timestamp
descending, take last 5. For each ticker with a prior session, note the
conviction change inline ("AAPL was bearish last check, now neutral").
First run (no sessions dir): skip silently.

---

## Step 1 — Load Watchlist

Read `~/.heurist/watchlist.json`.

```bash
cat ~/.heurist/watchlist.json 2>/dev/null || echo '{"tickers":[]}'
```

Expected format:
```json
{ "tickers": ["NVDA", "AAPL", "MSFT", "AMD", "TSLA"] }
```

**If file is missing or `tickers` array is empty:**

ASK the user:
> "Watchlist is empty. What names are you tracking? (comma-separated, e.g. NVDA, AAPL, TSLA)"

Wait for free-text input. Parse the comma-separated list, uppercase each
symbol, deduplicate, then write to file:

```bash
mkdir -p ~/.heurist
cat > ~/.heurist/watchlist.json << 'ENDOFFILE'
{ "tickers": ["NVDA", "AAPL"] }
ENDOFFILE
```

Replace the array with the parsed symbols. Confirm: "Watchlist saved."

---

## Step 2 — Choose View

ASK (use ask tool with options): "How do you want to see this?"

- **Quick status — one line per ticker, sorted by who's moving** *(Recommended)*
- **Detailed — panels with technicals and analyst data per name**
- **Movers only — just the ones that moved, skip the quiet ones**

Wait for answer before fetching any data.

---

## Step 3 — Select Tickers (if > 5)

If the watchlist contains more than 5 tickers, ASK:

- **Show all** — fetch and render every ticker
- **Select subset** — ask user to name the tickers they want (comma-separated)

For "Select subset": wait for input, filter the watchlist to the named symbols,
preserve order from the watchlist.

---

## Data Pipeline

Run phases in order. Parallelize within each phase. POST to TUI after each
phase that produces renderable data (progressive rendering).

### Phase 1 — Symbol Resolution (parallel, all tickers)

For each ticker in the selected list, call `resolve_symbol` in parallel.

```
mcp__heurist-finance__yahoofinanceagent_resolve_symbol(query: "<TICKER>")
```

Collect canonical symbols. If any ticker fails resolution, note it and skip
it from subsequent phases (do not block).

### Phase 2 — Quote Snapshot (parallel, all tickers)

For each resolved symbol, call `quote_snapshot` in parallel. This phase is
the **minimum required** — POST a first render after this phase completes.

```
mcp__heurist-finance__yahoofinanceagent_quote_snapshot(symbol: "<resolved_symbol>")
```

Map result to quote row:
```json
{
  "symbol": result.symbol,
  "name": result.name,
  "price": result.price.last_price,
  "changePct": ((result.price.last_price / result.price.previous_close) - 1) * 100,
  "change": result.price.last_price - result.price.previous_close,
  "volume": result.price.volume,
  "marketCap": result.stats.market_cap,
  "yearHigh": result.stats.year_high,
  "yearLow": result.stats.year_low
}
```

For **Movers Only** view: after Phase 2, filter to tickers where
`|changePct| >= 1.5%` (or all if none qualify). Sort descending by
`|changePct|`. If the filtered list is empty, show a note "No significant
movers today" and offer the full Quick Status instead.

### Phase 3 — Technicals + Analyst (Detailed view only, parallel)

Skip this phase for Quick Status and Movers Only.

For each ticker, call both in parallel:
```
mcp__heurist-finance__yahoofinanceagent_technical_snapshot(symbol: "<resolved_symbol>")
mcp__heurist-finance__yahoofinanceagent_analyst_snapshot(symbol: "<resolved_symbol>")
```

Map technical result:
```json
{
  "rsi": result.indicators.rsi_14,
  "trend": result.states.trend,
  "momentum": result.states.momentum,
  "signal": result.signal.action,
  "confidence": result.signal.confidence,
  "support": result.price.support,
  "resistance": result.price.resistance
}
```

Map analyst result:
```json
{
  "buy": result.ratings.buy,
  "hold": result.ratings.hold,
  "sell": result.ratings.sell,
  "target": result.target_price.mean,
  "current": currentPrice
}
```

### Phase 4 — Macro Regime (shared, always)

Call once regardless of view:
```
mcp__heurist-finance__fredmacroagent_macro_regime_context()
```

Map result to macro panel (same mapping as parent skill). Include as a
shared context bar or footer panel in the TUI layout.

---

## Render Dispatch

### TUI_READY — Ink Canvas

**Quick Status / Movers Only**:

POST a single render using a `table` block — one row per ticker, sorted by
`changePct` descending for Movers, or by `|changePct|` descending for Quick Status.

```json
{
  "action": "render",
  "blocks": [
    { "divider": "WATCHLIST — QUICK STATUS" },
    {
      "table": {
        "headers": ["Symbol", "Name",            "Price",   "Chg %",  "Volume",  "vs 52W"],
        "align":   ["left",   "left",             "right",   "right",  "right",   "right"],
        "rows": [
          {
            "cells": ["NVDA", "NVIDIA",   "$172.70", "+3.2%",  "45.0M",   "18%"],
            "colors": { "3": "green" }
          },
          {
            "cells": ["AAPL", "Apple",    "$211.50", "-0.8%",  "28.3M",   "54%"],
            "colors": { "3": "red" }
          },
          {
            "cells": ["MSFT", "Microsoft","$415.20", "+0.4%",  "18.1M",   "62%"],
            "colors": { "3": "green" }
          }
        ]
      }
    },
    { "spacer": 1 },
    {
      "panel": "macro",
      "data": {
        "pillars": [
          "Inflation: STICKY ↓",
          "Growth: SLOW ↓",
          "Policy: TIGHT →"
        ]
      }
    }
  ]
}
```

`colors` key is the column index (0-based string). Use `"green"` for positive
change %, `"red"` for negative.

**Detailed Dashboard**:

POST a render with one `stack` per ticker (quote + technical + analyst), then
a shared macro footer. Stack ticker columns vertically — no `row` wrapping
(too many tickers to fit side-by-side).

```json
{
  "action": "render",
  "blocks": [
    { "divider": "WATCHLIST — NVDA" },
    {
      "row": [
        { "panel": "quote",     "data": { "symbol": "NVDA", "price": 172.7, "changePct": 3.2, "variant": "compact" }, "w": 0.5 },
        { "panel": "technical", "data": { "rsi": 41.2, "signals": ["BEARISH", "SELL 68%"] }, "w": 0.25 },
        { "panel": "analyst",   "data": { "buy": 55, "hold": 2, "sell": 0, "target": 269, "current": 172.7 }, "w": 0.25 }
      ]
    },
    { "divider": "WATCHLIST — AAPL" },
    {
      "row": [
        { "panel": "quote",     "data": { "symbol": "AAPL", "price": 211.5, "changePct": -0.8, "variant": "compact" }, "w": 0.5 },
        { "panel": "technical", "data": { "rsi": 52.3, "signals": ["NEUTRAL", "HOLD 54%"] }, "w": 0.25 },
        { "panel": "analyst",   "data": { "buy": 28, "hold": 8, "sell": 2, "target": 241, "current": 211.5 }, "w": 0.25 }
      ]
    },
    { "divider": "MACRO" },
    {
      "panel": "macro",
      "data": {
        "pillars": [
          { "pillar": "Inflation", "state": "STICKY",    "direction": "↓" },
          { "pillar": "Growth",    "state": "SLOWING",   "direction": "↓" },
          { "pillar": "Policy",    "state": "TIGHT",     "direction": "→" }
        ]
      }
    }
  ]
}
```

**Progressive rendering**: POST after Phase 2 with table rows only (no
technical/analyst). POST again after Phase 3 with full detailed rows. POST
macro block after Phase 4.

### TUI_DOWN — Markdown Fallback

Render a markdown summary in chat.

**Quick Status / Movers Only** — a compact table:

```
## Watchlist — Quick Status  (as of 2026-03-21 14:32 ET)

| Symbol | Price  | Change %  | Volume    | vs 52W    |
|--------|--------|-----------|-----------|-----------|
| NVDA   | 172.70 | +3.2% ▲   | 45.0M     | █░░░░ 18% |
| AAPL   | 211.50 | -0.8% ▼   | 28.3M     | ███░░ 54% |
...

**Macro**: Inflation STICKY | Growth SLOWING | Policy TIGHT
```

**Detailed Dashboard** — a section per ticker with sub-sections for quote,
technicals, analyst, then a shared macro footer. Follow the parent skill's
markdown formatting conventions (bold headers, tables, bullet signals).

---

## Follow-up Loop

After rendering, ASK:

- **"Add a name to the list"** — prompt for symbol, validate via `resolve_symbol`, append to `~/.heurist/watchlist.json`, re-render
- **"Drop a ticker"** — prompt for symbol (or list for selection), remove from file, re-render
- **"[TICKER]'s interesting — full deep-dive?"** — route to `:analyst` sub-skill for the named ticker
- **"Compare the top movers head-to-head"** — take the top N (≤ 5) tickers by `|changePct|`, route to `:pm`
- **"Refresh — show me what changed"** — re-run Phases 2–4 for the current selection, POST updated render
- **"Done"** — end the watchlist session

### Add ticker flow

1. ASK: "Which ticker to add?"
2. Call `resolve_symbol` to validate.
3. If valid: read current `~/.heurist/watchlist.json`, append symbol (deduplicated), write back.
4. Confirm: "Added [SYMBOL]. Watchlist now has N tickers."
5. Re-render the full watchlist.

### Remove ticker flow

1. ASK: "Which ticker to remove?" (show current list as options)
2. Remove from array, write back to `~/.heurist/watchlist.json`.
3. Confirm: "Removed [SYMBOL]."
4. Re-render remaining tickers.

### Deep dive routing

Pass the ticker directly to the `:analyst` sub-skill. Read
`skills/analyst/SKILL.md` and follow its instructions with the selected
ticker pre-supplied (skip the ticker-ask step).

### Compare top movers routing

Collect the top N tickers (N = min(5, tickers with `|changePct| >= 1.0%`)).
Pass as the comparison set to `:pm`. Read `skills/pm/SKILL.md` and
follow its instructions with the ticker list pre-supplied.

---

## Watchlist File Contract

- Path: `~/.heurist/watchlist.json`
- Schema: `{ "tickers": string[] }` — uppercase symbols, no duplicates, order preserved
- Max tickers: no hard limit, but warn if > 20 ("Large watchlist — consider using Movers Only view")
- Always write atomically: build the new JSON string, write to file in one operation
- Never remove a ticker without explicit user confirmation

---

## Important Rules (watchlist-specific)

1. **Load file first, every time.** Don't cache the watchlist across sessions.
2. **Parallel by default.** All per-ticker MCP calls in Phases 1–3 run in parallel.
3. **Skip failed tickers.** If `resolve_symbol` or `quote_snapshot` fails for a ticker, omit it from the render and note the failure briefly.
4. **Macro is always shared.** Call `macro_regime_context` once, show it once — don't duplicate per ticker.
5. **Never fabricate prices.** Every price, change %, or signal must come from an MCP response.
6. **Phase 2 is the gate.** Do not render until Phase 2 is complete. Phases 3 and 4 augment but do not block the first render.
7. **Movers threshold is advisory.** If the user explicitly asked for Movers Only and nothing qualifies, show the note and offer Quick Status — don't silently switch.

---

## Research Mode

When TUI is not running, output markdown in chat. Same data, same dashboard feel.

```
▐██ **HEURIST FINANCE** · watch · 6 tickers

## Watchlist — 2026-03-22 14:32 ET

> NVDA breaking below 200-day, watch `$165`. AAPL quiet. TSLA vol spike
> on robotaxi timeline — noise until deliveries report.

| Ticker | Price    | Change  | RSI  | Signal   | Alert              |
|--------|----------|---------|------|----------|--------------------|
| NVDA   | $172.93  | -3.5%   | 38.0 | SELL     | Below 200-day MA   |
| AAPL   | $213.49  | +0.8%   | 52.3 | NEUTRAL  | —                  |
| MSFT   | $428.12  | +0.3%   | 55.1 | NEUTRAL  | —                  |
| TSLA   | $178.22  | -2.1%   | 41.8 | SELL     | Vol 2.3x avg       |
| AMZN   | $198.34  | +1.2%   | 58.4 | BUY      | New 52W high       |
| META   | $612.88  | -0.4%   | 48.9 | NEUTRAL  | —                  |

*Prior: NVDA was BULL (Mar 15) — conviction changed*

**Macro** · Inflation STICKY · Growth SLOWING · Policy TIGHT

---
*Claude Opus 4 · 14 tools · ~$0.10*
```

Rules:
- Summary blockquote leads — flag the one or two movers worth watching.
- Table is the primary data display. RSI and Signal columns only for
  Detailed view; omit for Quick Status.
- Alert column: use `—` when nothing notable; name the specific condition
  when it matters (volume, MA crossover, 52W level).
- Prior conviction inline in table footer when session history exists.
- Footer: model · tool count · estimated cost.

---

## Error Handling

- MCP tool returns error → omit that ticker's row, note failure briefly
- Symbol not found → skip ticker, tell user, suggest alternative
- All Phase 2 tools fail → abort with error message, no empty render
- Partial data → render what you have, mark missing columns as `—`
- TUI not responding → fall back to Research mode, continue analysis

---

## Completion

After rendering:
```
Data sources: {list agents used}
Tools called: {count}
Mode: Research (or Terminal at localhost:{port})
```

### Session Save

Write session after each successful analysis:

```bash
mkdir -p ~/.heurist/sessions
```

Session file: `~/.heurist/sessions/{YYYY-MM-DD}-{NNN}.json`
```json
{
  "id": "{date}-{NNN}",
  "timestamp": "{ISO}",
  "tickers": ["{all tickers in watchlist analyzed}"],
  "sub_skill": "watch",
  "thesis": "{first 200 chars of summary blockquote}",
  "conviction": "neutral",
  "model": "{model used}"
}
```

For NNN: `ls ~/.heurist/sessions/<date>-*.json 2>/dev/null | wc -l` + 1,
zero-padded to 3 digits. Delete sessions older than 90 days:
`find ~/.heurist/sessions -name '*.json' -mtime +90 -delete`.
