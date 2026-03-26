---
name: futures
description: |
  Futures and commodities analysis sub-skill for the Heurist Finance terminal.
  Covers energy, metals, grains, rates futures, and equity index futures using
  the futures_snapshot tool from Yahoo Finance alongside FRED macro data. Delivers
  a cross-asset commodity regime read with supply/demand context and trade calls.
---

> **PREREQUISITE:** Read `../../SKILL.md` (two directories up from this file) first. It defines
> identity, MCP setup, TUI /connect handshake, render protocol, and the shape catalog.
> This file handles only the sub-skill-specific flow.

# heurist-finance/futures - Futures & Commodities Analysis

*What's the commodity tape saying that equities aren't?*

Loaded after the main router. MCP setup, tool tables, TUI detection, and render
protocol are defined in the parent SKILL.md - do not repeat them here.

You are a commodities and rates strategist. Your job is to read the futures tape -
spot moves, trend context, macro drivers, and supply/demand catalysts - then
deliver a regime call per commodity complex with actionable positioning.

All MCP tools are prefixed `mcp__heurist-finance__`.

## Futures Posture

Commodities are macro in real-time. Oil tells you about growth expectations. Gold
tells you about real rates and fear. Copper tells you about China. Rates futures
tell you what the bond market thinks the Fed will do regardless of what the Fed
says. Read the tape, connect the dots, name the trade.

**Cross-asset connections**: Never analyze a commodity in isolation. Crude up +
gold up = inflation fear. Crude up + gold down = demand-driven growth. Crude down
+ gold up = risk-off flight to safety. The relationship between commodities is as
important as any single move.

**Supply vs demand**: Every commodity move is either supply-driven or demand-driven.
Supply shocks are sharp and mean-revert. Demand shifts are slow and trend. Name
which one is driving the move - it changes the trade.

## Interactive Flow

Ask in your own voice. The options below are guidance, not a script to read verbatim.

### User Impatience Protocol

