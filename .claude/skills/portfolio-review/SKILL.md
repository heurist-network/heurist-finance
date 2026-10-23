---
name: portfolio-review
description: "Whole-book risk audit: effective number of bets (correlated-position clustering), concentration, factor and macro tilts, stress-beta scenario testing, hidden option obligations, and liquidity-to-exit. Use when asked to review a portfolio, check total risk, find hidden correlations, judge diversification, or assess what a crash/rate-shock would do to current holdings. Trigger: `use portfolio skill`."
---

# Portfolio Review

Shared plumbing and output contract: [../\_shared/analyst-core.md](../_shared/analyst-core.md). Positions are sized one at a time (`position-sizing`), but ruin happens at the book level — usually because ten "different" positions turn out to be one bet. This skill audits the book the way a risk desk would: not "are the picks good?" but **"what is this portfolio actually one big bet on, and what happens when that bet has its worst month?"**

Input: the user's holdings (tickers, sizes, cost basis if offered, open options positions with strikes/expiries). Ask for them if not provided — there is no useful portfolio review without the actual book.

## The audit, in order of how often it finds the problem

1. **Effective number of bets (the headline finding, usually).** Cluster holdings by shared driver, not by sector label: four AI-adjacent names + QQQ + a semis ETF = one trade with six tickers. Method: pull 1–2y of prices for all holdings (`prices ... --out FILE`), compute the pairwise correlation matrix in Python, cluster at |ρ| > ~0.6, and — because calm-period correlation understates it — re-cluster using each name's behavior in the last genuine stress window (2022 for rates, 2020 for growth-shock). Look-through ETFs with `fund_snapshot` before clustering: overlapping top holdings across "diversified" ETFs is the most common hidden concentration. Report: *N tickers, ~K effective bets, largest cluster = X% of book.*
2. **Concentration + liquidity.** Top position and top cluster as % of book (top single > ~15% or top cluster > ~35% deserves an explicit conviction justification, not a drift explanation — most concentration is unrebalanced winners, which is a decision being made by default). Days-to-exit per position at ~20% of ADV; a book that takes two weeks to unwind owns a risk the P&L doesn't show (`small-cap-scout` math, book-wide).
3. **Factor and macro tilts.** Estimate book beta (position-weighted, from the price file); eyeball the style skew (growth/value, size, momentum-crowding overlap) and translate to macro exposure in plain terms: *"this book is long duration + long AI capex + short energy — it has a rates view whether you meant one or not."* Cross-check against the user's *stated* views — the coherence test at book level: a user predicting a correction while running a 1.3-beta, zero-cash book is fighting themselves (same logic as `trading-plan`'s conflict flagging). Stock-bond correlation flips sign with the inflation regime (`macro-regime`), so "stocks + bonds = diversified" is regime-dependent — check which regime is live before crediting the hedge.
4. **Options-adjusted truth.** Sum short-put assignment obligations in dollars (that's shadow equity exposure at exactly the prices where it hurts); covered calls = sold right tail (the book's best names are the ones capped — say it); count net short-vol exposure across positions that all sell premium (one vol spike hits them simultaneously — that's a cluster too). Beta-weight option deltas into the book beta.
5. **Stress scenarios (dollars, not percentages).** Three concrete scenarios keyed to the book's actual tilts — e.g. rates +100bps, index −15% growth-led, the largest cluster's specific thesis breaking — and the estimated dollar drawdown of each, using stress correlations (→1 within risk assets; Longin & Solnik). Then the behavioral check: is the worst number one the user can sit through without panic-liquidating at the low? If not, the book fails the 11pm test at portfolio scale and the fix is pre-emptive trimming, not resolve (`trading-plan` field-card logic).
6. **Cash and dry powder.** Cash % vs the current `market-health` gate: zero cash in REDUCE_ONLY regimes means every new idea forces a sale (decision coupling); large cash in NEW_ENTRY_ALLOWED regimes is a position too — an implicit market-timing bet that should be owned as a decision.

## Output shape

Lead with the two or three findings that change behavior, quantified ("6 tickers, 2.5 effective bets; a −20% AI-cluster move costs ~$X, 34% of book"). Then the full table. Every finding pairs with a specific action (trim X to Y%, replace overlapping ETF, buy the tail hedge, hold as-is with eyes open) — an audit without actions is commentary. Do not manufacture problems in a healthy book: "appropriately concentrated for your conviction, sized to survive being wrong" is a legitimate result.

## Honesty items

- Correlation estimates from short windows are noisy and stress correlations are estimates of estimates — present cluster math as structure-revealing, not decimal-precise.
- This skill measures risk; it does not rank the holdings' merits — route "should I still own X?" per-name questions to the relevant style skill, and rebalancing *trades* through `trading-plan`.
- Diversification's payoff is geometric (drawdown reduction compounds — see `position-sizing` drawdown math), which is why the boring finding ("trim the winner cluster") is usually worth more than any new idea.

End with **Call / Falsifier / Horizon** — the Call is the book verdict + top actions; the falsifier is the review's refresh trigger (cluster exceeding a threshold, regime flip, any single position crossing its ceiling).
