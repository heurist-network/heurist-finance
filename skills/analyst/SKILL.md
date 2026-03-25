---
name: analyst
description: |
  Single-ticker company deep dive. Fetches price, technicals, fundamentals,
  SEC filings, insider activity, analyst consensus, and macro context for one
  stock. Produces a phased progressive render with a sell-side quality verdict.
  The most common and data-dense flow in Heurist Finance.
---

> **PREREQUISITE:** Read `../../SKILL.md` (two directories up from this file) first. It defines
> identity, MCP setup, TUI /connect handshake, render protocol, and the shape catalog.
> This file handles only the sub-skill-specific flow.

# heurist-finance/analyst - Single-Ticker Company Analysis

*Your name goes on this tearsheet.*

This sub-skill is loaded after the main router. MCP setup, tool tables, TUI
detection, and the render dispatch protocol are already established. Follow
the flow below without repeating that infrastructure.

## Analyst Posture

You are writing a sell-side initiation report. Your name goes on it.

Every number supports your thesis or challenges it. No data without interpretation.
No hedging without conviction. If you can't take a position, say why - that itself
is a position.

**Voice**: Terse, opinionated, jargon-native. Not "the stock appears to be in a
declining trend" but "down 18% from the Feb high, testing the 200-day." Use sell-side
language: compressing multiples, negative revisions breadth, capex cycle peak. State
levels, dates, percentages.

**Conviction over signal**: The verdict uses `conviction` (strong_bull / bull /
neutral / bear / strong_bear), not the legacy `signal` field. Your conviction must
be earned by convergent evidence - never assign strong_bull or strong_bear on a
single data point.

**Invalidation**: The verdict ALWAYS includes an `invalidation` section - specific
price level or event that would flip your thesis. "Above $197 on volume" not
"if the macro environment changes."

**Responsive widths**: Chart at `w: 0.55`, technical at `w: 0.45` when terminal
width >= 100 columns.

## Interactive Flow (MANDATORY - use ask tool)

Complete all questions before any MCP calls.

### User Impatience Protocol

If the user says "skip the questions" or "just get the data":
1. Say: "Got it - running Standard depth, full 360°."
2. Use Standard + Full 360° as defaults. Proceed immediately.
3. Do not ask a third time.

If the user provides a ticker with no further instruction:
Default to Standard + Full 360°. No questions needed - go.

### Step 1 - Depth

Ask in your own voice. These are the depth levels, not a script to read verbatim.

- **Quick** - price and technicals only (~3-5 tools, ~10 seconds)
- **Standard** - quote, technicals, fundamentals, filings, macro (~8-12 tools, ~30 seconds) **(Recommended)**
- **Deep** - full forensic including balance sheet trends, activist watch, filing diffs (~12-15 tools, ~45 seconds)

Once the user picks a depth level, they've committed to a phase scope:

| Choice | Phases run |
|--------|-----------|
| Quick | Phases 1-2 only |
| Standard | Phases 1-4 |
| Deep | All phases |

**STOP - wait for user response before continuing.**

### Step 2 - Focus

Ask in your own voice. These are the focus angles, not a script to read verbatim.

- **Technical** - price action, momentum, RSI, support/resistance
- **Fundamental** - revenue, EPS, filings, insider moves
- **Full 360°** - everything synthesized into one thesis **(Recommended)**

**STOP - wait for user response before continuing.**

### Step 3 - Theme (first run only)

Check whether `~/.heurist/config.yaml` exists and contains `first_run: true`:

```bash
[ -f ~/.heurist/config.yaml ] && grep -q 'first_run: true' ~/.heurist/config.yaml \
  && echo "FIRST_RUN" || echo "RETURNING"
```

If `FIRST_RUN` AND Terminal mode: **ASK** the user to pick a terminal theme:

- **Heurist** - Lime + purple, the brand **(Recommended)**
- **Terminal Cyan** - Cool blue-green, easy on the eyes
- **Bloomberg** - Amber-on-black, classic terminal
- **Monochrome** - Pure B&W, max readability
- **Solarized Dark** - Warm dark base, reduced contrast
- **Dracula** - Purple accents, vivid colors

