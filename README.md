# Heurist Finance

Agent-native financial research desk in your terminal.

Turn Claude Code, Codex, OpenCode, or any terminal agent into a sell-side
research desk. Ask about a stock, sector, or macro regime, and get a 
Bloomberg-density dashboard with inspectable evidence.

## What It Does

- **Single-ticker deep dive** — quote, price history, technicals, analyst
  consensus, fundamentals, SEC filings, insider activity, macro context,
  and a conviction verdict.
- **Compare tickers** — 2–5 names side by side, ranked by conviction and
  risk/reward.
- **Macro regime** — inflation, growth, labor, rates, yield curve, and
  market implications.
- **Sector scan** — leaders, laggards, rotation trades, catalysts, risks.
- **Market pulse** — fast read on what matters right now.
- **Event analysis** — earnings, FOMC, product launches, shocks, and
  whether they're priced in.
- **Watchlist** — movers, status changes, and what shifted since the last
  check.

Session memory persists across runs — prior reports, conversation history,
and the last dashboard are saved and restored automatically.

## See It Work

```
You:    /heurist-finance NVDA

Agent:  [fetches quote, price history, analyst ratings, macro context, news — in parallel]
        [renders deep-dive dashboard in your terminal]

        NVDA $124.92 ▼ -2.34%  |  Vol 312M  |  MCap $3.06T
        ▁▂▃▄▃▂▁▂▃▄▅▆▅▄▃▂▁▂▃▄  6M weekly
        ████████████████████████████████████████████████████▓░░ BUY 55 | HOLD 2
        RSI 37.8 — approaching oversold
        Target $169.50 (+36% upside)

        VERDICT: BUY — Oversold at $124 with strong analyst consensus.
        Blackwell Ultra launch catalyst. Accumulate on weakness.

Agent:  RSI is 37 (approaching oversold). Want me to drill deeper?

You:    Compare with AMD

Agent:  [switches to compare layout — side-by-side NVDA vs AMD]
```

One command. Real data. Visual output. Follow-up drills.

## Install

```bash
npx @heurist-network/skills add heurist-finance
```

Or with a specific agent:

```bash
npx @heurist-network/skills add heurist-finance --agent claude
npx @heurist-network/skills add heurist-finance --agent codex
npx @heurist-network/skills add heurist-finance --agent opencode
```

Then run setup:

```bash
cd ~/.agents/skills/heurist-finance && bash setup.sh
```

Setup detects your agent, configures the MCP connection, and asks before writing any config.

**Requirements:** Node.js 18+

## Terminal

Start the interactive terminal:

```bash
bin/hf
```

The terminal opens full-screen with a branded splash on startup. When your
agent runs a query, it takes over the display with a live dashboard.
Ctrl+C exits cleanly.

Keyboard: `j`/`k` or `↑`/`↓` to scroll, `PgUp`/`PgDn` for page jumps,
`g`/`G` for top/bottom. Mouse wheel also works.

## How It Works

```
  Agent               Heurist Finance              Heurist Mesh
  ┌─────┐             ┌─────────────┐              ┌──────────┐
  │ You │──question──▶│ SKILL.md    │──MCP tools──▶│ Yahoo    │
  │     │             │ routes to   │              │ FRED     │
  │     │◀─dashboard──│ sub-skill   │◀─data────────│ SEC      │
  └─────┘             │ renders TUI │              │ Exa      │
                      └─────────────┘              └──────────┘
```

1. You ask a financial question
2. The skill routes to the right sub-skill (deep-dive, compare, macro, etc.)
3. Sub-skill fetches data via Heurist Mesh MCP tools — in parallel
4. Data renders progressively via the block engine — 7 block types compose any layout
5. Agent offers follow-up drills (compare with peers, show insider timeline, etc.)

Bloomberg terminal-like power but without the $30k annual subscription, right in your computer.

## 7 Research Modes

| Mode | Trigger | What you get |
|------|---------|-------------|
| **Deep Dive** | `NVDA`, `Apple` | Single-ticker analysis — quote, chart, technicals, analyst, news, verdict |
| **Compare** | `NVDA vs AMD` | Side-by-side (2-5 tickers) with relative valuation |
| **Macro** | `inflation`, `rates` | Economic regime dashboard — CPI, Fed Funds, GDP, employment |
| **Sector** | `semiconductors`, `AI stocks` | Sector rotation, top movers, thematic analysis |
| **Pulse** | `how's the market` | 3-second broad market snapshot |
| **Event** | `FOMC`, `GTC keynote` | Event/catalyst impact on specific tickers |
| **Watchlist** | `my watchlist` | Track and monitor your saved tickers |

## 25 MCP Tools Across 4 Data Sources

| Source | Tools | Data |
|--------|-------|------|
| **Yahoo Finance** | 10 | Quotes, price history, technicals, analyst ratings, fundamentals, news |
| **FRED** | 6 | CPI, PCE, Fed Funds, GDP, unemployment, macro regime |
| **SEC EDGAR** | 7 | Filings, XBRL financials, insider activity, institutional holders |
| **Exa Search** | 2 | Web search with LLM digest, URL scraping |

## 17 Terminal UI Components

| Component | What it renders |
|-----------|----------------|
| **QuoteHeader** | Ticker, price, change, volume, market cap, 52-week range |
| **BrailleChart** | Sparkline time-series charts using braille characters |
| **CandlestickChart** | OHLC candlestick charts |
| **AnalystBar** | Buy/hold/sell consensus bar with target price |
| **GaugeBar** | Single-value gauge with colored fill and preset thresholds |
| **MacroDashboard** | Multi-pillar macro regime display (inflation, growth, labor, rates) |
| **HeatMap** | N×M color-coded grid for sector/metric comparison |
| **CorrelationMatrix** | N×N pairwise correlation grid |
| **TreeMap** | Proportional area map for market cap, sector weight, etc. |
| **FlowSankey** | Flow diagram for fund flows, sector rotation, capital movement |
| **WaterfallChart** | Sequential gain/loss waterfall |
| **EarningsSurprise** | Quarterly actual vs. estimate with surprise percentage |
| **InsiderTimeline** | Insider buys/sells plotted on a timeline |
| **FilingTimeline** | SEC filing dates and types on a timeline |
| **HolderBar** | Institutional holder bars with percentage and share count |
| **NewsStream** | Headline list with source, time, and clickable links (OSC 8) |
| **Verdict** | Conviction verdict panel — thesis, catalysts, risks, levels, timeframe |

## License

MIT
