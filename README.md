# Heurist Finance

Investment research with AI agents, kept in a git repo. Open it in Claude Code, Codex or
Cursor and ask a market question. The agent pulls prices, options, SEC filings, FRED series
and the web through [Heurist Mesh](https://heurist.ai), and answers with a call, the evidence
behind it and what would prove it wrong. When you decide to trade, it writes a plan with price
levels, and a monitor messages you on Telegram when a level is crossed.

For a hosted version, [finance.heurist.ai](https://finance.heurist.ai) is an AI financial
workbench where you read the market feed and research with AI in the browser.

## Quick start

You need Python 3.11+, [uv](https://docs.astral.sh/uv/) and a coding agent.

```bash
git clone https://github.com/heurist-network/heurist-finance
cd heurist-finance
cp .env.example .env        # add HEURIST_API_KEY and EODHD_API_KEY
uv sync
uv run python scripts/hf_tool.py quote NVDA QQQ
claude                      # or codex, cursor
```

Get a Heurist API key at [heurist.ai/credits](https://heurist.ai/credits), or with a referral
code at [dev-api-form.heurist.ai](https://dev-api-form.heurist.ai/). The EODHD key
([eodhd.com](https://eodhd.com)) covers daily bars and quotes.

Then talk to the agent:

```
Interview me and fill in profile.md.
use research skill: are semiconductor earnings revisions still rising?
use trading skill: plan an entry in AMD after its earnings.
use audit skill: <paste a thread or article>
```

Your profile, plans and fills end up in this repo. Keep your copy in a private repository
rather than a public fork.

## Skills

The skills are in `.claude/skills/` (linked from `.agents/skills/` for other agents). The agent
picks one from the question, or you name it with the phrase in the second column. All of them
follow [`_shared/analyst-core.md`](.claude/skills/_shared/analyst-core.md): every number comes
from a tool call, the agent estimates before it reads consensus, and each answer ends with a
call, a falsifier and a horizon.

| Skill | Phrase | Use for |
|---|---|---|
| [hf-research](.claude/skills/hf-research/SKILL.md) | `use research skill` | Parallel research across prices, filings, macro and the web, then a skeptic pass |
| [trading-plan](.claude/skills/trading-plan/SKILL.md) | `use trading skill` | A written plan: scenarios, size, invalidation list, monitor levels |
| [earnings-preview](.claude/skills/earnings-preview/SKILL.md) | `use earnings-preview skill` | Research lanes, bull/bear debate, fact-check and a verdict committed before the print |
| [earnings-play](.claude/skills/earnings-play/SKILL.md) | `use earnings skill` | Implied vs realized move, vol crush, post-earnings drift |
| [entry-exit-timing](.claude/skills/entry-exit-timing/SKILL.md) | `use timing skill` | Limit-price ladders and stops from trend regime and σ bands |
| [position-sizing](.claude/skills/position-sizing/SKILL.md) | `use sizing skill` | Fractional Kelly, volatility targeting, portfolio heat |
| [portfolio-review](.claude/skills/portfolio-review/SKILL.md) | `use portfolio skill` | Correlated clusters, concentration, stress losses in dollars |
| [market-health](.claude/skills/market-health/SKILL.md) | `use market skill` | Breadth, distribution days, volatility and credit, ending in an exposure gate |
| [macro-regime](.claude/skills/macro-regime/SKILL.md) | `use macro skill` | Curve, credit, dollar and inflation turned into positions |
| [sector-rotation](.claude/skills/sector-rotation/SKILL.md) | `use sector skill` | Sector relative strength and rate sensitivity |
| [valuation-expectations](.claude/skills/valuation-expectations/SKILL.md) | `use valuation skill` | What the price already implies, against base rates |
| [fundamental-forensics](.claude/skills/fundamental-forensics/SKILL.md) | `use forensics skill` | Accruals, cash vs earnings, restatement red flags |
| [thesis-audit](.claude/skills/thesis-audit/SKILL.md) | `use audit skill` | Fact-checks someone else's thesis claim by claim |
| [options-strategist](.claude/skills/options-strategist/SKILL.md) | `use options skill` | Strikes, expiry and management rules for a view |
| [momentum-trend](.claude/skills/momentum-trend/SKILL.md) | `use momentum skill` | Momentum and trend, with crash risk |
| [technical-evidence](.claude/skills/technical-evidence/SKILL.md) | `use technicals skill` | Chart signals ranked by statistical support |
| [sentiment-positioning](.claude/skills/sentiment-positioning/SKILL.md) | `use sentiment skill` | Crowding, insider clusters, contrarian signals |
| [event-driven](.claude/skills/event-driven/SKILL.md) | `use event skill` | M&A arb, spinoffs, index changes, lockups, activists |
| [short-thesis](.claude/skills/short-thesis/SKILL.md) | `use short skill` | Short cases with catalyst and squeeze checks |
| [small-cap-scout](.claude/skills/small-cap-scout/SKILL.md) | `use smallcap skill` | Liquidity, spread cost, pump and dilution checks |
| [stock-screener](.claude/skills/stock-screener/SKILL.md) | `use screener skill` | Screens built around a named mispricing |
| [pairs-relative-value](.claude/skills/pairs-relative-value/SKILL.md) | `use pairs skill` | Cointegration, half-life, entry bands |
| [dividend-income](.claude/skills/dividend-income/SKILL.md) | `use dividend skill` | Yield traps and payout coverage |
| [commodity-curve](.claude/skills/commodity-curve/SKILL.md) | `use commodity skill` | Futures curve, roll yield, COT positioning |
| [bond-data](.claude/skills/bond-data/SKILL.md) | `use bond skill` | Corporate bond terms, TRACE prices, spreads |
| [trade-postmortem](.claude/skills/trade-postmortem/SKILL.md) | `use postmortem skill` | Grades closed trades on process, not P&L |

## Market data CLI

Agents and subagents fetch data through one command that prints JSON:

```bash
uv run python scripts/hf_tool.py quote NVDA MU
uv run python scripts/hf_tool.py prices QQQ --period 5y --out px.json
uv run python scripts/hf_tool.py options NVDA --expiry 2026-12-18
uv run python scripts/hf_tool.py fred BAMLH0A0HYM2 T10Y3M
uv run python scripts/hf_tool.py primary NVDA
uv run python scripts/hf_tool.py trials --nct NCT05552755
uv run python scripts/hf_tool.py describe sec xbrl_fact_trends
uv run python scripts/hf_tool.py call sec insider_activity query=NVDA
```

`tools` lists every Mesh tool (`yahoo`, `fred`, `sec`, `exa`) and `describe` shows a tool's
parameters. `primary`, `document`, `trials` and `papers` save each retrieved document under
`logs/primary-sources/` so you can see what changed between reads.

## Plans and alerts

A plan is a Markdown file in `trading/plans/` with its levels in the frontmatter:

```yaml
---
ticker: QQQ
status: active
levels:
  - {id: add-1, when: "price <= 450", action: "buy 30% of target"}
  - {id: stop, when: "close < sma200", action: "exit all on a Friday close"}
  - {id: vix, ticker: "^VIX", when: "close > 30", action: "add the reserve"}
events:
  - {date: 2030-01-15, what: "CPI release"}
---
```

Three scripts run from cron on any always-on machine:

- `scripts/monitor.py` checks every active plan, sends the alert and commits the fired level.
- `scripts/watch.py` hands each file in `trading/watches/` to a Claude agent, for conditions
  that need reading rather than a price, such as "the 8-K with the merger vote date is out".
- `scripts/brief.py preopen|postclose` sends a short brief on what touched your positions and
  writes its notes to `context/`, which every new agent session reads first.

The watch and brief agents need `ANTHROPIC_API_KEY`. Without a Telegram bot token, alerts print
to stdout. [AGENTS.md](AGENTS.md) has the full plan format and an example crontab.

## Layout

```
profile.md              you: constraints, stance, lessons from past trades
trading/plans/          one plan per file
trading/portfolio.md    holdings and cash
trading/trades.md       one row per fill, tied to a plan level or `unplanned`
trading/watches/        conditions checked by an agent
research/               notes, one topic per file
messages/               daily briefs
context/                the brief's notes for the next session
.claude/skills/         skills
scripts/, src/          CLI, monitor, watch, brief
```

## Upgrading from 0.x

Up to 0.10.4 this repo was a Node terminal app (`hf`) with broker connectors. That code is in
the git history at commit `1c77563`.

## License

MIT