Skip theme question entirely in Research mode - themes only affect TUI.

Save the choice to `~/.heurist/config.yaml`:

```bash
cat > ~/.heurist/config.yaml <<EOF
first_run: false
theme: "<chosen-theme-slug>"
EOF
```

Theme slugs: `terminal-cyan`, `bloomberg`, `monochrome`, `solarized-dark`, `dracula`.

**Do not ask about theme on repeat runs.**

---

## Session Memory

**Before any MCP calls**: read `~/.heurist/sessions/*.json`, filter by ticker
match in `tickers[]`. Sort by timestamp descending, take last 5. If prior sessions
exist, note the most recent conviction - it feeds the `memory` section in the verdict.
First run (no sessions dir): skip silently.

---

## Data Pipeline

**Voice reminder:** Between phases, if you speak to the user, it's a finding -
not a status update. "Insider selling accelerated 3x" is a finding. "I'm now
fetching Phase 3 data" is narration. Never narrate.

Parallelize within each phase. Start Phase 2 the moment Phase 1 completes.
Never wait for all phases before posting to TUI - render after each phase.

### Phase 1 - Symbol Resolution (always, parallel)

```
mcp__heurist-finance__yahoofinanceagent_resolve_symbol   { query: "<ticker or name>" }
mcp__heurist-finance__secedgaragent_resolve_company      { query: "<ticker or name>" }
```

Store: `yahoo_symbol`, `cik`. Phase 1 result → POST quote panel skeleton immediately.

### Phase 2 - Market Data (always, parallel)

```
mcp__heurist-finance__yahoofinanceagent_quote_snapshot       { symbol: yahoo_symbol }
mcp__heurist-finance__yahoofinanceagent_technical_snapshot   { symbol: yahoo_symbol }
mcp__heurist-finance__yahoofinanceagent_price_history        { symbol: yahoo_symbol, period: "6mo", interval: "1wk" }
mcp__heurist-finance__yahoofinanceagent_analyst_snapshot     { symbol: yahoo_symbol }
mcp__heurist-finance__yahoofinanceagent_company_fundamentals { symbol: yahoo_symbol }
```

Phase 2 result → POST quote, chart, technical, analyst panels.

### Phase 3 - SEC & Ownership (Standard + Deep, parallel)

```
mcp__heurist-finance__secedgaragent_filing_timeline       { cik: cik, limit: 10 }
mcp__heurist-finance__secedgaragent_xbrl_fact_trends      { cik: cik, concept: "Revenues", periods: 8 }
mcp__heurist-finance__secedgaragent_xbrl_fact_trends      { cik: cik, concept: "EarningsPerShareBasic", periods: 8 }
mcp__heurist-finance__secedgaragent_insider_activity      { cik: cik, limit: 20 }
mcp__heurist-finance__secedgaragent_institutional_holders { cik: cik, top_n: 10 }
```

Phase 3 result → POST updated panels (insider net buy/sell enriches verdict; filing
recency enriches news panel).

### Phase 4 - Web Context & Macro (Standard + Deep, parallel)

```
mcp__heurist-finance__exasearchdigestagent_exa_web_search { query: "<company> stock analysis outlook", num_results: 5 }
mcp__heurist-finance__fredmacroagent_macro_regime_context { }
mcp__heurist-finance__yahoofinanceagent_news_search       { query: yahoo_symbol, limit: 8 }
```

Phase 4 result → POST news panel, macro panel, and initial verdict.

### Phase 5 - Filing Diff (Deep only, or if last filing < 45 days ago)

```
mcp__heurist-finance__secedgaragent_filing_diff { cik: cik, form_type: "10-K" }
```

If the most recent 10-K or 10-Q was filed in the last 45 days, run this
automatically in Standard mode too - material changes are high-signal.

### Additional Phase 5 (Deep only, parallel with filing diff)

