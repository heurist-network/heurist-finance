---
name: options-strategist
description: "Map a market view to the right options structure: direction × magnitude × timing × IV regime → specific structure with strikes, expiry, and management rules. Use when asked which options strategy fits a thesis, whether to buy or sell premium, to compare structures (spread vs outright, calendar vs vertical), or to critique a proposed options trade. Trigger: `use options skill`."
---

# Options Strategist

Shared plumbing and output contract: [../\_shared/analyst-core.md](../_shared/analyst-core.md). Options math conventions (price from **bid** on anything sold, report IV/OI/volume/spread per strike) and the coherence test live in `trading-plan` — this skill picks the *structure*; trading-plan sizes and commits it. Public options content is Greeks calculators and "17 strategies" catalogs; the actual skill is the mapping from **view → structure**, which is what this file encodes.

## Step 1 — Make the view explicit on four axes

No structure choice is possible until the view is stated as: **direction** (up / down / flat / "not down"), **magnitude** (drift vs repricing — is the move bigger or smaller than what's priced?), **deadline** (is there a date by which it must happen, or is it open-ended?), and **conviction on timing vs level**. State also whether this is a new position or an overlay on stock already held — for an income overlay (covered calls on an existing holding), the axes apply to the *combined* position (stock + short call), not the option leg alone. Most bad options trades are a correct directional view expressed on the wrong axis — long calls for a view with no deadline, short puts for a view with a crash tail.

## Step 2 — Read the vol surface before choosing

- **IV Rank** (current IV vs its own 52-week range — no IV history in this stack, so proxy with the current ATM IV's percentile vs 1y realized-vol history per the core convention, labeled as proxy): IVR > 50 tilts toward net-selling structures, IVR < 20 toward net-buying. Per-strike IV and BS delta come from `hf_tool.py options SYM --expiry ...`. But rank alone is the public-content trap —
- **Term structure decides the rest:** loop `yahoo options_chain symbol=SYM expiration=... moneyness=atm limit_contracts=6` across expirations and read ATM IV per expiry. Contango (front < back) is the normal state and a mild short-front tailwind; **an event hump** (one expiry's IV spiked) means an earnings/catalyst date lives there — check `equity_overview` for the earnings date and never sell that expiry "for the juicy premium" without pricing the gap (see `earnings-play`).
- **Implied vs realized spread:** implied minus 20d/60d realized vol is the actual premium being paid. Selling options at IV below realized is picking up nickels at a discount.

## Step 3 — The mapping

| View | IV regime | Structure | Why |
|---|---|---|---|
| Directional, deadline, expect repricing > implied move | low/any | Long call/put or debit vertical | Paying for convexity is right when the move beats what's priced |
| Directional drift, no hard deadline | high | Short put / credit spread (bull) or call credit spread (bear) | Get paid for time; deadline-free views shouldn't pay theta |
| Directional, but IV high and move size uncertain | high | Debit spread over outright | Spread sells back the inflated wing |
| "Not down" / accumulate-lower | high | Cash-secured short put at a strike you'd own | Only coherent if assignment is genuinely wanted (coherence test) |
| Flat / range | IVR > 50 | Iron condor / short strangle (defined-risk unless account is sized for tails) | Selling range needs paid vol AND no event inside DTE |
| Big move, direction unknown, before catalyst | IV *below* its event-normal | Long straddle/strangle bought weeks early | Buy vol before the hump inflates, exit into it — never hold through the print by default |
| Own stock, expect chop | any | Covered call above resistance | Capped right tail is a real cost — price it, don't call it "free income" |
| Long-dated conviction | low front, flat term | LEAPs / deep ITM (70+Δ) as stock substitute | Delta exposure with defined risk; check the 3rd-Friday dates directly (chain listing truncates) |

Practitioner management heuristics worth adopting (tastytrade-style mechanics — label them practitioner convention, not law): short premium around 16–30Δ at 30–60 DTE, take profits at ~50% of max credit, manage or close at ~21 DTE to dodge gamma; the published "~70% win rates" on these exclude the tail losses that dominate expectancy if unmanaged — say that out loud.

## Hard rules

- **Never sell naked premium in IVR < 20** — thin premium vs full gap risk is structurally negative expectancy (one 3σ gap erases the year).
- **Earnings inside the DTE changes everything.** Check the date first. If the thesis *is* the event, `earnings-play` rules govern; if a long-horizon drift thesis merely spans a print, it stays a drift trade — price the gap explicitly (strikes and size that survive the implied move) instead of reclassifying it as an earnings trade.
- **Liquidity gate:** OI < ~100 or bid-ask wider than ~10% of mid on a leg → pick another strike/expiry or another name; the fill and the exit eat the theoretical edge.
- **Coherence test on every leg** (from trading-plan): in the scenario where this leg executes, is the user holding what they wanted at that moment? A bull selling only their right tail via covered calls, or an income seller who'd hate assignment, fails it.
- Defined-risk max loss is still real money: report max loss in dollars, probability-weighted, next to the premium.

End with **Call / Falsifier / Horizon** — for options the falsifier includes a vol condition (e.g., "wrong if IV stays bid after the event") and the horizon equals the expiry structure by construction.
