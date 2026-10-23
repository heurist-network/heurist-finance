---
name: market-health
description: "Market-regime health check that terminates in an explicit exposure gate (NEW_ENTRY_ALLOWED / REDUCE_ONLY / CASH_PRIORITY): breadth, distribution-day counting, volatility regime, credit confirmation, and leadership quality. Use when asked how healthy the market is, whether now is a good time to add risk, whether a correction is starting, or before any batch of new long entries. Trigger: `use market skill`."
---

# Market Health

Shared plumbing and output contract: [../\_shared/analyst-core.md](../_shared/analyst-core.md). The most consequential retail question isn't stock selection — it's **how much equity exposure to carry right now**. Most public content answers with commentary; this skill answers with a gate. The output is one of three states, borrowed from the best practice in public trading skills and worth adopting as-is:

- **NEW_ENTRY_ALLOWED** — regime supports adding risk; normal sizing applies.
- **REDUCE_ONLY** — hold what's working, no new entries, trim laggards; tighten falsifiers.
- **CASH_PRIORITY** — distribution/stress regime; raising cash outranks any new idea.

The state is a *gate on other skills* (momentum entries, screen finalists, event trades all check it), and its confidence is **capped by input completeness**: with inputs missing or conflicting, default to the more conservative state and say which inputs were unavailable — never average conflicting readings into false moderation.

## The inputs (pull all five lanes; each can veto)

1. **Index trend + distribution counting.** `technical_snapshot symbols=^GSPC,^IXIC` (daily + weekly). Trend state vs 50/200d first. Then count **distribution days** — declines ≥ ~0.2% on higher volume than the prior day — over the trailing 25 sessions (compute from `prices ^GSPC --period 3mo --full --out FILE`; volume needs `--full`): **4–6 in the window is the O'Neil-school caution signal** that institutional selling is underway, historically preceding intermediate corrections. Cluster timing matters more than raw count; expire days older than 25 sessions. A follow-through day (major index +1.5%+ on rising volume, day 4+ of a rally attempt) is the same school's re-entry signal after a correction — label both as practitioner methodology with real but imperfect hit rates (false FTDs happen in bear markets; the tool is exposure throttling, not prophecy).
2. **Breadth (the market of stocks vs the stock market).** % of members above 200d/50d MAs, new highs − new lows, advance/decline behavior; equal-weight vs cap-weight spread (RSP vs SPY via `prices`) is the cheap always-available proxy — a cap-weighted index at highs while the equal-weight lags badly and NH-NL is negative = narrow leadership, the classic late-stage signature. Sourcing: attempt the primary breadth statistics first via `web` (Barchart/StockCharts publish them); only after that attempt fails, say so and fall back to the RSP/SPY proxy + sector participation (`sector-rotation`), labeled as proxy.
3. **Volatility regime.** `^VIX` level + realized vol of the index. VIX > ~28–30 with an inverted VIX term structure = stress regime (forced flows dominate); VIX grinding under ~13 for months = complacency (cheap hedges, stretched rubber band — an input to REDUCE_ONLY only in combination). The *transition* (VIX regime shift on rising realized) matters more than the level.
4. **Credit confirmation.** From `macro-regime`: IG/HY OAS direction (`fred macro_series_history`). Equity weakness *without* credit confirmation is usually rotation → don't gate to CASH_PRIORITY on equities alone. Credit widening + equity weakness = genuine regime risk.
5. **Leadership quality.** What's leading the tape (`equity_screen day_gainers`, sector RS from `sector-rotation`, news tone via `yahoo news_search`): offensive leadership (cyclicals, quality growth, broadening participation) vs defensive/speculative leadership (staples+utilities leading = risk-off internals; low-quality speculative froth leading = late-stage recruitment). Leadership is the tiebreaker lane when trend and breadth disagree.

## Mapping inputs → state

No composite score — per the core rules, a single number would launder five judgments. Instead: **CASH_PRIORITY** requires at least two independent lanes in stress (e.g., distribution cluster + credit widening, or trend break + breadth collapse). **REDUCE_ONLY** on any single hard veto: distribution count ≥5, index below a falling 200d weekly trend, breadth divergence persisting >4 weeks at new index highs, or a VIX-regime flip. **NEW_ENTRY_ALLOWED** needs trend up *and* breadth participating *and* no credit deterioration — health is conjunctive, sickness is disjunctive, which encodes the asymmetry that missing a week of upside is cheap and catching a distribution phase fully invested is not.

State the reading's dissent honestly: "trend and leadership say allowed, breadth dissents — allowed, half-size entries" is a legitimate refined output. End with the gate as a dated line other skills can quote — `Gate: REDUCE_ONLY as of 2026-07-11` — because a health reading is good for days, not weeks: treat one older than a week, or predating a 2%+ index day, as expired and re-run.

## No-edge honesty

This gate does not predict crashes, call tops, or time bottoms — nobody reliably does, and pretending to is the signature slop of market-commentary content. What it does is *documented-input exposure throttling*: institutional distribution, breadth deterioration, and credit stress are observable while they happen, and reacting to them mid-process (weeks-scale) is exactly what a multi-week retail seat can do that a benchmark-hugging fund cannot.

End with **Call / Falsifier / Horizon** — the Call is the gate state; the falsifier is what flips it (e.g., "upgrades on a valid follow-through day + breadth thrust"; "downgrades on a 5th distribution day or HY > 400bps").