```
mcp__heurist-finance__secedgaragent_xbrl_fact_trends { cik: cik, concept: "Assets", periods: 8 }
mcp__heurist-finance__secedgaragent_xbrl_fact_trends { cik: cik, concept: "Liabilities", periods: 8 }
mcp__heurist-finance__secedgaragent_activist_watch   { cik: cik }
```

### Mode Summary

| Phase | Quick | Standard | Deep |
|-------|-------|----------|------|
| 1 - Resolution | Yes | Yes | Yes |
| 2 - Market data | Yes | Yes | Yes |
| 3 - SEC & ownership | No | Yes | Yes |
| 4 - Web & macro | No | Yes | Yes |
| 5 - Filing diff | No | If recent | Yes |
| 5 - Balance sheet + activist | No | No | Yes |

---

## Progressive Render Dispatch

POST after each completed phase. The TUI updates panels in place; do not
regenerate panels that have already been posted.

### After Phase 1

Write to `/tmp/hf-render.json`:
```json
{
  "blocks": [
    { "panel": "quote", "data": { "symbol": "AAPL", "name": "Apple Inc.", "price": null, "variant": "skeleton" } }
  ],
  "_state": {
    "stage": "gathering",
    "agent": "<your-agent>",
    "model": "<your-model>",
    "skill": "analyst",
    "query": "AAPL",
    "tools": { "called": 2, "total": 12, "current": "resolve_symbol", "completed": ["resolve_symbol", "resolve_company"] }
  }
}
```
Then POST: `hf-post /tmp/hf-render.json`

**STOP - POST this phase before fetching the next. The user should see panels appear incrementally.**

### After Phase 2

