---
name: macro-regime
description: "Translate macro conditions into positioning: yield curve, credit spreads, dollar, inflation/growth mix — read the regime, then express it as specific trades with invalidation levels instead of macro commentary. Use when asked what the macro backdrop means for a portfolio, how to position for Fed/inflation/recession scenarios, or whether a macro fear should change equity exposure. Trigger: `use macro skill`."
---

# Macro Regime

Shared plumbing and output contract: [../\_shared/analyst-core.md](../_shared/analyst-core.md). Two failure modes dominate retail macro: consuming macro as *commentary* (no position, no falsifier), and expressing a macro view through the wrong instrument. This skill's contract: every macro read terminates in **an expression with an invalidation level** or an explicit "this changes nothing at your horizon."

## The regime dashboard (pull, don't recall)

`fred macro_regime_context` for the evidence: pillar-grouped series with latest observations, derived yoy/mom and direction, and an `as_of_date`. It returns no regime labels — **classify the regime yourself from the derived series, and date the classification with the response's `as_of_date`**; never quote a regime label as if the tool asserted it. Then `macro_series_history`/`macro_series_snapshot` for the specific series; `yahoo market_overview market=RATES|CURRENCIES|COMMODITIES` for the live tape. Release timing via `macro_release_calendar`. Use `macro_vintage_history` when judging what was knowable at a past date (revisions rewrite history — especially payrolls).

The four inputs that carry most of the signal, with their documented readings:

- **Yield curve (10y−3m).** Inversion has preceded every US recession with ~4–6 quarter lead (Estrella & Mishkin 1996) — but it's a *warning*, not a timer: 1998 and 2019-style false/soft signals exist, and equities often rally for months post-inversion. The recession-proximate signal is the **re-steepening from inversion** (front-end collapsing = Fed cutting into weakness). Never cite the curve without a credit and labor cross-check.
- **Credit spreads — the honest one.** IG OAS widening **> ~100bps off its 12-month trough**, or HY OAS through ~500bps, has coincided with essentially every >15% equity drawdown. Credit leads or confirms; equity-only signals without credit confirmation are usually rotation, not regime change.
- **Dollar.** ±10% YoY DXY moves transmit mechanically: strong dollar pressures EM, commodities, and S&P multinational EPS (sell-side rule of thumb ~30–40bps of EPS per 1% DXY — cite as rule of thumb). A commodity or EM thesis that ignores the dollar direction is half a thesis.
- **Growth/inflation mix** defines the quadrant: rising growth + falling inflation is the equity sweet spot; falling growth + rising inflation is the only quadrant where bonds don't hedge stocks (2022). The mix, not the level, drives cross-asset correlation — and stock-bond correlation flips sign with the inflation regime, which changes what "diversified" means (see `portfolio-review`).

**Bear-flattening + credit-widening together** (front rates rising faster than long, HY leaking) is the specific combination with a poor forward equity hit rate — treat it as the derisk tripwire rather than any single series.

## Regime → expression

The discipline: pick the instrument that isolates the view. Rate view → rate-sensitive instrument (long-duration Treasury ETF, not "short tech as a rates proxy"). Dollar view → FX/commodity expression. Recession view → credit/defensives/duration, sized to survive being early. Retail expresses macro through levered single-name equities mostly because those are the tickers at hand — flag it every time; the basis between the view and the instrument is an uncompensated risk.

- Every expression carries a **macro invalidation level on the driver itself** (e.g., "wrong if HY OAS re-tightens below X" / "wrong if core CPI prints < Y% two consecutive months"), not just a price stop on the instrument.
- **Being early is the expensive part** ("fighting the Fed"): shorting equities three quarters before a recession that arrives — or doesn't — bleeds carry the whole way. Macro derisking for this user usually means *exposure reduction and hedge structure* (see `position-sizing`, `options-strategist` for cheap tails), not outright macro shorts.
- Macro regime also acts as a **gate on the other skills**: momentum crash conditions, vol-selling regimes, cyclical multiples — when the regime read is bearish, say which *other* active playbooks it demotes.

## No-edge honesty

The first minutes after CPI/FOMC/payrolls are pod-shop territory — no retail edge, and the day-1 reaction frequently reverses. The retail-viable macro horizon is **weeks-to-quarters positioning**, where the edge is patience and the willingness to hold an uncomfortable view with a defined falsifier, not reaction speed. Also: a macro narrative that can't name its transmission channel into the specific asset ("rates up → so what for *this* stock's cash flows?") is commentary, not analysis — check recent news (`yahoo news_search`, `web`) rather than re-deriving consensus.

End with **Call / Falsifier / Horizon** — the falsifier lives on the macro series, the horizon in weeks-to-quarters, and "your equity ideas are fine, macro changes nothing at your horizon" is a legitimate and common call.
