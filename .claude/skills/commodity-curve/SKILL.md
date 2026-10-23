---
name: commodity-curve
description: "Commodity analysis built on the futures curve: contango/backwardation and roll yield, COT positioning extremes, seasonality with decade-drift honesty, real-rates linkage for gold, and instrument selection (futures ETF roll bleed). Use when asked to analyze oil, gold, natgas, grains, or any commodity trade, or to vet a commodity ETF holding. Trigger: `use commodity skill`."
---

# Commodity Curve

Shared plumbing and output contract: [../\_shared/analyst-core.md](../_shared/analyst-core.md). Equities pay you for holding; commodities pay (or charge) you for *rolling*. Every commodity call starts at the curve, because a correct spot view can still lose money to carry — the single most common retail commodity error.

## Curve first, always

Pull the front contract and 2–4 deferred months: `yahoo quote_snapshot`/`prices` on `CL=F` plus specific months (`CLZ26.NYM` style); spot-check via `market_overview market=COMMODITIES`. Compute **annualized roll yield** = (front − deferred) ÷ front × (12 ÷ months between), and state the regime:

- **Backwardation** (front > deferred): scarcity now; long positions *earn* the roll. Gorton & Rouwenhorst's long-run futures work associates backwardation regimes with positive excess returns — the curve is itself a signal, not just a cost.
- **Contango** (front < deferred): storage economics; long positions *pay* the roll. Steep contango (>~10–12% annualized) has fully consumed correct directional theses — the USO 2020 case (right that oil recovers, −60% anyway via roll bleed) is the canonical lesson; cite it when a user wants long exposure in steep contango.
- The trade must clear the carry: expected spot move minus roll cost over the holding period. Write that arithmetic out. In steep contango, the honest expressions are deferred contracts, producer equities (which own the curve), or call spreads — not the front-month tracker.

**Instrument audit for ETFs:** `fund_snapshot` + the fund's roll methodology (`web`). Front-month rollers (USO-style) bleed in contango; equity proxies (XLE, GDX) add equity beta and management factors — say which risk the user is actually buying.

## Positioning, seasonality, and the macro leg

- **COT as a crowding flag, not a timer.** Managed-money net positioning from the CFTC's weekly Commitments of Traders report — the workable source is cftc.gov's Disaggregated COT (or Tradingster/Barchart mirrors) via `web`; disambiguate the contract (WTI positioning lives on NYMEX, Brent on ICE — name which report you pulled). If a current reading can't be pinned down, "COT unavailable this run" is the expected fallback: flag it, don't fabricate a percentile. >~90th percentile of its 3-year range flags washout vulnerability: forward returns from crowded-long extremes show negative skew. Use it to veto adding to crowded trades and to size down, never as a standalone reversal signal — extremes persist.
- **Seasonality: real but decaying, decade-drift applies.** Natgas withdrawal season (Nov–Mar) genuinely structures vol and storage math; ag planting/harvest cycles are physical. But specific calendar patterns ("buy corn in February") drift by decade and are partly folklore — check the claimed pattern against the last 10–15 years from `prices` before citing it, and label the sample size.
- **Gold is a real-rates trade wearing a commodity costume.** Post-2003 correlation with 10y TIPS yields ≈ −0.4 to −0.6; a +100bps real-rate shock has historically pressured gold 15–25% over 6–12 months (label: regularity, not law — central-bank buying regimes weaken it, as post-2022 showed). Pull real rates via `fred macro_series_history`; a gold view without a real-rates and dollar view is incomplete (see `macro-regime`).
- **Supply/demand work is where the fundamental edge lives:** inventories (EIA weekly for energy via `web`), production discipline, demand proxies. News (`yahoo news_search`, `web`) tracks the narrative; the curve tells you how much of it is priced — backwardation *is* the market saying "shortage now."

## No-edge honesty

USDA/EIA/OPEC headline reactions are algo territory — no retail seat in the first minutes. Physical/storage arb is institutional (April 2020's negative WTI was a storage-economics event, not a chart pattern). The retail-viable seat: multi-week curve-aware directional and relative trades (producer vs commodity, deferred-month positioning, seasonal vol structure) where the edge is doing the carry arithmetic most participants skip.

End with **Call / Falsifier / Horizon** — the falsifier should include a curve condition (e.g., "wrong if the curve flips to contango — the shortage thesis is then dead by definition"), because the curve is the thesis's own scoreboard.
