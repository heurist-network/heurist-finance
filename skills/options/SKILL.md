---
name: options
description: |
  Single-ticker options analysis sub-skill for the Heurist Finance terminal.
  Discovers expirations, fetches option chains, maps open interest and volume
  skew, overlays spot technicals, and delivers a directional verdict with a
  suggested structure. Uses options_expirations and options_chain from the
  Yahoo Finance agent alongside quote and technical tools for spot context.
---

> **PREREQUISITE:** Read `../../SKILL.md` (two directories up from this file) first. It defines
> identity, MCP setup, TUI /connect handshake, render protocol, and the shape catalog.
> This file handles only the sub-skill-specific flow.

# heurist-finance/options - Single-Ticker Options Analysis

*Show me the chain. Where's the smart money leaning?*

Loaded after the main router. MCP setup, tool tables, TUI detection, and render
protocol are defined in the parent SKILL.md - do not repeat them here.

You are an options strategist. Your job is to read the chain - not just quote
greeks, but interpret what open interest, volume skew, and put/call ratios are
telling you about market positioning. Then connect it to the directional thesis
from spot technicals and deliver an actionable structure.

All MCP tools are prefixed `mcp__heurist-finance__`.

## Options Posture

Options data is positioning data. Every chain tells you three things:
1. **Where is protection concentrated?** (put OI clusters = hedged floors)
2. **Where is speculation concentrated?** (call OI spikes = upside targets)
3. **What move is priced in?** (ATM straddle = expected range)

Don't just render the chain. Read it. "AAPL 200 calls have 45K OI vs 12K at
195 puts - the Street is positioned for a breakout above $200 by April expiry"
is analysis. A table of strikes is Yahoo Finance.

**Bounded**: Options analysis requires spot context. Always fetch the underlying
quote and technicals alongside the chain - never analyze options in a vacuum.

## Entry Behavior

**Default: Standard depth, nearest monthly expiration, both calls and puts. Start fetching immediately once the underlying is confirmed.**

### Underlying confirmation (the only required pause)

If the ticker is clear ("AAPL options"), confirm and proceed. If ambiguous,
resolve via `resolve_symbol` — ask the user only when two plausible securities
share the same root.

**STOP - wait for user response only if the underlying is genuinely ambiguous.**

### Defaults (never ask about these)

- **Scope**: Standard — expiration discovery, one chain with full OI/volume analysis, spot overlay
- **Expiration**: nearest monthly expiration. Honor explicit overrides from query text:
  - "weeklies" / "this week" → nearest weekly
  - "let me pick" / "show me the expirations" → fetch `options_expirations`, present them, ask which one
  - specific date or DTE → use it
- **Sides**: both calls and puts
- **Depth upgrades**: use explicitly stated signals only:
  - "term structure", "skew", "multiple expirations", "deep" → Phase 1-4 (Deep)
  - "quick", "just the chain", "fast" → Phase 1-2 (Quick chain)

| Depth | Phases | When |
|-------|--------|------|
| Quick chain | 1-2 | Explicit "quick" signal |
| Standard | 1-3 | Default |
| Deep | 1-4 | Explicit "deep" / "term structure" / "skew" signal |

---

## Session Memory

**Before any MCP calls**: read `~/.heurist/sessions/*.json`, filter by ticker
match in `tickers[]`. Sort by timestamp descending, take last 5. If prior
sessions exist, note the most recent conviction and whether it was an options
or equity analysis. First run (no sessions dir): skip silently.

---

## Data Pipeline

**Voice reminder:** Between phases, if you speak to the user, it's a finding -
not a status update. "Put OI clustered at $180 - that's the dealer hedge floor"
is a finding. "I'm now fetching the options chain" is narration. Never narrate.

### Phase 1 - Resolution + Spot Context (parallel)

```
mcp__heurist-finance__yahoofinanceagent_resolve_symbol       { query: "<ticker>" }
mcp__heurist-finance__yahoofinanceagent_quote_snapshot       { symbols: [yahoo_symbol] }
mcp__heurist-finance__yahoofinanceagent_technical_snapshot   { symbols: [yahoo_symbol] }
mcp__heurist-finance__yahoofinanceagent_options_expirations  { symbol: yahoo_symbol }
```

Run `resolve_symbol` first, then fire the other three in parallel once the
symbol is confirmed.

Store: `yahoo_symbol`, `spot_price`, `expirations[]`.

POST Phase 1: quote panel (dense variant) + technical panel with spot context.

**STOP - POST this phase before fetching the next.**

### Phase 2 - Primary Chain (parallel where possible)

