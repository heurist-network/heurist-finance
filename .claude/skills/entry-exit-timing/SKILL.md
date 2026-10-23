---
name: entry-exit-timing
description: "Turn an existing trade thesis into timed entries and exits with concrete limit prices: regime classification (fade vs follow), sigma/z-score band reads, MACD as trend descriptor, Fibonacci-gridded pullback zones for limit-order ladders, and stop/target placement from the same math. Use when asked when to buy/sell, where to set a limit order, whether to buy the dip or the breakout, or how to scale into/out of a position. Trigger: `use timing skill`."
---

# Entry & Exit Timing

Shared plumbing and output contract: [../\_shared/analyst-core.md](../_shared/analyst-core.md). Scope discipline first: **timing sits on top of a thesis, it doesn't create one.** This skill takes a direction that already exists on other grounds (any style skill) and answers *when* and *at what price* — its value is improving the entry/exit price distribution and forcing pre-committed levels, worth real basis points but never a substitute for edge. If no thesis exists, route to a style skill first.

## Step 1 — Classify the regime (this decides everything)

The universal timing error is applying a mean-reversion tool in a trend or a breakout tool in a range. Classify before choosing, from `prices SYM --period 1y --out FILE` + `technical_snapshot`, computed not eyeballed:

- **Efficiency ratio** (Kaufman): |net change over 20d| ÷ sum of |daily changes|. > ~0.4 = trending; < ~0.2 = ranging; between = mixed (halve size or stand aside).
- Corroborate: price vs 50/200d structure and slope; Bollinger band *width* percentile (squeezes precede expansion — a 6-month-low band width says the next move is a break, not a fade); MACD histogram sign and slope as the trend descriptor it honestly is (Tier 2 per `technical-evidence` — a smoothed trend state, not an entry oracle; its crosses lag ~by construction and whipsaw in ranges).
- **The mapping:** trending → buy pullbacks / breakout retests in trend direction only; never fade band touches against the trend (riding the upper band is what strong trends *do* — "overbought" is a trend's natural state). Ranging → fade the extremes toward the mean, both directions eligible. This split is the entire reason band fades sometimes "work great" and sometimes bleed — the tool didn't change, the regime did.
- **When daily and weekly disagree,** the thesis horizon governs: a multi-week thesis trades the weekly regime and uses the daily read only for entry location; if the setup exists only on the daily, it's a shorter trade than the thesis — say so and treat it as one.
- Before recommending any fresh entry, establish the current `market-health` gate (run its quick dashboard — index trend + distribution count — if not already known this session) and name it in the Call; a REDUCE_ONLY tape caps fresh-entry recommendations.

## Step 2 — The σ framework (bands done right)

Work in z-scores, not band-touch binaries: z = (price − 20d SMA) ÷ 20d σ (Bollinger with 2σ default; %b is the same number rescaled).

- **Mandatory base-rate computation before any band trade** — this is the skill's core move and what separates it from chart-lore: find every prior z < −2 (or > +2) instance in 2–5y of history for *this name*, compute forward 5/10/20-day returns vs unconditional baseline, report N, hit rate, and average move. < 10 occurrences = anecdote, say so. The documented anchor is short-term reversal (Jegadeesh 1990, ~1-week horizon, liquid names) — σ-extremes are its practical detector, but the effect size varies enormously by name and regime, hence: measure, don't assume.
- **Range-regime fades:** enter z ≤ −2 (long) with limit orders (below), target the mean (z=0) or opposite band, **time-stop ~5–10 sessions** — mean-reversion that hasn't reverted is a broken assumption (half-life logic from `pairs-relative-value` applies to single names too). Hard stop at z ≈ −3 *with a fundamental-news check*: a 3σ move on news is regime change, not opportunity (don't fade earnings gaps — see `earnings-play`).
- **Trend-regime pullbacks:** the buy zone is the pullback to the 20d mean or −1σ *within* an uptrend (z between 0 and −1.5), MACD histogram contracting-then-curling as the maturity read; not the −2σ panic level, which in a healthy trend rarely prints and in a dying one prints on the way to worse.

## Step 3 — Fib grid → limit-price ladder (the honest version)

Straight talk first, consistent with `technical-evidence`: Fibonacci ratios carry **no replicated statistical edge** — 38.2/50/61.8% are not magic numbers. What *is* empirically normal: pullbacks within intact trends commonly retrace roughly one-third to two-thirds of the prior swing before resuming. The fib grid is a useful **convention for gridding that zone into pre-committed limit prices** — use it as a price ladder, never as evidence.

Mechanics: define the swing (last significant low→high for a long entry, off the weekly for multi-week theses); compute 38.2%/50%/61.8% retracement prices; then **confluence-gate each level** — a level earns a limit order only where it coincides with independent structure: the σ-band level from Step 2, prior breakout/consolidation shelf, the rising 50d MA, round-number liquidity. Confluence of two-plus independent levels beats any single line; a bare fib with nothing beneath it gets nothing.

Two entry modes, don't blend them: if the trade is a single range-regime fade, it gets one entry at the band with Step 2's time-stop — no ladder; if it's multi-week accumulation of a thesis position, grid the ladder below.

**The ladder (default 3 tranches for scale-in):** ~25% of intended size at the first confluence (typically the 38.2% zone / −1σ), ~35–40% at the second (50% / mean or shelf), remainder at the deep zone (61.8% / −2σ) — sized so the *full* fill at the deep level is the position `position-sizing` approved, and a partial fill is a smaller position, not a worse one. State every limit price explicitly in the output, plus: **invalidation below the 61.8–78.6% zone** — a retracement beyond ~2/3–3/4 of the swing has empirically stopped being a pullback and become a reversal, which is exactly where the stop belongs (stop = ladder bottom minus ~1 ATR of slack, so the stop isn't inside normal noise; pull ATR from the price file).

Ladders and gaps: limits are GTC until the thesis checkpoint or the invalidation prints; if price gaps *below* the whole ladder, cancel — do not chase the falling knife the ladder was designed to buy in an orderly way; if price runs *up* without filling tranche 1, the disciplined miss is the correct outcome (chasing converts a timing plan back into impulse).

## Exits use the same math in reverse

Profit targets at the opposite band / prior swing extension with the measured base rate as the sanity check; scale-out ladder mirrors the scale-in; trend positions trail by structure (`momentum-trend` exits — falsifier levels, not targets); mean-reversion positions exit at the mean *by default* and always by the time-stop. Selling an existing holding into strength: grid +1σ/+2σ/prior-high confluence as limit-sell levels — same machinery, opposite sign. Worked shape for an existing winner: sell ~25% at +1σ, ~35% at +2σ or the prior high (whichever confluence is nearer), trail the remainder with a stop at the higher of the breakout/entry shelf or the last swing low − 1 ATR — tranche sizes mirror the scale-in, and the stop formula is the entry one reflected.

## No-edge honesty

Timing refinement is worth tens of basis points per entry, compounding but modest — it will never rescue a wrong thesis, and over-optimizing entries (waiting for the perfect −2σ that never comes) costs more in missed theses than it saves in fills. Intraday band/MACD scalping on liquid names is HFT territory with no retail seat. And every level this skill outputs is *visible to everyone* — the edge isn't the level, it's the pre-commitment: limits placed calmly in advance beat market orders placed emotionally in the moment, which is a behavioral edge (the field card's whole thesis) rather than an informational one. Frame it that way.

End with **Call / Falsifier / Horizon** plus the **limit-price table** (level, price, tranche size, confluence justification, stop, time-stop) — the table *is* the deliverable; entering the resulting position at size still routes through `trading-plan`.
