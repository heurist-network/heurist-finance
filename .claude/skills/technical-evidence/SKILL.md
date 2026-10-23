---
name: technical-evidence
description: "Technical analysis ranked by evidence: which price-based signals have documented statistical support (short-term reversal, 52-week-high effects, post-earnings drift), which are degraded, and which are folklore — plus how to use TA correctly as timing/risk placement for a thesis. Use when asked to read a chart, judge support/resistance, evaluate an indicator signal, or time an entry/exit. Trigger: `use technicals skill`."
---

# Technical Evidence

Shared plumbing and output contract: [../\_shared/analyst-core.md](../_shared/analyst-core.md). TA's honest job in this stack: **timing and risk placement for a thesis that exists on other grounds** — and occasionally a standalone signal where the effect is actually documented. (For the operational entry/exit procedure — regime-gated band reads, limit-price ladders, stops — use `entry-exit-timing`; this skill is the evidence layer beneath it.) This skill's core content is the evidence tiering, because treating folklore and documented effects as one "technical picture" is the signature TA failure.

## The evidence tiers

**Tier 1 — documented, still-live effects (usable as signal):**
- **Short-term reversal:** ~1-week losers beat winners over the following week (Jegadeesh 1990) — liquid names, fades with size. Implication: *don't chase* multi-day spikes; buy pullbacks, fade panic days in quality names.
- **52-week-high proximity** (George & Hwang): anchoring underreaction near highs, ~0.5%/month effect. New-high lists are a feature, not a warning.
- **Momentum 3–12 months** — full treatment in `momentum-trend`; it's the strongest price-only effect known.
- **Post-earnings drift** — price/volume confirmation of a surprise carries real forward signal (`earnings-play`).
- **Volatility clustering:** today's vol predicts tomorrow's (the one universally replicated price fact) — position sizing and stop width should be ATR/realized-vol-scaled, always.

**Tier 2 — degraded or conditional (context only, never standalone):**
- **Moving-average trend rules:** genuine in-sample edge on indices pre-1990 (Brock, Lakonishok & LeBaron 1992), largely arbitraged away after publication and costs. Still useful as *regime descriptors* (above/below 200d changes the return distribution's shape) — not as entry signals.
- **RSI(2)-style short-term mean reversion** (Connors): worked in specific ETF samples, regime-dependent, dies in trends. Test on the actual asset's recent data before citing (see below).
- **Volume confirmation:** breakouts on ≥1.5× average volume fail less often — directionally supported, weak alone.
- **Classic patterns (head-and-shoulders etc.):** mixed academic evidence (Lo, Mamaysky & Wang found *some* information content; out-of-sample profitability after costs is thin). Descriptive language, not signal.

**Tier 3 — folklore (never present as evidence):** Fibonacci retracements, harmonic patterns, Elliott wave counts, candlestick-catalog names, round-number "psychology" beyond liquidity clustering. If the user leans on these, say plainly they have no replicated statistical support — offer the Tier 1/2 nearest-neighbor instead of humoring the frame.

## Compute the base rate instead of eyeballing the chart

The agent's structural advantage over a human chartist: it can *test the claim on the spot*. When a setup is proposed ("this always bounces at the 50-day"), pull `prices SYM --period 5y --out FILE` and compute the actual conditional stats in Python: how many prior touches, what happened next, win rate and average move vs the unconditional baseline. A dozen lines of numpy converts chart-lore into either a measured edge or a debunk — do this whenever a specific repeatable pattern is claimed. Small-sample honesty: <10 occurrences = anecdote, label it.

## Using TA correctly (the risk-placement job)

- **Levels are for stops, not prophecy.** A support level's value is that it's a *falsifier location*: below it, the structure that justified the position is objectively gone. Place invalidation where the thesis breaks, then size from stop distance (`position-sizing`) — never the reverse (sizing first, then finding a "level" that fits).
- **Read structure off `technical_snapshot`** (trend state, momentum, vol, key levels) and the weekly timeframe for any multi-week thesis — the daily chart's noise is not the holding timeframe's signal. Match the chart's timeframe to the trade's clock (a trading-plan principle).
- **Divergence between price and thesis timeframes** is the useful chart alarm: a multi-week fundamental long breaking its weekly uptrend on volume deserves a thesis re-check (route through the invalidation list, not the pulse — see trading-plan's stress protocol).
- Indicator soup (RSI+MACD+Bollinger+Stoch on one chart) is four correlated transforms of the same price series pretending to be confirmation — pick trend, momentum, vol once each.

## No-edge honesty

Intraday tape/level-2 reading on liquid names is a spoofing-rich HFT arena; candlestick day-trading on mega-caps has no retail seat. Price-only edges at the multi-day horizon are thin and mostly the Tier 1 list — TA earns its keep here as **discipline infrastructure** (falsifier locations, vol-scaled stops, regime awareness), which is genuinely valuable and honestly framed as such.

End with **Call / Falsifier / Horizon** — technically-derived falsifiers are the skill's best output: a specific level or structure whose loss objectively kills the setup.