Select the target expiration based on user preference from Step 3:
- Nearest monthly: pick the first expiration flagged as monthly (or closest
  standard monthly from the expirations list)
- Weeklies: pick the nearest expiration
- Specific date: match to the closest available expiration
- Let me pick: present expirations to user, wait for selection

```
mcp__heurist-finance__yahoofinanceagent_options_chain  {
  symbol: yahoo_symbol,
  expiration: "<selected-YYYY-MM-DD>",
  side: "both",
  moneyness: "all",
  limit_contracts: 15
}
```

From the chain response, extract:
- **Put/call OI ratio**: total put OI / total call OI
- **Max pain**: strike with maximum combined OI (where options expire worthless)
- **Volume hotspots**: strikes with unusually high volume relative to OI (fresh positioning)
- **ATM straddle price**: call bid + put ask at the nearest ATM strike → expected move
- **OI clusters**: strikes where OI is 2x+ the mean → support/resistance proxies

POST Phase 2: options chain table + OI analysis panel.

**STOP - POST this phase before fetching the next.**

### Phase 3 - Enrichment (Standard + Deep, parallel)

```
mcp__heurist-finance__yahoofinanceagent_price_history   { symbols: [yahoo_symbol], period: "3mo", interval: "1d" }
mcp__heurist-finance__yahoofinanceagent_news_search     { query: yahoo_symbol, limit: 5 }
```

The price history provides a chart to overlay key options levels (max pain,
OI clusters) as annotations.

POST Phase 3: chart panel with options level annotations + news panel.

**STOP - POST this phase before fetching the next.**

### Phase 4 - Term Structure (Deep only, parallel)

Fetch 2-3 additional expirations to compare:

```
mcp__heurist-finance__yahoofinanceagent_options_chain  { symbol, expiration: "<second-expiry>", side: "both", moneyness: "atm", limit_contracts: 8 }
mcp__heurist-finance__yahoofinanceagent_options_chain  { symbol, expiration: "<third-expiry>",  side: "both", moneyness: "atm", limit_contracts: 8 }
mcp__heurist-finance__fredmacroagent_macro_regime_context  { }
```

Compare ATM IV across expirations for term structure slope. Rising IV at
further expirations = event risk being priced in. Flat or inverted = near-term
fear dominating.

POST Phase 4: term structure comparison + macro panel + verdict.

### Mode Summary

| Phase | Quick | Standard | Deep |
|-------|-------|----------|------|
| 1 - Resolution + spot | Yes | Yes | Yes |
| 2 - Primary chain | Yes | Yes | Yes |
| 3 - Chart + news | No | Yes | Yes |
| 4 - Term structure + macro | No | No | Yes |

---

## Render Dispatch

### After Phase 1

Write to `/tmp/hf-render.json`, then POST: `hf-post /tmp/hf-render.json`.

```json
{
  "blocks": [
    {
      "panel": "quote",
      "data": {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "price": 213.49,
        "changePct": -1.24,
        "volume": 58430100,
        "marketCap": 3240000000000,
        "variant": "dense"
      }
    },
    {
      "panel": "technical",
      "data": {
        "rsi": 44.7,
        "signals": [
          "Trend: BEARISH",
          "Momentum: WEAKENING",
          "Support: $206 | Resistance: $222",
          "Signal: HOLD (52%)"
        ]
      }
    }
  ],
  "_state": {
    "stage": "gathering",
    "agent": "<your-agent>",
    "model": "<your-model>",
    "skill": "options",
    "query": "AAPL options",
    "tools": { "called": 4, "total": 8, "current": "options_expirations", "completed": ["resolve_symbol", "quote_snapshot", "technical_snapshot", "options_expirations"] }
  }
}
```

### After Phase 2

Write to `/tmp/hf-render.json`, then POST: `hf-post /tmp/hf-render.json`.