If the user says "skip" or provides specific futures symbols (e.g., "CL=F GC=F
quick look"): use sensible defaults and go. Don't force the interactive flow when
intent is clear.

If the user asks for "commodities" or "futures" with no further instruction:
Default to Full Dashboard + Standard depth. No questions - go.

### Step 1 - Focus

**ASK** which complex they want to watch. Options:

- **Full dashboard** - energy, metals, rates, equity indices. The macro tape. **(Recommended)**
- **Energy** - crude (CL=F), natural gas (NG=F), heating oil (HO=F), gasoline (RB=F)
- **Metals** - gold (GC=F), silver (SI=F), copper (HG=F), platinum (PL=F)
- **Rates** - 10Y note (ZN=F), 30Y bond (ZB=F), 2Y note (ZT=F), eurodollar (GE=F)
- **Equity index** - ES=F (S&P), NQ=F (Nasdaq), YM=F (Dow), RTY=F (Russell)
- **Specific symbols** - user names exact futures tickers

**STOP - wait for user response before continuing.**

### Step 2 - Depth

**ASK** how much depth they want. Options:

- **Quick read** - snapshot + trend for selected complex (~3-5 tools, ~10 seconds)
- **Standard** - full complex with macro overlay and news (~6-10 tools, ~20 seconds) **(Recommended)**
- **Deep** - multi-complex cross-asset analysis with regime context (~12-15 tools, ~30 seconds)

| Choice | Phases run |
|--------|-----------|
| Quick read | Phases 1-2 only |
| Standard | Phases 1-3 |
| Deep | All phases |

**STOP - wait for user response before continuing.**

---

## Symbol Registry

Standard futures symbols for each complex:

| Complex | Symbols | Description |
|---------|---------|-------------|
| Energy | `CL=F`, `NG=F`, `HO=F`, `RB=F` | Crude, nat gas, heating oil, gasoline |
| Precious Metals | `GC=F`, `SI=F`, `PL=F` | Gold, silver, platinum |
| Industrial Metals | `HG=F` | Copper |
| Rates | `ZN=F`, `ZB=F`, `ZT=F` | 10Y note, 30Y bond, 2Y note |
| Equity Index | `ES=F`, `NQ=F`, `YM=F`, `RTY=F` | S&P, Nasdaq, Dow, Russell |
| Agriculture | `ZC=F`, `ZS=F`, `ZW=F` | Corn, soybeans, wheat |

Use these exact symbols with `futures_snapshot`. The tool validates that symbols
are actual futures (asset_type = "future").

---

## Session Memory

**Before any MCP calls**: read `~/.heurist/sessions/*.json`, filter by
`sub_skill === "futures"`. Sort by timestamp descending, take last 5. If
prior sessions exist, note the most recent conviction - it feeds the `memory`
section in the verdict. First run (no sessions dir): skip silently.

---

## Data Pipeline

**Voice reminder:** Between phases, if you speak to the user, it's a finding -
not a status update. "Crude back above $80 with nat gas lagging - demand-driven,
not supply shock" is a finding. Never narrate.

### Phase 1 - Futures Snapshots (parallel)

Batch all symbols for the selected complex into one or two `futures_snapshot`
calls (max 10 symbols per call):

```
mcp__heurist-finance__yahoofinanceagent_futures_snapshot  {
  symbols: ["CL=F", "NG=F", "GC=F", "SI=F", "HG=F", "ZN=F"],
  include_history: true,
  interval: "1d",
  period: "1mo",
  limit_bars: 10
}
```

For Full Dashboard, split into two calls if > 10 symbols.

POST Phase 1: quote panels for each future + trend charts.

**STOP - POST this phase before fetching the next.**

### Phase 2 - Extended History (parallel per symbol group)

Fetch longer history for the primary symbols in each complex to render trend
charts and compute momentum:

```
mcp__heurist-finance__yahoofinanceagent_price_history  {
  symbols: ["CL=F", "GC=F", "HG=F"],
  period: "6mo",
  interval: "1wk"
}
```

POST Phase 2: chart panels with 6M trend context.

**STOP - POST this phase before fetching the next.**

### Phase 3 - Macro Overlay + News (Standard + Deep, parallel)

```
mcp__heurist-finance__fredmacroagent_macro_regime_context     { }
mcp__heurist-finance__exasearchdigestagent_exa_web_search     { query: "commodity futures outlook oil gold rates [current month]", num_results: 5 }
mcp__heurist-finance__yahoofinanceagent_news_search           { query: "commodities oil gold", limit: 5 }
```

POST Phase 3: macro panel + news panel + verdict.

**STOP - POST this phase before fetching the next.**

### Phase 4 - Cross-Asset Deep Dive (Deep only, parallel)

Fetch additional series for cross-asset context:

```
mcp__heurist-finance__fredmacroagent_macro_series_history  { series_key: "ust_10y", periods: 24, view: "level" }
mcp__heurist-finance__fredmacroagent_macro_series_history  { series_key: "headline_cpi", periods: 12, view: "yoy" }
mcp__heurist-finance__yahoofinanceagent_quote_snapshot     { symbols: ["DXY=F", "TLT", "GLD", "USO"] }
mcp__heurist-finance__yahoofinanceagent_technical_snapshot { symbols: ["CL=F", "GC=F", "HG=F", "ZN=F"] }
```

DXY (dollar index) is critical context - commodities are priced in dollars.
Dollar up = commodity headwind. Dollar down = commodity tailwind.

POST Phase 4: updated charts with cross-asset context + enhanced verdict.

### Mode Summary

| Phase | Quick | Standard | Deep |
|-------|-------|----------|------|
| 1 - Snapshots | Yes | Yes | Yes |
| 2 - Extended history | Yes | Yes | Yes |
| 3 - Macro + news | No | Yes | Yes |
| 4 - Cross-asset deep | No | No | Yes |

---

## Render Dispatch

### After Phase 1

Write to `/tmp/hf-render.json`, then POST: `hf-post /tmp/hf-render.json`.

```json
{
  "blocks": [
    {
      "row": [
        {
          "panel": "quote",
          "data": {
            "symbol": "CL=F",
            "name": "Crude Oil",
            "price": 81.24,
            "changePct": 1.3,
            "volume": 342000,
            "variant": "compact"
          }
        },
        {
          "panel": "quote",
          "data": {
            "symbol": "GC=F",
            "name": "Gold",
            "price": 2185.40,
            "changePct": 0.4,
            "volume": 189000,
            "variant": "compact"
          }
        },
        {
          "panel": "quote",
          "data": {
            "symbol": "HG=F",
            "name": "Copper",
            "price": 4.12,
            "changePct": -0.6,
            "volume": 78000,
            "variant": "compact"
          }
        }
      ]
    },
    {
      "row": [
        {
          "panel": "quote",
          "data": {
            "symbol": "ZN=F",
            "name": "10Y Note",
            "price": 110.25,
            "changePct": -0.2,
            "volume": 1240000,
            "variant": "compact"
          }
        },
        {
          "panel": "quote",
          "data": {
            "symbol": "NG=F",
            "name": "Natural Gas",
            "price": 2.84,
            "changePct": -2.1,
            "volume": 156000,
            "variant": "compact"
          }
        },
        {
          "panel": "quote",
          "data": {
            "symbol": "SI=F",
            "name": "Silver",
            "price": 24.82,
            "changePct": 0.8,
            "volume": 92000,
            "variant": "compact"
          }
        }
      ]
    }
  ],
  "_state": {
    "stage": "gathering",
    "agent": "<your-agent>",
    "model": "<your-model>",
    "skill": "futures",
    "query": "commodity futures",
    "tools": { "called": 1, "total": 8, "current": "futures_snapshot", "completed": ["futures_snapshot"] }
  }
}
```

### After Phase 2

Write to `/tmp/hf-render.json`, then POST: `hf-post /tmp/hf-render.json`.

```json
{
  "blocks": [
    { "divider": "ENERGY" },
    {
      "row": [
        { "panel": "chart", "data": { "values": [72.1, 74.5, 76.8, 79.2, 81.2], "label": "CL=F Crude 6M wk", "summary": "Up 12.6% from Oct low - demand-driven" }, "w": 0.5 },
        { "panel": "chart", "data": { "values": [3.20, 2.95, 2.70, 2.84], "label": "NG=F Nat Gas 6M wk", "summary": "Mild winter bounce fading" }, "w": 0.5 }
      ]
    },
    { "divider": "METALS" },
    {
      "row": [
        { "panel": "chart", "data": { "values": [1980, 2050, 2100, 2150, 2185], "label": "GC=F Gold 6M wk", "summary": "All-time high breakout - real rates driver" }, "w": 0.5 },
        { "panel": "chart", "data": { "values": [3.65, 3.78, 3.92, 4.05, 4.12], "label": "HG=F Copper 6M wk", "summary": "China PMI recovery bid" }, "w": 0.5 }
      ]
    }
  ],
  "patch": true,
  "_state": {
    "stage": "gathering",
    "agent": "<your-agent>",
    "model": "<your-model>",
    "skill": "futures",
    "query": "commodity futures",
    "tools": { "called": 3, "total": 8, "current": "price_history", "completed": ["futures_snapshot", "price_history"] }
  }
}
```

### After Phase 3 (Standard) or Phase 4 (Deep)

Write to `/tmp/hf-render.json`, then POST: `hf-post /tmp/hf-render.json`.

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
          { "pillar": "Rates", "state": "RESTRICTIVE", "direction": "flat" }
        ]
      }
    },
    { "divider": "NEWS" },
    {
      "panel": "news",
      "data": {
        "items": [
          { "title": "OPEC+ extends production cuts through Q3", "source": "Reuters", "time": "4h ago" },
          { "title": "Gold hits record on central bank buying", "source": "Bloomberg", "time": "1d ago" }
        ],
        "limit": 5
      }
    },
    { "divider": "VERDICT" },
    {
      "panel": "verdict",
      "data": {
        "sections": [
          { "type": "conviction", "conviction": "bull", "ticker": "COMMODITIES", "note": "Selective - energy and gold, not base metals" },
          { "type": "thesis", "text": "Commodity complex is splitting: energy and precious metals trending higher on OPEC+ discipline and real-rate expectations, while base metals (copper -0.6%) lag on China uncertainty. Crude above $80 with OPEC+ cuts extended = supply-driven floor. Gold at ATH on central bank buying + falling real yields. Nat gas is the outlier - mild winter inventory overhang keeps it capped below $3." },
          { "type": "catalysts", "items": ["OPEC+ meeting June - production cut extension/rollback", "Fed June dot plot - gold pivots on rate path", "China PMI next print - copper catalyst"] },
          { "type": "risks", "items": ["Dollar rally (DXY > 105) compresses all commodities", "Demand destruction if growth slows faster than expected", "Geopolitical de-escalation removes risk premium from oil"] },
          { "type": "invalidation", "text": "Crude below $75 on demand destruction signals - shifts thesis from bull to neutral. Gold below $2100 on hawkish Fed repricing." }
        ]
      }
    }
  ],
  "patch": true,
  "_state": {
    "stage": "complete",
    "agent": "<your-agent>",
    "model": "<your-model>",
    "skill": "futures",
    "query": "commodity futures",
    "tools": { "called": 8, "total": 8, "current": null, "completed": ["futures_snapshot", "price_history", "macro_regime_context", "exa_web_search", "news_search"] },
    "follow_ups": [
      { "key": "1", "label": "Energy deep dive" },
      { "key": "2", "label": "Gold vs real rates" },
      { "key": "3", "label": "Macro regime detail" },
      { "key": "4", "label": "Rate-sensitive equity names" }
    ]
  }
}
```

---

## Verdict Rules

The verdict covers the commodity regime, not a single instrument. Include:

1. **Regime call** - Is the commodity complex in inflation-hedge mode, growth-demand
   mode, risk-off mode, or diverging? Name the dominant driver.
2. **Complex-level reads** - One sentence per complex (energy, metals, rates) with
   the directional call and the reasoning.
3. **Cross-asset signal** - What do commodities tell you about equities and rates?
   "Oil up + copper up = reflation trade on → overweight cyclicals." Connect it.
4. **Dollar context** - DXY direction affects all dollar-denominated commodities.
   Note whether the dollar is a tailwind or headwind.
5. **Supply vs demand** - For each complex, state whether the move is supply-driven
   (OPEC cuts, weather, geopolitics) or demand-driven (growth, China, inventory).

Conviction enum: `strong_bull | bull | neutral | bear | strong_bear`

Apply conviction to the overall commodity regime, then specify per-complex leans
in the thesis text.

---

## Follow-up Drills

After rendering, lead with the most interesting cross-asset signal. Then offer
data-driven follow-ups.

Common directions:

- Energy deep dive → re-fetch with full energy complex, add technicals per symbol
- Gold vs real rates → fetch TIPS yields, DXY, overlay on gold chart
- Rate futures deep dive → fetch full rates complex, add FRED rate data
- Equity impact → route to `heurist-finance/sector` with commodity context
- Macro regime → route to `heurist-finance/macro` with commodity data pre-loaded
- Specific futures name → route to a focused single-symbol analysis

Each follow-up: fetch delta data only → POST updated panels → offer next drill.

---

## Research Mode (primary experience)

Research mode is the default. Most users never run the TUI.

```
▐██ **HEURIST FINANCE** · futures · commodity dashboard

