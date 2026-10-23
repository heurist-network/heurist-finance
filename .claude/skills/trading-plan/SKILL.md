---
name: trading-plan
description: "Turn a trade idea into a data-grounded decision and a written one-page trading plan: pulls live prices/options/fundamentals via scripts/hf_tool.py, builds scenario tables with probabilities, checks the trade against the user's own market view and psychology guardrails, and writes the plan to trading/plans/. Use when asked to plan a trade, evaluate an entry/exit, analyze an options trade (sell puts, covered calls, spreads), size a position, or when the user is stressed about an open position and asking whether to exit. Trigger phrase: `use trading skill`."
---

# Trading Plan

## Overview

Companion to `hf-research`: that skill answers *"what's true?"* — this one answers *"what do I do, at what size, and what would change my mind?"* Two outputs, proportional to the ask:

1. **Decision-ready analysis** — live data, scenario table, a directional call with its falsifier.
2. **A written plan** (only when actually entering/sizing a position) — saved to `trading/plans/YYYY-MM-DD-<slug>.md`.

Read `profile.md` (repo root) before planning: it holds the user's stance, no-go list, and known failure modes (for example: emotional exits mid-trade, drifting from the plan). Every plan this skill produces must be executable by the user's *worst* self, not just their best self. [field-card.md](field-card.md) is the psychology reference — treat it as part of this skill.

## Data layer

Same CLI as hf-research: `scripts/hf_tool.py` from repo root, JSON to stdout, `describe` before `call`. Most-used for trading:

| Need | Command |
|---|---|
| Spot + day range + 50/200-day | `hf_tool.py call yahoo quote_snapshot symbol=SYM` |
| Option expirations (discovery) | `hf_tool.py call yahoo options_chain symbol=SYM` (no expiration; list truncates at 12 — LEAPs exist even if not shown, try the 3rd-Friday date directly) |
| Option chain slice | `hf_tool.py call yahoo options_chain symbol=SYM expiration=YYYY-MM-DD side=puts moneyness=otm min_strike=A max_strike=B limit_contracts=40` |
| IV term structure | loop `options_chain` over expirations with `moneyness=atm limit_contracts=6`, read ATM IV per expiry |
| Trend/momentum/vol state | `hf_tool.py call yahoo technical_snapshot symbol=SYM` |
| Valuation, analyst estimates, EPS revisions, earnings date | `hf_tool.py call yahoo equity_overview symbol=SYM` |
| Cycle evidence (margins, inventory, capex) | `hf_tool.py call sec xbrl_fact_trends query=SYM metric="gross profit" frequency=quarterly limit=12` (plain-English match can grab stale concepts — prefer exact XBRL names like `PaymentsToAcquirePropertyPlantAndEquipment`; dedupe restatement rows by period-end) |
| History for backtests | `hf_tool.py prices SYM --period 5y --out FILE` |

Options math conventions (compute from **bid** — conservative, that's the fill you're guaranteed):

- premium/contract = bid × 100; yield on collateral = bid / strike; annualized ≈ yield × 365/DTE
- breakeven = strike − bid (short put); cushion = (spot − breakeven) / spot
- Always report IV, OI, volume, and bid–ask spread per strike. Prefer liquid round strikes over odd strikes with better headline yield — the fill and the exit eat the difference.

For a genuinely multi-source thesis (cycle calls, macro turns), fan out research lanes per the hf-research recipe first; this skill consumes those findings.

## Analysis requirements

Never give options advice from a single quote. Minimum bar:

- **IV level AND term structure.** The level says what you're paid; the slope (backwardation/contango, event humps) says whether the market expects vol to fall — a tailwind for sellers — and flags earnings inside the contract's life.
- **Scenario table, 3–5 rows.** Each: named scenario, probability (judgmental is fine — say so), price band at the relevant horizon, and *what the position does there*. Sum the rows into odds of profit/loss/assignment.
- **Coherence test.** For every leg, ask: *in the scenario where this leg executes, is the user holding something they wanted at that moment?* A secular bull selling only puts is short their own right tail; an income seller who'd hate assignment is short their own timing. Flag these conflicts explicitly — including conflicts with views the user stated in conversation (e.g. selling puts today while predicting a 15% dip next month → scale in, don't sell full size).
- **Cyclicals: separate the three peaks.** Price-*momentum* peak → absolute-*price* peak → *profit* peak arrive in that order, quarters apart, and the stock leads fundamentals by ~2 quarters. Never let "earnings are still growing" stand in for "the stock won't fall." For price-levered names, run the EPS sensitivity (revenue ≈ P×Q against a near-fixed cost base) — show what a 30% ASP giveback does to consensus EPS.
- **Name the falsifier.** Every recommendation ends with what evidence would change it. No falsifier → not a recommendation, just a mood.

## The plan document

Write one only when the user is entering or sizing a real position. Required fields (this is the pre-flight from the field card, made concrete):

1. **Thesis** — one sentence. Can't write it → don't trade it.
2. **The clock** — the timeframe the thesis lives on; the only timeframe on which the position may be checked.
3. **Entry / exits** — price levels, or for options: strike, expiry, premium collected, breakeven.
4. **Invalidation list** — *specific* news that kills the thesis (signal) vs. pre-declared noise (wars, Fed noise, red tape) that the stop/cushion already prices. This list is what the user reads instead of panicking.
5. **Size + the 11pm test** — position size such that a scary headline at 11pm doesn't compel checking. State the collateral/assignment obligation in dollars.
6. **The pre-fought bad day** — one paragraph: what the worst mid-life mark plausibly looks like (for short options: the vol-spike paper drawdown, with a dollar estimate) and the pre-committed response (nothing, unless the invalidation list fired).
7. **Scenario table** — from the analysis, with per-scenario P&L.
8. **Calendar** — earnings dates, macro events, expiry; the checking cadence.

The file starts with a YAML frontmatter block that `scripts/monitor.py` reads (format in `AGENTS.md`): `ticker`, `status: active`, `levels` (every entry/exit/stop price from section 3, each with an `id`, a `when` condition and the `action`), and `events` (the dated rows of section 8 that call for a check). The `entry-exit-timing` limit-price table maps one row per level.

Save to `trading/plans/YYYY-MM-DD-<slug>.md`, add the position to `trading/portfolio.md`, and show the user the full text.

## Mid-trade stress protocol

When the user asks "should I exit?" with a position open — or sounds scared — do **not** lead with market analysis. First run the field card's tests against their own plan, out loud:

1. Is this event already priced into the plan (the stop/cushion's job)?
2. Does the news pass through the *thesis* (supply/demand/earnings of what's held) or only through their pulse?
3. Which self is deciding — the one who wrote the plan, or the one on the minutes-chart?
4. **Which market are they in?** (field card Part 2.5) — their fear was trained on assets that can die; route the alarm by regime: no-earnings speculative → alarm usually right; crowded story stock → check the narrative; profitable cyclical → route to the invalidation list; index/megacap quality → false positive.

Only if a test genuinely fails does the market analysis begin. If the plan has no invalidation list (trade predates this skill), reconstruct one from their original thesis before ruling. Grade any completed trade on the process 2×2 (plan-adherence × outcome), never on P&L alone.

## Voice

Decisive and numbers-first — but honesty about tails outranks confidence: state the assignment/loss probability plainly, call judgmental probabilities judgmental, and never dress a rich premium as free money (high IV is rent on real risk). No CYA disclaimers. Proportionality: a quick "is this strike sane?" gets two CLI calls and a paragraph, not a plan document.