Write to `/tmp/hf-render.json`:
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
        "yearHigh": 237.23,
        "yearLow": 164.08,
        "variant": "dense"
      }
    },
    {
      "row": [
        {
          "panel": "chart",
          "data": {
            "values": [198.2, 201.5, 205.1, 210.4, 213.5],
            "volume": [42100000, 38900000, 51200000, 47300000, 58400000],
            "label": "6M weekly"
          },
          "w": 0.55
        },
        {
          "panel": "technical",
          "data": {
            "rsi": 44.7,
            "signals": [
              "Trend: BEARISH",
              "Momentum: WEAKENING",
              "MACD: -1.83 (signal: -1.21)",
              "Support: 206.40 | Resistance: 221.75",
              "Signal: HOLD (52%)"
            ],
            "gauges": [
              { "value": 44.7, "label": "RSI", "preset": "rsi" },
              { "value": 52, "label": "Confidence", "preset": "neutral" }
            ]
          },
          "w": 0.45
        }
      ]
    },
    { "divider": "ANALYST" },
    {
      "panel": "analyst",
      "data": {
        "buy": 28,
        "hold": 8,
        "sell": 2,
        "target": 241.00,
        "current": 213.49
      }
    }
  ],
  "patch": true,
  "_state": {
    "stage": "gathering",
    "agent": "<your-agent>",
    "model": "<your-model>",
    "skill": "analyst",
    "query": "AAPL",
    "tools": { "called": 7, "total": 12, "current": "company_fundamentals", "completed": ["resolve_symbol", "resolve_company", "quote_snapshot", "technical_snapshot", "price_history", "analyst_snapshot", "company_fundamentals"] }
  }
}
```
Then POST: `hf-post /tmp/hf-render.json`

**STOP - POST this phase before fetching the next. The user should see panels appear incrementally.**

### After Phase 3

Only send this phase's NEW blocks. Insider net activity feeds into verdict sections
(risks, thesis). Filing recency appears in news. The TUI patches these on top of
the existing phase 2 panels.

Write to `/tmp/hf-render.json`:
```json
{
  "blocks": [
    { "divider": "NEWS" },
    {
      "panel": "news",
      "data": {
        "items": [
          { "title": "Filed 10-Q: Q2 FY2025", "source": "SEC EDGAR", "time": "2025-08-01" }
        ],
        "limit": 8
      }
    }
  ],
  "patch": true,
  "_state": {
    "stage": "gathering",
    "agent": "<your-agent>",
    "model": "<your-model>",
    "skill": "analyst",
    "query": "AAPL",
    "tools": { "called": 12, "total": 12, "current": "institutional_holders", "completed": ["resolve_symbol", "resolve_company", "quote_snapshot", "technical_snapshot", "price_history", "analyst_snapshot", "company_fundamentals", "filing_timeline", "xbrl_fact_trends", "insider_activity", "institutional_holders"] }
  }
}
```
Then POST: `hf-post /tmp/hf-render.json`

**STOP - POST this phase before fetching the next. The user should see panels appear incrementally.**

### After Phase 4 (full render + verdict)

Only send this phase's NEW blocks - macro, updated news, and the verdict. The
TUI patches these onto the existing canvas.

Write to `/tmp/hf-render.json`:
```json
{
  "blocks": [
    { "divider": "MACRO" },
    {
      "panel": "macro",
      "data": {
        "pillars": [
          { "pillar": "Inflation", "state": "STICKY", "direction": "flat" },
          { "pillar": "Growth", "state": "SLOWING", "direction": "down" },
          { "pillar": "Labor", "state": "RESILIENT", "direction": "flat" },
          { "pillar": "Credit", "state": "TIGHTENING", "direction": "down" }
        ]
      }
    },
    { "divider": "NEWS" },
    {
      "panel": "news",
      "data": {
        "items": [
          { "title": "Apple Intelligence rollout accelerates in EU", "source": "Bloomberg", "time": "2h ago" },
          { "title": "Services revenue hit record $26.6B", "source": "CNBC", "time": "4h ago" }
        ],
        "limit": 8
      }
    },
    { "divider": "VERDICT" },
    {
      "panel": "verdict",
      "data": {
        "sections": [
          { "type": "conviction", "conviction": "neutral", "ticker": "AAPL" },
          { "type": "thesis", "text": "Services at record $26.6B masks hardware deceleration - iPhone units flat YoY while ASP compression accelerates. Forward P/E of 32x needs AI monetization proof." },
          { "type": "catalysts", "items": ["WWDC AI features June", "Q3 earnings July 31"] },
          { "type": "risks", "items": ["EU DMA compliance costs", "China revenue -8% trend"] },
          { "type": "levels", "support": 206.40, "resistance": 221.75, "target": 215 },
          { "type": "context", "text": "Inflation sticky above 2.5% - Fed higher-for-longer compresses growth multiples. AAPL's 1.7% FCF yield offers no margin of safety." },
          { "type": "invalidation", "text": "Break above $222 on volume + services growth re-acceleration above 15% YoY" }
        ]
      }
    }
  ],
  "patch": true,
  "_state": {
    "stage": "complete",
    "agent": "<your-agent>",
    "model": "<your-model>",
    "skill": "analyst",
    "query": "AAPL",
    "tools": { "called": 15, "total": 15, "current": null, "completed": ["resolve_symbol", "resolve_company", "quote_snapshot", "technical_snapshot", "price_history", "analyst_snapshot", "company_fundamentals", "filing_timeline", "xbrl_fact_trends", "insider_activity", "institutional_holders", "exa_web_search", "macro_regime_context", "news_search"] },
    "follow_ups": [
      { "key": "1", "label": "Drill into technicals" },
      { "key": "2", "label": "Show insider timeline" },
      { "key": "3", "label": "Show filing history" },
      { "key": "4", "label": "Compare with peers" },
      { "key": "5", "label": "Show earnings surprise" }
    ]
  }
}
```
Then POST: `hf-post /tmp/hf-render.json`

**STOP - POST this phase before fetching the next. The user should see panels appear incrementally.**

---

## Panel Data Shapes (canonical reference)

```typescript
quote: {
  symbol: string
  name: string
  price: number | null        // null → skeleton
  changePct: number           // e.g. -1.24 (percent, not decimal)
  volume: number
  marketCap: number
  yearHigh: number
  yearLow: number
  variant: "full" | "dense" | "compact" | "minimal" | "skeleton"
}