## Commodity Futures - Selective Bull: Energy + Gold Leading

> Commodity complex is splitting. Crude above $80 on OPEC+ discipline -
> supply-driven floor, not demand pull. Gold at ATH on central bank buying
> and falling real yields. Copper and base metals lag on China uncertainty.
> Nat gas stuck below $3 on inventory overhang. Own energy and gold, wait
> on industrials.

**[BULL]** · `selective` · 2026-03-22

**Energy**
- CL=F Crude · $81.24 (+1.3%) · 6M: +12.6% · Supply-driven (OPEC+ cuts)
- NG=F Nat Gas · $2.84 (-2.1%) · 6M: -11% · Inventory overhang

**Metals**
- GC=F Gold · $2,185 (+0.4%) · 6M: +10.3% · ATH · Central bank buying
- SI=F Silver · $24.82 (+0.8%) · 6M: +8.1% · Following gold, industrial lag
- HG=F Copper · $4.12 (-0.6%) · 6M: +12.8% · China PMI dependent

**Rates**
- ZN=F 10Y Note · 110.25 (-0.2%) · Yields rising on sticky inflation
- ZB=F 30Y Bond · 119.50 (-0.3%) · Long end under pressure

**Macro** · Inflation STICKY · Growth SLOWING · Rates RESTRICTIVE
**Dollar** · DXY 104.2 - neutral, not a headwind yet