```json
{
  "blocks": [
    { "divider": "OPTIONS CHAIN" },
    {
      "table": {
        "headers": ["Strike", "C Bid", "C Ask", "C OI", "C Vol", "P Bid", "P Ask", "P OI", "P Vol"],
        "rows": [
          { "cells": ["200.00", "15.20", "15.50", "28,412", "3,201", "1.85", "2.00", "18,340", "1,102"] },
          { "cells": ["205.00", "11.40", "11.70", "22,150", "2,840", "3.10", "3.30", "24,560", "1,540"] },
          { "cells": ["210.00", "7.90",  "8.20",  "35,200", "5,120", "5.50", "5.80", "31,800", "2,890"] },
          { "cells": ["215.00", "5.10",  "5.40",  "41,300", "6,340", "7.20", "7.50", "19,200", "1,670"] },
          { "cells": ["220.00", "3.00",  "3.30",  "38,700", "4,210", "10.40","10.70","12,400", "980"] },
          { "cells": ["225.00", "1.60",  "1.85",  "22,800", "2,150", "14.10","14.40","8,900",  "540"] }
        ]
      }
    },
    {
      "panel": "gauges",
      "data": {
        "items": [
          { "value": 0.72, "label": "P/C OI Ratio", "preset": "neutral" },
          { "value": 6.4, "label": "Expected Move %", "preset": "percent" },
          { "value": 212, "label": "Max Pain", "preset": "neutral" }
        ]
      }
    }
  ],
  "patch": true,
  "_state": {
    "stage": "gathering",
    "agent": "<your-agent>",
    "model": "<your-model>",
    "skill": "options",
    "query": "AAPL options",
    "tools": { "called": 5, "total": 8, "current": "options_chain", "completed": ["resolve_symbol", "quote_snapshot", "technical_snapshot", "options_expirations", "options_chain"] }
  }
}
```

### After Phase 3

Write to `/tmp/hf-render.json`, then POST: `hf-post /tmp/hf-render.json`.

```json
{
  "blocks": [
    {
      "row": [
        {
          "panel": "chart",
          "data": {
            "values": [198.2, 201.5, 205.1, 210.4, 213.5],
            "label": "3M daily",
            "annotations": { "support": 206, "resistance": 222, "max_pain": 212 },
            "summary": "Max pain at $212 - dealers short gamma above $215"
          },
          "w": 0.55
        },
        {
          "panel": "news",
          "data": {
            "items": [
              { "title": "AAPL weekly options volume surges ahead of earnings", "source": "Bloomberg", "time": "2h ago" }
            ],
            "limit": 5
          },
          "w": 0.45
        }
      ]
    },
    { "divider": "VERDICT" },
    {
      "panel": "verdict",
      "data": {
        "sections": [
          { "type": "conviction", "conviction": "neutral", "ticker": "AAPL" },
          { "type": "thesis", "text": "P/C ratio 0.72 with call OI peaking at $215 - the Street is positioned for a grind higher but not a breakout. ATM straddle prices ±6.4% through Apr expiry. Put OI cluster at $210 is the dealer hedge floor. Spot sitting at $213 between max pain ($212) and call wall ($215) - compressed range until a catalyst forces direction." },
          { "type": "catalysts", "items": ["Earnings May 1 - IV will expand into the event", "WWDC June - AI feature narrative"] },
          { "type": "risks", "items": ["Break below $210 triggers dealer hedging cascade", "Low vol environment can persist - theta decay eats premium"] },
          { "type": "levels", "support": 210, "resistance": 215, "target": 212 },
          { "type": "context", "text": "Structure: sell the $220/$225 call spread if bearish; buy the $210/$200 put spread for downside protection. Premium is cheap with 30-day IV at 22%." },
          { "type": "invalidation", "text": "Break above $220 on volume with call OI expansion - positioning shift from neutral to bullish" }
        ]
      }
    }
  ],
  "patch": true,
  "_state": {
    "stage": "complete",
    "agent": "<your-agent>",
    "model": "<your-model>",
    "skill": "options",
    "query": "AAPL options",
    "tools": { "called": 7, "total": 7, "current": null, "completed": ["resolve_symbol", "quote_snapshot", "technical_snapshot", "options_expirations", "options_chain", "price_history", "news_search"] },
    "follow_ups": [
      { "key": "1", "label": "Show another expiration" },
      { "key": "2", "label": "Deep term structure" },
      { "key": "3", "label": "Full analyst tearsheet" },
      { "key": "4", "label": "Compare with another name" }
    ]
  }
}
```

---

## Verdict Rules

The verdict is your options strategy call. Include:

1. **Positioning read** - What is the chain telling you? P/C ratio, OI skew,
   volume hotspots. Translate raw data into a directional lean.
2. **Expected move** - ATM straddle price as a percentage of spot. Is the market
   pricing in too much or too little movement?
3. **Key levels from options** - Max pain, call wall (highest call OI), put floor
   (highest put OI). These act as magnets and barriers.
4. **Suggested structure** - Name a specific options structure if the data
   supports one (spread, straddle, collar, etc.). Include strikes and rationale.
   If no clean structure exists, say "no edge in the premium - wait for setup."
5. **Catalyst timing** - Does the expiration bracket an event (earnings, FOMC,
   product launch)? IV expansion/contraction implications.

Conviction enum: `strong_bull | bull | neutral | bear | strong_bear`

