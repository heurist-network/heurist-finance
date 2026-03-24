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
  <img src="docs/screenshots/splash.png" width="720" alt="Heurist Finance - terminal splash screen" />
</p>

---

You already use an AI agent for code. Now it does the research too.

Ask about any stock, sector, or macro regime. Get a conviction note -
thesis, evidence, falsifiers, verdict. The agent gathers the evidence.
You make the call.

<p align="center">
  <img src="docs/screenshots/NVDA.png" width="720" alt="NVDA deep-dive dashboard" />
</p>

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

## See It Work

No terminal needed. Drop `/heurist-finance NVDA` into your agent and get the research inline:

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

Every query produces a position. The assumptions are visible. The evidence
is inspectable. The desk remembers what it said last time - so when conviction
changes, you know.

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
  You                  Heurist Finance               Heurist Mesh
  +---------+          +----------------+             +----------+
  |         |--query-->|  routes to     |--MCP tools->| Yahoo    |
  |         |          |  sub-skill     |  in parallel| FRED     |
  |         |<-panels--|  forms thesis  |<-real data--| SEC      |
  |         |<-verdict-|  renders TUI   |             | Exa      |
  +---------+          +----------------+             +----+-----+
                                                           |
                                                         more
                                                        sources
                                                        coming
```

Heurist Finance is an MCP skill. It installs into Claude Code, Codex CLI,
OpenCode, or any MCP-compatible host. The skill bridges your agent to
[Heurist Mesh](https://mesh.heurist.ai) - a marketplace of MCP tools that
handle the data plumbing.

**Data sources** - fetched in real-time via MCP:

| Source | Coverage |
|--------|----------|
| **Yahoo Finance** | Quotes, price history, technicals, analyst consensus, fundamentals, news |
| **FRED** | CPI, PCE, Fed Funds, GDP, unemployment, macro regime context |
| **SEC EDGAR** | Filings, XBRL financials, insider activity, institutional holders, activist watch |
| **Exa Search** | Web search with LLM digest, URL scraping for deep context |

The agent calls these tools in parallel, normalizes the data into
schema-validated panels, and renders progressively - blocks appear as
data arrives.

## Quick Start

**Requirements:** Node.js 18+

```bash
npx @heurist-network/skills add finance
```

That's it. The agent handles MCP setup on first run.

Open two panes - agent on one side, terminal on the other:

```bash
# Pane 1: the terminal
hf

# Pane 2: your agent
/heurist-finance NVDA
```

The terminal lights up the moment the agent starts fetching. Panels build
as data arrives. This is the intended experience - watching the research
assemble itself while the agent works.

<p align="center">
  <img src="docs/screenshots/connect.png" width="720" alt="Heurist Finance connected to Claude Code" />
</p>

**Terminal** - full-screen dashboard, progressive rendering. Use this when
you want the Bloomberg feel: panels building as data arrives.

**Research** - dense markdown note, delivered inline. Use this when you're
mid-session, want to paste findings elsewhere, or just need the thesis.

Same data, same analysts, same conviction. Different canvas.

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

## Community

Built by [Heurist AI](https://heurist.ai) as a [Heurist Mesh](https://mesh.heurist.ai) marketplace skill.

- Issues and feedback: [GitHub Issues](https://github.com/heurist-network/heurist-finance/issues)
- Heurist community: [Discord](https://discord.gg/heuristai)

## License

MIT - see [LICENSE](LICENSE).