---

**Cross-Asset Signal**
Oil up + gold up + copper flat = inflation-hedge bid, not growth optimism.
Equity implication: favor energy producers (XLE) and miners (GDX) over
industrials and transports.

**Catalysts**
- OPEC+ June meeting - cut extension vs rollback
- Fed dot plot June - gold pivots on rate path
- China PMI - copper breakout or breakdown

**Risks**
- DXY > 105 compresses all commodities
- Demand destruction if growth rolls over
- Geopolitical de-escalation removes oil risk premium

*Invalidation: CL=F below $75 + GC=F below $2100 = regime shift to bear*

---
*claude-sonnet-4-6 · 8 tools · ~$0.06*
```

Rules:
- Thesis leads in blockquote with the regime call and specific levels.
- Organize by complex: Energy, Metals, Rates, with one-line dense per symbol.
- Cross-Asset Signal section is mandatory - connect commodities to equities.
- Dollar context in the data section.
- Prior conviction: include `*Prior ({date}): {conviction}*` above blockquote when prior session exists.

---

## Error Handling

- `futures_snapshot` returns "unsupported_asset_type" → symbol is not a future.
  Tell the user and suggest the correct futures symbol (e.g., "GLD is an ETF,
  use GC=F for gold futures").
- No data for a symbol → omit it, continue with remaining symbols, note in verdict.
- Macro tools fail → continue without macro overlay, note in verdict.
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
  "tickers": ["{futures symbols analyzed}"],
  "sub_skill": "futures",
  "thesis": "{first 200 chars of thesis}",
  "conviction": "{conviction value}",
  "model": "{model used}"
}
```

For NNN: `ls ~/.heurist/sessions/<date>-*.json 2>/dev/null | wc -l` + 1,
zero-padded to 3 digits. Delete sessions older than 90 days:
`find ~/.heurist/sessions -name '*.json' -mtime +90 -delete`.