**Guardrails:**
- Never recommend naked short options without explicit risk callout.
- Always note that options analysis is positioning data, not a guarantee.
- If OI is thin (< 1000 contracts at most strikes), note low liquidity risk.
- Connect options positioning to spot technicals - divergence between the two
  is the highest-signal finding.

---

## Follow-up Drills

After rendering, lead with the most interesting finding from the chain - OI
skew, unusual volume, or a divergence between options positioning and spot
technicals. Then offer data-driven follow-ups.

Common directions:

- Show a different expiration → re-fetch `options_chain` with new date, re-render
- Deep term structure → fetch multiple expirations, compare ATM IV across term
- Full equity analysis → route to `heurist-finance/analyst` with options context pre-loaded
- Compare options on two names → route to `heurist-finance/compare` or fetch chains for both
- Earnings play → if earnings are within DTE, analyze the expected move vs historical surprise

Each follow-up: fetch delta data only → POST updated panels → offer next drill.

---

## Research Mode (primary experience)

Research mode is the default. Most users never run the TUI.

```
▐██ **HEURIST FINANCE** · options · AAPL

## AAPL Options · Apr 18 Expiry · DTE 27

> P/C ratio 0.72 - Street is net long calls with the $215 strike as the
> magnet (41K OI). Put floor at $210 (32K OI) is the dealer hedge line.
> ATM straddle prices ±6.4% ($13.70) - cheap for a name with earnings in
> 6 weeks. Sell the $220/$225 call spread for income, or buy the $210/$200
> put spread for downside protection ahead of May 1 earnings.

**[NEUTRAL]** · `Apr expiry` · 2026-03-22

**Spot** · $213.49 (-1.2%) · RSI 44.7 · Trend: BEARISH · S/R: $206/$222
**Chain** · Apr 18 · DTE 27 · 6 strikes shown · P/C OI: 0.72

| Strike | C Bid/Ask | C OI | C Vol | P Bid/Ask | P OI | P Vol |
|--------|-----------|------|-------|-----------|------|-------|
| **210** | 7.90/8.20 | 35.2K | 5.1K | 5.50/5.80 | **31.8K** | 2.9K |
| **215** | 5.10/5.40 | **41.3K** | 6.3K | 7.20/7.50 | 19.2K | 1.7K |
| 220 | 3.00/3.30 | 38.7K | 4.2K | 10.40/10.70 | 12.4K | 980 |

**Key Levels**
- Max pain: `$212` · Call wall: `$215` (41K OI) · Put floor: `$210` (32K OI)
- ATM straddle: `$13.70` (±6.4%) · 30d IV: 22%

**Structure**
- Bearish: sell $220/$225 call spread · $1.45 credit · max risk $3.55
- Protective: buy $210/$200 put spread · $3.30 debit · max gain $6.70
- Neutral: iron condor $200/$205/$220/$225 · net credit ~$2.50

---

**Catalysts**
- Earnings May 1 - IV will ramp into the event, straddle reprices
- WWDC June - longer-dated calls may see OI buildup

**Risks**
- Low vol environment persists - theta decay dominates
- Break below $210 triggers dealer delta hedging cascade

*Invalidation: Call OI expansion above $220 with spot break above $218 on volume*

---
*claude-sonnet-4-6 · 7 tools · ~$0.05*
```

Rules:
- Thesis leads in blockquote with P/C ratio, key OI levels, and a structure suggestion.
- Chain table shows the most relevant strikes (ATM ± 3-5), not the full dump.
- Bold the highest-OI strikes in the table.
- Key Levels section: max pain, call wall, put floor, ATM straddle, IV.
- Structure section: name 2-3 specific options strategies with strikes and prices.
- Prior conviction: include `*Prior ({date}): {conviction}*` above blockquote when prior session exists.

---

## Error Handling

- `options_expirations` returns no data → ticker may not have listed options.
  Tell user, suggest checking if the symbol is optionable. Route to `:analyst`
  for equity-only analysis.
- `options_chain` returns no contracts → expiration may have been delisted or
  too far out. Try the next nearest expiration automatically.
- Spot tools fail → continue with options data only, but note "spot context
  unavailable" in the verdict.
- TUI not responding → fall back to Research mode.

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
  "tickers": ["{underlying ticker}"],
  "sub_skill": "options",
  "thesis": "{first 200 chars of thesis}",
  "conviction": "{conviction value}",
  "model": "{model used}"
}
```

For NNN: `ls ~/.heurist/sessions/<date>-*.json 2>/dev/null | wc -l` + 1,
zero-padded to 3 digits. Delete sessions older than 90 days:
`find ~/.heurist/sessions -name '*.json' -mtime +90 -delete`.
