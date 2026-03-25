<h1 align="center">Heurist Finance</h1>

<p align="center">
  <strong>The view that matters.</strong><br>
  Agent-native financial research for your terminal.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Node.js-18%2B-brightgreen" alt="Node.js 18+" />
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License" />
  <img src="https://img.shields.io/badge/version-0.9.12-C0FF00" alt="v0.9.12" />
</p>

<p align="center">
  <video width="720" controls autoplay muted loop playsinline poster="docs/screenshots/NVDA.png">
    <source src="https://misc-files.heurist.xyz/split-demo.mp4" type="video/mp4" />
    <a href="https://misc-files.heurist.xyz/split-demo.mp4">Open the demo video</a>
  </video>
</p>

---

You already use an AI agent for code. Now it does the research too.

Ask about any stock, sector, or macro regime. Get a conviction note -
thesis, evidence, falsifiers, verdict. The agent gathers the evidence.
You make the call.

## Quick Start

**Requirements:** Node.js 18+

```bash
npx @heurist-network/skills add finance
```

Open two panes - agent on one side, terminal on the other:

```bash
# Pane 1: the terminal
hf

# Pane 2: your agent
/heurist-finance NVDA
```

The terminal lights up the moment the agent starts fetching. Panels build
as data arrives.

## The Desk

Every seat takes a position.

| Command | Analyst | What they do |
|---------|---------|-------------|
| `/analyst` | Senior Equity Analyst | Deep-dives, SEC filings, and the view that matters |
| `/pm` | Portfolio Manager | Side-by-side conviction. 2-5 names, one winner |
| `/strategist` | Chief Macro Strategist | Rates, inflation, growth - the regime behind the trade |
| `/sector-head` | Sector Head | Rotations, thematics, and the names moving money |
| `/desk` | Trading Desk | Market pulse. Everything that matters, fast |
| `/risk` | Risk Analyst | Event impact. Catalyst timing. What could go wrong |
| `/watch` | Watchlist Monitor | Your names. Tracked. Alerted. Conviction logged |

Most AI finance tools hedge everything. *"The stock may be experiencing
some downward pressure."* This desk doesn't do that. It says *"falling knife
at RSI 38, wait for $120"* - and if you push back, it defends the call or
updates it with the new evidence.

## What It Feels Like

You type `NVDA`.

The terminal lights up - quote appears first, chart follows, panels keep
growing. By the time you've read the technicals, the SEC filings are in.
Full tearsheet with insider activity, macro overlay, and analyst consensus.

The verdict: *"Falling knife at RSI 38. Wait for $120."*

Not a summary. A position - with the levels, the catalysts, and the specific
conditions that would flip the thesis. Every panel shows its source. Every
number is traceable. If the data contradicts the thesis, the desk says so.

Then: *"Insiders sold $58M last quarter. Want the timeline?"*

You drill in. The desk stays in character. It remembers your last session's
conviction and flags when the view has changed.

<p align="center">
  <img src="docs/screenshots/NVDA.png" width="720" alt="NVDA deep-dive dashboard" />
</p>

## Terminal

```bash
hf
```

| Key | Action |
|-----|--------|
| `j`/`k` or up/down | Scroll |
| `PgUp`/`PgDn` | Page jump |
| `g`/`G` | Top / bottom |
| `Tab` | Next panel |
| `?` | Help overlay |
| `q` | Return to splash / quit |

Or skip the terminal. Drop `/heurist-finance NVDA` into your agent and get the research inline:

```
**[BEAR]** - `months` - 2026-03-24

*Prior (Mar 15): bull at $168 - conviction changed*

> Forward P/E of 38x prices in perfection while insiders sold $58M in Q4.
> Blackwell ramp is priced in. The next surprise is negative.

**CATALYSTS**
- Q4 datacenter revenue print (Jan 28)
- PCE August 29 - if sticky, compresses the multiple further
- China export control escalation - $8B TAM at risk

**RISKS**
- Blackwell production delays
- Hyperscaler capex pullback signals
- Sustained PCE above 2.5% forces Fed higher-for-longer

**LEVELS**
Support $145 - Resistance $197 - Target $160

**INVALIDATION**
Above $197 on volume invalidates the bear case.

---

*claude-sonnet-4-6 - 12 tools - ~$0.08*
```