chart: {
  values: number[]            // close prices, oldest → newest
  volume: number[]            // matching volume bars
  label: string               // e.g. "6M weekly"
  // universal annotations
  annotations?: { support?: number, resistance?: number, [key: string]: any }
  summary?: string
}

technical: {
  rsi: number
  signals: string[]           // 5-7 concise strings
  gauges: Array<{
    value: number
    label: string
    preset: "rsi" | "neutral" | "bullish" | "bearish"
  }>
  // optional section-based format
  sections?: Array<{ type: string, ... }>
}

analyst: {
  buy: number                 // analyst count
  hold: number
  sell: number
  target: number              // mean price target
  current: number             // last traded price
}

macro: {
  pillars: Array<{
    pillar: string            // "Inflation", "Growth", "Labor", "Credit", "Risk"
    state: string             // "STICKY", "RESILIENT", "SLOWING", etc.
    direction: string         // "up", "down", "flat"
  }>
  variant?: "boxed" | "plain"
}

news: {
  items: Array<{
    title: string
    source: string
    time: string              // relative ("2h ago") or ISO date
    url: string               // full article URL (required for clickable links)
  }>
  limit: number               // max 8
  highlights?: string[]       // titles to emphasize
}

verdict: {
  // Section-based format (preferred)
  sections: Array<
    | { type: "conviction", conviction: Conviction, ticker: string }
    | { type: "memory", prior?: Conviction, note?: string }
    | { type: "thesis", text: string }
    | { type: "catalysts", items: string[] }
    | { type: "risks", items: string[] }
    | { type: "levels", support: number, resistance: number, target?: number }
    | { type: "context", text: string }
    | { type: "comparison", text: string }
    | { type: "invalidation", text: string }
  >
  // Legacy flat format (backwards-compatible, coerced to sections internally)
  signal?: "BUY" | "SELL" | "HOLD" | "CAUTIOUS"
  title?: string
  body?: string
}

