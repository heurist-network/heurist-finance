---
name: dividend-income
description: "Income-equity analysis centered on yield-trap detection: free-cash-flow coverage, payout sustainability under stress, dividend-growth vs high-yield trade-offs, REIT/MLP-specific metrics, and total-return honesty. Use when asked to evaluate a dividend stock, build income from a portfolio, judge whether a high yield is safe, or compare income strategies (dividends vs covered calls vs bonds). Trigger: `use dividend skill`."
---

# Dividend Income

Shared plumbing and output contract: [../\_shared/analyst-core.md](../_shared/analyst-core.md). The organizing fact: **an unusually high yield is a price, not a gift** — the market charging admission to a risk it can see. The skill is determining whether the market is right (trap) or overshooting (opportunity), which is a cash-flow question, never a yield-screen question.

## The trap detector (run on any yield that catches the eye)

Data: `equity_overview` (yield, payout, history), `xbrl_fact_trends` for the real series — `PaymentsOfDividendsCommonStock`, CFO, capex (`PaymentsToAcquirePropertyPlantAndEquipment`), debt maturities; `prices` for the yield's own history.

1. **Coverage on free cash flow, not EPS.** FCF payout = dividends ÷ (CFO − capex). **< ~70% is comfortable; > 100% means the dividend is being borrowed.** EPS-based payout ratios hide it — EPS carries non-cash items and buyback-shrunk denominators. Compute trailing-4q and the 3-year trend; deteriorating coverage with a "committed" dividend is the pre-cut signature.
2. **Relative-yield alarm:** yield > ~2× its sector median, or > the company's own 10-year average by multiple points, is the market pricing a cut. The historical pattern: by the time a stressed payer finally cuts, the *stock* has already taken the damage — and often rallies on the cut (uncertainty resolved). So the trap isn't the cut; it's the ride down to it.
3. **Balance-sheet collision test:** debt maturities inside 24 months vs FCF after dividends. A dividend competing with a refinancing wall loses — check whether the credit market (bond yields via `web` if findable) already disagrees with the equity market's yield read.
4. **Cyclical peak-payout trap:** a commodity/cyclical yielding 8% on peak earnings is yielding 8% *of a number that's about to halve* — run coverage on mid-cycle FCF (see `valuation-expectations` on cyclical earnings). Variable-dividend policies (many energy names) are honest about this; fixed promises on cyclical cash flows are not.
5. **Sector-native metrics:** REITs — coverage on FFO/AFFO (via `web`/filings; GAAP EPS is meaningless under depreciation), plus lease duration vs rate environment. MLPs/midstream — distributable cash flow and incentive structures. BDCs/mortgage REITs — the double-digit yields are leveraged spread bets; label them as such, not "income."

## Choosing an income posture

- **Dividend growth beats high current yield for multi-year money:** the documented sweet spot in dividend investing is *growers with low payout ratios* (room to keep growing), not the top-yield decile — top-decile yield portfolios systematically underperform the second tier because they're loaded with pre-cut traps. A 2% yield growing 10%/yr passes a 6% static yield inside a decade, with less cut risk the whole way.
- **Dividend safety is a forensics question at the margin:** a payer whose earnings quality is deteriorating (`fundamental-forensics`) cuts sooner than its coverage ratio suggests — accruals hide cash stress until it hits the dividend line.
- **Total-return honesty:** the dividend is not free money detached from the stock (the price drops by the dividend on ex-date; "dividend capture" strategies are a documented no-edge zone after costs and tax). A falling stock yielding 6% is a losing position with a coupon. Judge the whole position.
- **Covered-call "income" comparison:** selling calls on holdings converts upside into cash flow — a real trade-off, not extra yield (see `options-strategist`, and the coherence test: a bull who caps their right tail is fighting themselves). Compare income postures on total expected return and tail shape, not headline yield.
- Income ETFs: `fund_snapshot` for what's actually inside — many high-yield ETFs are trap aggregators; expense ratio + top-decile-yield holdings is a double toll.

## No-edge honesty

Dividend information is fully public and slow — there is no timing edge in "buying before the ex-date" or reacting to declarations. The retail edge in income investing is **patience and trap avoidance**: institutions chase yield mandates into traps retail is free to skip, and the multi-year compounding of uncut, growing dividends needs no speed at all. That fits this user's seat exactly, but the horizon is quarters-to-years — say so when the user frames income names on a multi-day clock.

End with **Call / Falsifier / Horizon** — the falsifier for any income call is a coverage number (e.g., "wrong if FCF payout crosses 100% next quarter" / "cut risk repriced if coverage recovers above 80%"), because the dividend's fate is the thesis.
