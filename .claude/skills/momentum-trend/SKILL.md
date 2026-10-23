---
name: momentum-trend
description: "Momentum and trend analysis with crash-risk discipline: 12-1 cross-sectional momentum, trend-template staging, time-series trend, volatility-scaled sizing, and the regimes where momentum blows up. Use when asked whether to buy strength, chase a breakout, hold a winner, evaluate relative strength, or trade a trending stock/commodity. Trigger: `use momentum skill`."
---

# Momentum & Trend

Shared plumbing and output contract: [../\_shared/analyst-core.md](../_shared/analyst-core.md). Momentum is the best-documented anomaly in the cross-section (~1%/month winner-minus-loser spread at 3–12 month horizons, Jegadeesh & Titman 1993, replicated across countries and asset classes) — **and** it carries the worst left tail of any factor. This skill is both halves.

## Measuring it right

- **The signal is 12-1, not 12-0:** total return over the past 12 months *excluding the most recent month*. The most recent ~1–4 weeks mean-reverts (Jegadeesh 1990) — chasing last week's winner is trading *against* the documented signal. Compute from `hf_tool.py prices SYM --period 2y --out FILE`, in Python.
- **Two flavors, low correlation (~0.1–0.3), use both:** cross-sectional (strong *relative to* peers/universe — rank the candidate against its sector ETF and SPY) and time-series (strong *in absolute terms* — is the asset above its own trend?). A stock outperforming a falling sector is a short-squeeze candidate, not a momentum long.
- **52-week-high proximity is its own signal** (George & Hwang): distance from the 52-week high predicts returns via anchoring underreaction, ~0.5%/month spread. Near-high consolidation > deep-drawdown "recovery momentum."
- **Trend template for staging** (Minervini-style, get inputs from `yahoo technical_snapshot`): price > 50d > 150d > 200d MA, 200d rising ≥ ~1 month, price ≥ 30% above 52w low and within ~25% of 52w high, relative strength vs SPY positive over 3/6/12mo. All true = Stage 2 (the only stage this skill buys). Breakouts want volume ≥ 1.5× 50d average; **extension > 50% above the 200d MA is a penalty, not strength** — mean-reversion risk dominates fresh-breakout economics there.

## The crash half (this is what public momentum content omits)

Momentum's returns are negatively skewed and its crashes are *predictable in kind*: they cluster when the market rebounds sharply after a big drawdown — the short/avoided leg (junk that fell most) squeezes violently while the winners lag (Daniel & Moskowitz 2016; 1932, 2009, 2020 each erased 1–2 years of momentum gains in weeks). Decision rules:

- **Regime gate before any momentum entry:** if the index is < ~2 months past a >20% drawdown low, or realized index vol is in its top decile, momentum entries are cut to half size or skipped. Before recommending fresh entries, establish the current `market-health` gate (run its quick dashboard if not already known this session) and name it in the Call; a REDUCE_ONLY tape caps fresh-entry recommendations.
- **Vol-scale the position** (Barroso & Santa-Clara 2015 — roughly doubles momentum Sharpe and cuts max drawdown): size ∝ `target_vol / realized_vol` of the name (63d realized, capped at 1×). A 60-vol name gets ~⅓ the dollars of a 20-vol name for the same conviction.
- **Exits are trend-defined, not target-defined:** the position lives while the structure that admitted it holds (e.g., close below the 50d on volume, or breakout level lost). Momentum winners are cut by falsifier, not sold at "fair value" — the whole anomaly is that they run further than feels reasonable.

## Costs and horizons (retail honesty)

- Monthly-rebalanced momentum in mid/large caps survives costs; **weekly-turnover momentum in illiquid names bleeds 2–4%/yr to spread and slippage** — the variant retail most often implements is the one that doesn't survive.
- 1–5 day "momentum" on liquid ETFs is an HFT game; gap-chasing meme names after social velocity peaks is buying someone's exit. The user's multi-day-to-multi-week seat matches the documented 3–12 month signal horizon — say so when an idea is really a day-trade in disguise.
- Momentum + leveraged ETFs compound the convexity you don't want (vol drag + crash skew).

End with **Call / Falsifier / Horizon**. The falsifier is structural (trend level / regime trigger), never a P&L number. Entering for real → hand to `trading-plan` for sizing and the invalidation list.