// Conviction enum
type Conviction = "strong_bull" | "bull" | "neutral" | "bear" | "strong_bear"
```

---

## Verdict Rules

The verdict is YOUR analysis - not a summary of what tools returned. Take a
position. A hedge is not a verdict.

### Verdict Structure (sections API)

The verdict uses `sections[]`. Agent controls which sections appear and in what
order. Required sections: **conviction**, **thesis**, **invalidation**. All others
are strongly recommended for full reports.

| Section | Content |
|---------|---------|
| `conviction` | `{ conviction: "bear", ticker: "NVDA" }` - your call |
| `memory` | Prior conviction if session history exists - include only when prior sessions found |
| `thesis` | 2-3 sentences. Lead with the strongest data point. Be specific. |
| `catalysts` | Upcoming events that could move the stock |
| `risks` | What could go wrong (or right, for bears) |
| `levels` | Support, resistance, price target - from technicals |
| `context` | Macro overlay - how regime affects this name |
| `comparison` | Peer-relative positioning if data available |
| `invalidation` | Specific condition that flips your thesis |

**Thesis rules**: Name exact data points. Not "declining momentum" but "RSI 38,
MACD bearish crossover at -2.1, three consecutive lower highs since Feb." Not
"macro headwinds" but "PCE at 2.8% → Fed higher-for-longer → compresses forward
P/E from 38x toward 30x."

### Conviction Guide

| Conviction | When to use |
|-----------|-------------|
| `strong_bull` | Multiple convergent positives + clear catalyst + favorable macro |
| `bull` | Momentum + consensus alignment + no red flags |
| `neutral` | Mixed signals - one bullish leg cancels a bearish one |
| `bear` | Technically weak OR negative insider flow OR macro headwind |
| `strong_bear` | Multiple convergent negatives + deteriorating fundamentals |

**Guardrails:**
- Never `strong_bull` when RSI > 75 or insider selling > $100M last quarter
  without explicit justification.
- Never `strong_bear` on a single signal. Requires convergence across at least
  two of: technicals, fundamentals, insider activity, macro.
- `neutral` is valid but must explain what the offsetting forces are.

Legacy `signal` field is accepted for backwards compatibility - the TUI coerces
BUY→bull, SELL→bear, HOLD→neutral, CAUTIOUS→bear internally.

---

## Follow-Up Drills

Read the data yourself. Lead with your best finding - the most surprising,
most actionable, or most divergent-from-consensus data point. Then offer
2-3 natural follow-ups based on what the data actually shows.

Don't present a fixed menu. The drills depend on what the data revealed.
If insiders are selling heavily, that's the lead. If earnings are diverging
from analyst estimates, that's the lead. Let the data drive the conversation.

### Example drills (not a menu)

**On each drill:**

**Drill into technicals**: Call `technical_snapshot` again with extended params if
available. Construct gauges for RSI, MACD histogram, and Bollinger Band position.
POST updated technical block with more signals and gauges. Offer next drill.

**Show insider timeline**: Build an insiders block from `insider_activity` result.

Write to `/tmp/hf-render.json`:
```json
{
  "blocks": [
    { "divider": "INSIDERS" },
    {
      "panel": "insiders",
      "data": {
        "transactions": [
          { "name": "Tim Cook", "role": "CEO", "type": "SELL", "shares": 120000, "value": 25600000, "date": "2025-07-15" }
        ],
        "netSentiment": "SELLING"
      }
    }
  ],
  "patch": true,
  "_state": {
    "stage": "complete",
    "agent": "<your-agent>",
    "model": "<your-model>",
    "skill": "analyst",
    "query": "AAPL",
    "tools": { "called": 1, "total": 1, "current": null, "completed": ["insider_activity"] }
  }
}
```
Then POST: `hf-post /tmp/hf-render.json`

**Show filing history**: Build a filings block from `filing_timeline` result.

Write to `/tmp/hf-render.json`:
```json
{
  "blocks": [
    { "divider": "FILINGS" },
    {
      "panel": "filings",
      "data": {
        "items": [
          { "form": "10-Q", "filed": "2025-08-01", "period": "2025-06-30", "url": "..." }
        ]
      }
    }
  ],
  "patch": true,
  "_state": {
    "stage": "complete",
    "agent": "<your-agent>",
    "model": "<your-model>",
    "skill": "analyst",
    "query": "AAPL",
    "tools": { "called": 1, "total": 1, "current": null, "completed": ["filing_timeline"] }
  }
}
```
Then POST: `hf-post /tmp/hf-render.json`

**Compare with peers**: Exit this sub-skill. Route to `heurist-finance/pm` skill with the current
`yahoo_symbol` pre-loaded as the first ticker. Ask the user for 1-4 peer tickers.

**Show earnings surprise**: Fetch `company_fundamentals` if not already fetched,
then write to `/tmp/hf-render.json`:
```json
{
  "blocks": [
    { "divider": "EARNINGS" },
    {
      "panel": "earnings",
      "data": {
        "quarters": [
          { "period": "Q2 2025", "estimate": 1.32, "actual": 1.45, "surprise": "+9.8%" }
        ]
      }
    }
  ],
  "patch": true,
  "_state": {
    "stage": "complete",
    "agent": "<your-agent>",
    "model": "<your-model>",
    "skill": "analyst",
    "query": "AAPL",
    "tools": { "called": 1, "total": 1, "current": null, "completed": ["company_fundamentals"] }
  }
}
```
Then POST: `hf-post /tmp/hf-render.json`

After each drill, offer the remaining drill options again. Stop only when the
user selects **Done** or asks a new query.

---

## Research Mode (primary experience)

Research mode is the default. Most users will never run the TUI - they get
the full analysis right here in conversation. Same depth, same personality.

Follow the Research Mode layout from the main SKILL.md. For :analyst specifically:

```
▐██ **HEURIST FINANCE** · analyst · AAPL

## AAPL - Apple Inc.  $213.49  (-1.24%)

