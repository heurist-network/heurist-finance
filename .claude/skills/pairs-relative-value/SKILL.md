---
name: pairs-relative-value
description: "Pairs and relative-value analysis: cointegration testing, spread half-life, entry/exit bands, dollar/beta-neutral construction, and the structural-break risks that kill pairs. Use when asked to trade one stock against another, evaluate a long/short pair, hedge a single-name view, or find relative-value between related assets. Trigger: `use pairs skill`."
---

# Pairs & Relative Value

Shared plumbing and output contract: [../\_shared/analyst-core.md](../_shared/analyst-core.md). A pair converts a market-direction bet into a *relationship* bet. That removes beta and adds two new ways to lose: the relationship breaks, or it mean-reverts slower than the capital can wait. Both are testable before entry — so test them.

## Qualify the pair (compute, don't assert)

Pull both legs: `hf_tool.py prices A B --period 3y --out FILE`, then a Python block for the statistics. The gates, in order:

1. **Economic linkage first.** Same demand driver, same input costs, or substitute products — stated in one sentence. Data-mined pairs with no economic reason are the ones that break. (KO/PEP yes; "these two cointegrated in-sample" no.)
2. **Cointegration, not correlation.** Correlation 0.9 says they wiggle together; cointegration says the *spread* is stationary — only the second supports mean-reversion trading. Engle–Granger on log prices (regress, ADF-test the residual) over a ~3y lookback, demand p < 0.05 — **and require sub-sample stability**: re-run on each half of the window and the most recent year; a pair that only cointegrates over the full window is regime-dependent, treat it as failed. High correlation with failed cointegration = trending spread = the classic slow bleed. **Failed cointegration with a real economic link and a directional relative view** downgrades to the fallback structure: a return-beta-hedged overlay (hedge ratio from a return regression), traded as directional relative value on a thesis falsifier — no bands, no mean-reversion logic, and say it's not a pair.
3. **Half-life of the spread** (fit OU / AR(1) on the residual: half-life = −ln(2)/ln(φ)). **Reject > ~30 trading days** — beyond that, capital lock-up and break risk dominate the convergence P&L, and it exceeds the user's multi-week horizon anyway. 5–20 days is the sweet spot.
4. **Hedge ratio from the cointegrating regression** (not 1:1 shares, not equal dollars unless β≈1): position legs so the traded unit is the stationary spread. Then check residual beta — sector-neutral pairing (both legs same sector) removes ~60% of market beta by construction; cross-sector "pairs" are usually a hidden factor bet (long tech / short energy is a rates trade wearing a pairs costume — say so).
5. **Short-leg reality check:** borrow availability and fee (`equity_overview`, short-interest context via `equity_screen screen_name=most_shorted_stocks`). A pair whose short leg is > 10–15% borrow fee or squeeze-listed has asymmetric blow-up risk — the short leg gets recalled precisely when it's ripping.

## Trading rules

- **Entry at ±2σ** of the spread's trailing distribution (use the half-life window ×4–6 for the lookback); **exit at mean**; **hard stop at 3–3.5σ** — at three-plus sigmas the correct Bayesian read is *structural break, not opportunity*. Averaging into a diverging spread is how pairs traders die.
- **Base rate for humility:** the canonical distance-method pairs study (Gatev, Goetzmann & Rouwenhorst 2006) earned ~11%/yr gross, **~6% after costs**, on a diversified book of pairs with 1–6 month holds. One pair is a coin with edge, not an income stream — expect single-pair hit rates near 60–70% with occasional full-stop losses.
- **Event scan before entry, both legs:** earnings dates (`equity_overview`), pending deals, index-change rumors. An acquisition of either leg is the #1 structural break; earnings inside the trade window turns the pair into two event bets. Check `yahoo news_search` for both.
- **Leverage math:** 2:1 gross on a ~6%/yr spread strategy with a realistic 15% spread-drawdown tail produces negative geometric returns if sized to peak margin. Size the pair so the 3.5σ stop is an acceptable loss, per `position-sizing`.

## What not to pair

- Levered/inverse ETFs on either leg — path dependency (vol drag) destroys the spread logic even when the ratio view is right.
- ADR-vs-local or ETF-vs-NAV arb — bank-desk latency games, no retail seat.
- Two names whose "relationship" is one year of a shared narrative. Cointegration needs a full cycle of history (≥2–3y) and even then breaks when the business models diverge (the pair that was Kodak/Fuji).

Relative value also generalizes beyond two stocks: stock vs its sector ETF (isolate idiosyncratic view), commodity producer vs the commodity (`commodity-curve` for the curve leg), megacap vs equal-weight. Same gates apply — economic link, stationarity, half-life, borrow.

End with **Call / Falsifier / Horizon** — the falsifier is the σ-stop or a named structural event; the horizon is a small multiple of the measured half-life, and if that math doesn't fit multi-day-to-multi-week, the honest call is "no trade."
