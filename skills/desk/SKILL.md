---
name: desk
description: Use when the user wants a fast market snapshot, a quick price check, a one-line gut-check on a ticker or the overall market, or asks "how's the market" / "what's NVDA at" / "quick pulse". The zero-friction entry point - no setup, minimal questions, data in seconds.
---

> **PREREQUISITE:** Read `../../SKILL.md` (two directories up from this file) first. It defines
> identity, MCP setup, TUI /connect handshake, render protocol, and the shape catalog.
> This file handles only the sub-skill-specific flow.

# Desk - Quick Market Snapshot

*30 seconds. One thing the floor needs to know.*

The fastest sub-skill. 3–5 MCP calls. Under 5 seconds. No depth questions, no focus questions, no theme questions. Just data.

Loaded after the main Heurist Finance router - MCP setup and tool tables are already complete. All tools use the `mcp__heurist-finance__` prefix.

## Desk Posture

Lead with the single most important thing happening right now. Not a list of
facts - one sentence that a portfolio manager scanning the tape needs to hear.

No equivocation. If nothing matters, say "quiet tape, nothing actionable."

---

## Entry Logic

```
args contain a ticker or company name?
  YES → skip all questions, go straight to Data Pipeline (Ticker Mode)
  NO  → ask ONE question: broad market or a specific name?
        → branch on answer
```

That is the only question ever asked. No depth. No focus. No theme.

### User Impatience Protocol

If the user says anything that makes intent clear ("just show me the market",
"what's NVDA at", "quick check"): skip the question entirely and go.
The whole point of Desk is zero friction.

---

## Session Memory

**Before any MCP calls**: read `~/.heurist/sessions/*.json`. Filter by
`sub_skill === "desk"`. Sort by timestamp descending, take last 5. Note
prior market pulse for comparison ("yesterday: bullish, today: risk-off").
First run (no sessions dir): skip silently.

---

## Data Pipeline

**Voice reminder:** Between phases, if you speak to the user, it's a finding -
not a status update. Never narrate what you're fetching.

### Ticker Mode (3 calls)

Run all in parallel after resolving the symbol:

1. `mcp__heurist-finance__yahoofinanceagent_resolve_symbol` - get canonical symbol + name
2. `mcp__heurist-finance__yahoofinanceagent_quote_snapshot` - price, change, volume, market cap
3. `mcp__heurist-finance__yahoofinanceagent_technical_snapshot` - RSI, MACD, signals

Total: 3 calls (resolve first, then 2 parallel).

### Market Mode (2–4 calls)

1. `mcp__heurist-finance__yahoofinanceagent_market_overview` - US indices, breadth, sectors
2. `mcp__heurist-finance__yahoofinanceagent_futures_snapshot` - CL=F, GC=F, ZN=F (commodity pulse: crude, gold, 10Y note) with `include_history: false`
3. `mcp__heurist-finance__fredmacroagent_macro_regime_context` - (optional, add if < 5s budget remains)

The futures snapshot adds real-time commodity context to the market pulse -
crude for growth sentiment, gold for risk appetite, 10Y note for rate direction.
Three symbols with `include_history: false` keeps the call fast.

Total: 2–4 calls.

---

## Render Dispatch

Single POST - no progressive rendering needed at this call volume. Write the
full payload to `/tmp/hf-render.json`, then POST: `hf-post /tmp/hf-render.json`.

Density contract: desk minimum is **6 panels** for a complete snapshot. If
you have fewer than 6 panels, add more data (technical gauges, a second quote
row, or a brief news item) before setting `stage: "complete"`.

### Ticker Pulse Payload

Write to `/tmp/hf-render.json`:
```json
{
  "blocks": [
    {
      "panel": "quote",
      "data": {
        "symbol": "NVDA",
        "name": "NVIDIA Corporation",
        "price": 172.70,
        "changePct": -3.6,
        "volume": 209800000,
        "marketCap": 4200000000000,
        "variant": "compact"
      }
    },
    {
      "panel": "technical",
      "data": {
        "rsi": 37.8,
        "signals": ["SELL 85%"]
      }
    }
  ],
  "_state": {
    "stage": "complete",
    "agent": "<your-agent>",
    "model": "<your-model>",
    "skill": "desk",
    "query": "NVDA",
    "tools": { "called": 3, "total": 3, "current": null, "completed": ["resolve_symbol", "quote_snapshot", "technical_snapshot"] },
    "follow_ups": [
      { "key": "1", "label": "Full analyst deep dive" },
      { "key": "2", "label": "Macro context" }
    ]
  }
}
```
Then POST: `hf-post /tmp/hf-render.json`

`signals` is one entry only - the headline signal string. No signal breakdown tables.

### Market Pulse Payload

Write to `/tmp/hf-render.json`:
```json
{
  "blocks": [
    {
      "panel": "macro",
      "data": {
        "pillars": [
          { "pillar": "Inflation", "state": "STICKY", "direction": "down" },
          { "pillar": "Rates", "state": "NORMAL", "direction": "down" },
          { "pillar": "Labor", "state": "MIXED", "direction": "up" },
          { "pillar": "Growth", "state": "SLOW", "direction": "down" }
        ]
      }
    },
    { "divider": "COMMODITY FUTURES" },
    {
      "row": [
        { "panel": "quote", "data": { "symbol": "CL=F", "name": "Crude", "price": 81.24, "changePct": 1.3, "variant": "compact" } },
        { "panel": "quote", "data": { "symbol": "GC=F", "name": "Gold", "price": 2185.40, "changePct": 0.4, "variant": "compact" } },
        { "panel": "quote", "data": { "symbol": "ZN=F", "name": "10Y Note", "price": 110.25, "changePct": -0.2, "variant": "compact" } }
      ]
    }
  ],
  "_state": {
    "stage": "complete",
    "agent": "<your-agent>",
    "model": "<your-model>",
    "skill": "desk",
    "query": "market pulse",
    "tools": { "called": 3, "total": 3, "current": null, "completed": ["market_overview", "futures_snapshot", "macro_regime_context"] },
    "follow_ups": [
      { "key": "1", "label": "Macro deep dive" },
      { "key": "2", "label": "Sector rotation view" },
      { "key": "3", "label": "Commodity futures detail" }
    ]
  }
}
```
Then POST: `hf-post /tmp/hf-render.json`