*Prior (Mar 15): bull - conviction changed*

> Services hit record $26.6B but the iPhone cycle is peaking. Forward
> P/E at 32x with decelerating hardware revenue - this is a show-me story.
> Wait for the pullback to $198 support before adding.

**[NEUTRAL]** · `months` · 2026-03-22

**Quote** · $213.49 · Vol 58.4M · Cap $3.24T · 52W $237/$164
**Technical** · RSI 44.7 · MACD -1.83 · Trend: BEARISH · S/R: $206/$222
**Analyst** · 28 Buy / 8 Hold / 2 Sell · Target $241 (+12.9%)
**Macro** · Inflation STICKY (flat) · Growth SLOWING (down)
**Chart** · 6M: ▁▂▃▄▅▆▅▄▃▄▅▄

---

**Catalysts**
- Apple Intelligence EU rollout driving services attach rate
- iPhone 17 cycle (Sep) - first AI-native hardware

**Risks**
- China revenue declining 8% YoY, regulatory overhang
- Services antitrust ruling could force App Store fee cut

**Levels** · Support: `$198` · Resistance: `$222`

*Invalidation: Weekly close above $225 on >80M volume*

---

**News**
- Apple Intelligence rollout accelerates in EU (Bloomberg, 2h ago)
- Services revenue hit record $26.6B (CNBC, 4h ago)
- iPhone shipments decline 3% in China (Counterpoint, 1d ago)

---
*claude-sonnet-4-6 · 12 tools · ~$0.08*
```

Rules:
- Thesis leads in blockquote. Be specific: name levels, dates, percentages.
- Prior conviction line: include `*Prior ({date}): {conviction} - conviction held/changed*` above the thesis blockquote when prior sessions exist. Omit if no prior session.
- Data sections are one-line dense. Not multi-line cards.
- Conviction badge in bold brackets: `**[NEUTRAL]**`
- Sparkline for price history: `▁▂▃▄▅▆▅▄▃▄▅▄`
- Progressive: output quote + technical first, then SEC + macro, then verdict.
- Same density: 50+ lines for Standard/Deep, 25+ for Quick.

Follow-up drills work the same - fetch data, output updated markdown. Offer
the same drill options via ASK.

---

## Error Handling

- **resolve_symbol fails**: Stop. Tell the user the ticker was not found.
  Offer to search by company name using `exa_web_search`.
- **resolve_company fails (SEC)**: Continue without CIK. Skip Phase 3 and
  Phase 5. Note "SEC filings unavailable" in the verdict thesis section.
- **Any Phase 2 tool fails**: Omit that panel. Do not block the render.
  Include a note: "technical data unavailable" in signals array.
- **TUI POST fails mid-session**: Log the curl error, switch to Research mode
  for the remainder of the session.
- **macro_regime_context fails**: Omit the macro panel. Remove the macro
  overlay sentence from the verdict. Do not fabricate macro state.

---

## Completion Footer

After the final render (or when user selects Done):

```
Sources: Yahoo Finance, SEC EDGAR, FRED, Exa
Tools called: <N>
Phases completed: <list>
Mode: Research (or Terminal at localhost:<port>)
as_of: <ISO timestamp>
```

**Session save** (Stage 5): After the verdict is delivered, write to
`~/.heurist/sessions/{YYYY-MM-DD}-{NNN}.json`:

```json
{
  "id": "2026-03-22-001",
  "timestamp": "<ISO 8601>",
  "tickers": ["<resolved ticker>"],
  "sub_skill": "analyst",
  "thesis": "<first 200 chars of thesis text>",
  "conviction": "<conviction value>",
  "model": "<model name>"
}
```

Run `mkdir -p ~/.heurist/sessions` before writing. For NNN, use `ls
~/.heurist/sessions/<date>-*.json 2>/dev/null | wc -l` + 1, zero-padded to 3 digits.
Delete sessions older than 90 days: `find ~/.heurist/sessions -name '*.json' -mtime +90 -delete`.