Same data, same analysts, same conviction - whether you're in the terminal or reading markdown. The terminal adds progressive rendering and the Bloomberg feel. Research mode gives you the thesis right in your conversation.

## Why This Exists

Right now, your pre-trade research looks like this: TradingView for the chart,
Seeking Alpha for the thesis, ChatGPT for a quick read on the quarter, SEC.gov
for the filing you probably won't finish. Four tabs, no integration, no memory.

That ritual is the problem. Heurist Finance collapses it into one command.

The agent pulls real-time data across equities, macro, filings, and news -
in parallel. It normalizes the data, renders it into an inspectable research
artifact, and forms a thesis with explicit assumptions and falsifiers. You
still make the call. The desk just makes sure you're making it with
everything on the table.

Bloomberg costs $32K/year and doesn't talk to your agent. This runs locally
and lives inside your agent stack.

## How It Works

```
                        ┌─────────────────────────────────────────────┐
                        │            Heurist Mesh (MCP)               │
                        │                                             │
  ┌──────────┐          │   ┌──────────┐  ┌──────────┐  ┌──────────┐  │
  │          │  query   │   │  Yahoo   │  │   FRED   │  │   SEC    │  │
  │  Claude  │────────▶ │   │ Finance  │  │  Macro   │  │  EDGAR   │  │
  │  Code    │          │   └────┬─────┘  └────┬─────┘  └────┬─────┘  │
  │  Codex   │          │        │             │             │        │ 
  │ OpenCode │  panels  │   ┌────┴─────────────┴─────────────┴────┐   │
  │          │◀──────── │   │         12-15 tools in parallel     │   │
  └──────────┘  verdict │   └─────────────────────────────────────┘   │
       │                │                                             │
       ▼                │   ┌──────────┐                              │
  ┌──────────┐          │   │   Exa    │                              │
  │   TUI    │          │   │  Search  │                              │
  │ 20 panel │          │   └──────────┘                              │
  │   types  │          └─────────────────────────────────────────────┘
  └──────────┘
```

Heurist Finance is an **MCP skill**. One install, any agent. It connects your
agent to [Heurist Mesh](https://mesh.heurist.ai) - a marketplace of MCP tools
that handle the data plumbing.

| Layer | What it does |
|-------|-------------|
| **Prompt architecture** | 8 SKILL.md files route queries, enforce density contracts, anchor analyst voice |
| **Schema coercion** | Normalizes messy agent output at the render boundary - any model works |
| **Block engine** | Agent composes layouts freely - panels, rows, stacks, tables, gauges |
| **Progressive rendering** | Patch-based streaming - panels build as data arrives, not all at once |

**Data sources** - 25 tools, fetched in real-time via MCP:

| Source | Coverage |
|--------|----------|
| **Yahoo Finance** | Quotes, price history, technicals, analyst consensus, fundamentals, news |
| **FRED** | CPI, PCE, Fed Funds, GDP, unemployment, macro regime context |
| **SEC EDGAR** | Filings, XBRL financials, insider activity, institutional holders, activist watch |
| **Exa Search** | Web search with LLM digest, URL scraping for deep context |

## Community

Built by [Heurist AI](https://heurist.ai) as a [Heurist Mesh](https://mesh.heurist.ai) marketplace skill.

- Issues and feedback: [GitHub Issues](https://github.com/heurist-network/heurist-finance/issues)
- Heurist community: [Discord](https://discord.gg/heuristai)

## License

MIT - see [LICENSE](LICENSE).