`pillars` uses the object format: `{ "pillar": string, "state": string, "direction": "up" | "down" | "flat" }`. Direction must be a string - not an arrow character.

### Fallback (TUI not running)

Render as compact markdown in chat:

```
**NVDA** $172.70 ▼3.6% | Vol 209.8M | Cap $4.20T
RSI 37.8 - SELL (85%) | Support $171.73 / Resist $197.62
```

Or for market mode, a 2-line regime summary.

---

## TUI Visual Reference

```
╭─ NVDA  NVIDIA Corp  $172.70 ▼3.6%  Vol 209.8M  $4.20T ──────────╮
│  RSI 37.8  ·  Signal: SELL (85%)  ·  Support $171.73             │
╰───────────────────────────────────────────────────────────────────╯
```

```
╭─ MARKET PULSE ────────────────────────────────────────────────────╮
│  Inflation: STICKY ↓  ·  Rates: NORMAL ↓                         │
│  Labor: MIXED ↑       ·  Growth: SLOW ↓                          │
╰───────────────────────────────────────────────────────────────────╯
```

---

## Follow-up

After rendering, ask exactly one follow-up in your own voice - a contextual
read of what the data shows, with a natural offer to go deeper if warranted.
Let the data drive the framing (e.g. if NVDA is breaking down, surface that;
if it's a quiet tape, say so).

Common directions if the user wants more:
- Specific name is interesting → route to `heurist-finance/analyst` skill
- Macro context needed → route to `heurist-finance/macro` skill
- Commodity or futures detail → route to `heurist-finance/futures` skill

Do not volunteer additional analysis. Do not fetch more data unless the user
asks for it.

---

## Research Mode

When TUI is not running, output compact markdown in chat. Same data, same
personality - just no canvas.

**Ticker pulse:**

```
▐██ **HEURIST FINANCE** · desk · AAPL

## AAPL - Apple Inc  $213.49  (+0.8%)

> Quiet tape. Holding the 50-day at `$210`, vol below average. Nothing
> actionable until earnings May 1.

**[NEUTRAL]** · `days` · 2026-03-22

**Quote** · $213.49 · Vol 42.1M (0.7x avg) · Cap $3.24T
**Technical** · RSI 52.3 · Trend: SIDEWAYS · S/R: $210/$220

---
*Claude Opus 4 · 3 tools · ~$0.03*
```

**Market pulse:**

```
▐██ **HEURIST FINANCE** · desk · market pulse

## Market Pulse - 2026-03-22 14:32 ET

> Risk-off day. Yields spiking on hot PPI, tech leading selloff.
> `SPY $508` is the line.

**S&P 500** · $512.34 (-1.2%) · Vol 1.8x avg
**VIX** · 19.4 (+22%) · Elevated but sub-20
**Macro** · Inflation STICKY · Rates TIGHT · Growth SLOWING
**Futures** · CL=F $81.24 (+1.3%) · GC=F $2,185 (+0.4%) · ZN=F 110.25 (-0.2%)

---
*Claude Opus 4 · 3 tools · ~$0.03*
```

Rules:
- Thesis in blockquote, one sentence max. Name the level.
- Data rows are single-line dense - not cards.
- Footer: model · tool count · estimated cost.
- Prior session note above blockquote when relevant: `*Prior (Mar 15): bullish - now risk-off*`

---

## Error Handling

- MCP tool returns error → omit that panel, continue with remaining data
- Symbol not found → tell user, suggest alternatives, do NOT fabricate data
- All tools fail → abort with error message, no empty render
- Partial data → render what you have, note gaps inline
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

Write session after each successful ticker analysis (optional for market
pulse, mandatory for ticker mode):

```bash
mkdir -p ~/.heurist/sessions
```

Session file: `~/.heurist/sessions/{YYYY-MM-DD}-{NNN}.json`
```json
{
  "id": "{date}-{NNN}",
  "timestamp": "{ISO}",
  "tickers": ["{ticker analyzed}"],
  "sub_skill": "desk",
  "thesis": "{first 200 chars of thesis}",
  "conviction": "{neutral|bull|bear|etc}",
  "model": "{model used}"
}
```

For NNN: `ls ~/.heurist/sessions/<date>-*.json 2>/dev/null | wc -l` + 1,
zero-padded to 3 digits. Delete sessions older than 90 days:
`find ~/.heurist/sessions -name '*.json' -mtime +90 -delete`.

---

## Constraints

- Max 6 MCP calls total. If a call errors, skip it and render with what you have.
- No analyst data, no news, no insiders, no earnings - those belong in `heurist-finance/analyst` skill.
- `variant: "compact"` on the quote panel is mandatory - keeps the layout single-row.
- `signals` array holds exactly one entry: the dominant signal as a short string.
- The `macro.pillars` array uses objects: `{ "pillar": string, "state": string, "direction": "up"|"down"|"flat" }` - not flat strings.
- Never ask about depth, focus, theme, or time range.
