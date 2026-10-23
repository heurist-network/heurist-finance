---
name: sector-rotation
description: "Sector allocation and rotation analysis: cycle-template positioning with base-rate humility, sector relative-strength ranking (where momentum actually works well), rate-sensitivity mapping, and breadth-within-sector confirmation. Use when asked which sectors to overweight, whether a sector move has legs, how rate/macro shifts hit sectors differently, or to place a stock pick in its sector context. Trigger: `use sector skill`."
---

# Sector Rotation

Shared plumbing and output contract: [../\_shared/analyst-core.md](../_shared/analyst-core.md). Sector selection explains a large share of a stock pick's return — a right stock in a wrong sector fights the tide the whole hold. Two engines drive this skill: **relative strength** (empirically the stronger one — momentum works notably well at the sector/industry level, where trends persist longer than in single names) and the **cycle template** (useful map, unreliable clock).

## The relative-strength engine (primary)

Data: `prices` on the SPDR set (XLK XLF XLE XLV XLI XLP XLY XLU XLB XLC XLRE) vs SPY, 6mo–2y; `technical_snapshot symbols=...` batched; `fund_snapshot` for what's actually inside a sector ETF (XLK's concentration means "tech sector" ≈ three stocks — always check before treating an ETF as a diversified sector view).

- **Rank sectors by 3- and 6-month return vs SPY** (computed, not recalled). Industry/sector momentum was Moskowitz & Grinblatt's finding before stock momentum got the fame — persistent enough that the top-3-sectors-by-RS rule has real backing. New leadership (a sector crossing into the top ranks after quarters at the bottom) is more information-rich than incumbency.
- **Confirm with breadth inside the sector:** a sector rally led by one mega-cap while the median member lags is a stock story wearing a sector costume (check equal-weight variants — RSP-style — via `prices`, or eyeball top-holdings dispersion from `technical_snapshot` on the ETF's top names). Broad participation = allocatable theme; narrow = pick the stock instead, or skip.
- **Duration of a rotation:** sector leadership regimes historically persist quarters, not days — which is exactly the user's horizon. A two-week bounce in last year's loser sector is more often short-covering than rotation; demand a month-plus of RS improvement plus a macro reason before calling it a turn.

## The cycle template (secondary — map, not clock)

The classic sequence — early cycle: financials, consumer discretionary, industrials; mid: tech, materials; late: energy, staples, healthcare; recession: staples, utilities, duration proxies. It's a real tendency with an honest caveat the user must hear: **cycle phase is only identifiable with confidence in hindsight**, and the sequence has broken in structurally driven markets (2020's tech-led "recession", AI capex overriding rate sensitivity). Use the template to *explain and cross-check* an RS reading ("energy leading + curve steepening = late-cycle-consistent"), never to front-run a phase the data hasn't confirmed.

**Rate-sensitivity map** (the mechanical part, pair with `macro-regime`): rising long yields pressure duration-like equities (REITs, utilities, unprofitable growth) and help banks' margins (until credit cracks); falling real rates lift gold miners and long-duration growth; the dollar routes energy/materials (see `commodity-curve` — a sector call on XLE is half a crude call: do the crude work). Every sector overweight should name its macro exposure explicitly, because a sector bet is usually a macro bet with a ticker.

## Workflow for a rotation call

1. Compute the RS ranking table (6mo and 3mo, both vs SPY) — show it.
2. For the proposed over/underweights: breadth check, concentration check (`fund_snapshot`), macro consistency (`macro-regime` inputs), and the crowding thermometer (`sentiment-positioning` — a sector that dominates news flow for weeks is late in the recruitment cycle; check `yahoo news_search` / `web`).
3. Express the view: sector ETF for the clean beta, or the strongest-RS names inside the sector for concentrated conviction (`momentum-trend` staging on the singles). Pairs form (long leader sector / short laggard) removes market direction (`pairs-relative-value` gates apply). Before recommending fresh entries, establish the current `market-health` gate (run its quick dashboard if not already known this session) and name it in the Call; a REDUCE_ONLY tape caps fresh-entry recommendations.
4. **The narrative-lag warning:** sector stories peak *after* the move — by the time the "great rotation into X" thinkpieces cluster, months of the RS move are spent. Dated news searches show when that clustering started.

## No-edge honesty

Day-trading sector ETF reversals and front-running scheduled rebalances are no-edge zones. The retail-viable seat is riding multi-quarter leadership with a falsifier, entering weeks (not minutes) into confirmation — the cost of confirmation is real but small next to the cost of buying a false turn.

End with **Call / Falsifier / Horizon** — the falsifier is an RS condition (e.g., "wrong if the sector drops out of the top 4 by 3-month RS" or a named macro reversal), horizon in weeks-to-quarters.
