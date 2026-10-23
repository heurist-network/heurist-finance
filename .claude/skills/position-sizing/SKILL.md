---
name: position-sizing
description: "Position sizing and risk budgeting: fractional Kelly with noisy-edge humility, volatility targeting, drawdown and risk-of-ruin arithmetic, correlation-shock sizing, and portfolio heat limits. Use when asked how big a position should be, whether to add/average down, how much total risk is on, or to size options/short positions with asymmetric tails. Trigger: `use sizing skill`."
---

# Position Sizing

Shared plumbing and output contract: [../\_shared/analyst-core.md](../_shared/analyst-core.md). Sizing is the one decision that operates on every trade, and the one public skills reduce to "risk 2%." The truths that matter: **sizing errors compound geometrically** (oversizing a positive-edge strategy can produce ruin), and **every sizing formula's inputs are estimates** — so the meta-rule is to size for the uncertainty in the estimate, not the estimate.

## The three frameworks (use ≥2, take the smaller answer)

**1. Fractional Kelly.** Kelly fraction f* = p − q/b (p win prob, q=1−p, b win/loss ratio) maximizes long-run growth *if the inputs are exact*. They never are — and Kelly is brutally asymmetric to input error: betting 2× true Kelly produces zero long-run growth with wild swings. Practitioner consensus (Thorp; MacLean/Ziemba): **¼ to ½ Kelly**, which keeps ~75%+ of the growth at ~25% of the variance. Workflow: estimate p and b from the scenario table (judgmental — label it), compute f*, quote ¼–½ of it, and show the sensitivity ("if your 60% win estimate is really 50%, Kelly goes negative — that's how little room this edge has"). A 3-scenario table collapses to binary Kelly inputs by folding: p = combined probability of the profitable scenarios, b = probability-weighted average gain of those ÷ probability-weighted average loss of the rest — label the collapse.

**2. Volatility targeting.** Size ∝ `target_vol / realized_vol` of the position (compute 63-day realized from `prices SYM --out FILE`; cap the multiplier at 1). Portfolio target for an active retail book: ~10–15% annualized. This is the fix that roughly doubled momentum's Sharpe in the academic record (Barroso & Santa-Clara; Moreira & Muir generalize it) — its real function is forcing *smaller* size in exactly the high-vol conditions where conviction feels highest. A 60-vol name gets a third of a 20-vol name's dollars at equal conviction, no exceptions by vibes.

**3. Stop-based risk budgeting** (the field-practical one): position = (account × risk-per-trade) ÷ (entry − invalidation). Risk 0.5–1.5% of account per idea for an active book — but the number that actually governs is **portfolio heat**: the sum of open risk across positions, ≤ ~5–6%. Heat is what the "2% rule" misses: six uncorrelated 1% risks are 6% heat; six *correlated* 1% risks are one 6% bet (see below). The invalidation price comes from the thesis (`technical-evidence` for placement discipline), never from the desired position size — sizing to a stop you moved to afford the size is the tail wagging the dog.

## The correction layers (where blow-ups actually come from)

- **Correlation shock:** in stress, pairwise correlations go toward 1 (Longin & Solnik) — diversification is weakest exactly when needed. Count the *effective* number of bets: four AI names + a tech-heavy index position is ~one trade. Size clusters on stress correlation (crisis behavior), not calm-period correlation; `portfolio-review` runs this test book-wide.
- **Risk of ruin compounds:** per-trade ruin probability p over n trades ≈ 1−(1−p)ⁿ — a "mere" 1% ruin chance per trade is ~39% over 50 trades. Anything with unbounded left tail (naked shorts, naked short options) must be sized so the *worst* case, not the expected case, is survivable — sum assignment/obligation dollars, not premium (see `options-strategist`, `short-thesis`).
- **Drawdown asymmetry:** −20% needs +25%; −50% needs +100%. Geometric compounding punishes variance per se — half the drawdown is worth more than it looks. This is *the* argument for undersizing that feels overcautious in real time.
- **Averaging down:** adding to a loser is only legitimate when (a) pre-planned in the entry plan as scale-in tranches, or (b) genuinely new information improved the thesis — the *price being lower* is not information. Otherwise it doubles exposure at the moment the market disagrees most, on an unchanged edge estimate.
- **The 11pm test** (from `trading-plan`): if a scary overnight headline would compel checking the position, it's oversized regardless of what the formulas said — the behavioral ceiling binds before the mathematical one, because panic-exits destroy the expectancy the sizing assumed.

## Degraded inputs (the normal case — branch explicitly)

If no ticker/instrument is named: skip vol targeting (nothing to measure) and run stop-based budgeting plus the Kelly sensitivity on the stated scenario odds. If no account size is given: output the formulas with account value as a fill-in slot, percentages fully computed, plus one worked example at a stated hypothetical size — never invent an account number.

## Output shape

A sizing answer states: the size (shares/contracts/dollars), which framework(s) produced it and their inputs, the portfolio-heat picture after adding it, the worst-case dollar loss (at the stop *and* at a gap-through-stop), and what would justify resizing. When frameworks disagree, take the smaller and say why they diverged — the divergence is usually the risk (formula assumes liquidity/normality the position doesn't have).

End with **Call / Falsifier / Horizon** — for sizing, the falsifier is the resize trigger (heat cap breached, vol regime change, thesis checkpoint), and "this trade is fine at half the size you proposed" is the most common correct call.
