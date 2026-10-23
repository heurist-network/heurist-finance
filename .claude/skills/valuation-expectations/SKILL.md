---
name: valuation-expectations
description: "Expectations-based valuation: reverse-engineer what growth and margins the current price already implies, test those implied expectations against base rates, and locate the variant view. Use when asked if a stock is cheap/expensive, what's priced in, whether to buy after a big move, or to sanity-check a price target. Trigger: `use valuation skill`."
---

# Valuation Expectations

Shared plumbing and output contract: [../\_shared/analyst-core.md](../_shared/analyst-core.md). This skill runs valuation **backwards** — from price to implied expectations — because that's the only direction that produces a trade.

## The core move

A DCF that outputs "fair value $147" is an opinion wearing a spreadsheet. The expectations-investing move (Rappaport & Mauboussin) inverts it: hold the discount rate and terminal assumptions fixed, and solve for **what revenue growth / operating margin path makes today's price fair.** Then ask one question: *is that path plausible against base rates?* The trade exists only where implied expectations and plausible outcomes diverge.

Workflow:

1. **Pull the inputs:** `yahoo equity_overview symbol=SYM` (price, market cap, forward estimates, analyst consensus), `sec xbrl_fact_trends` for the actual revenue/margin/FCF history (8–12 quarters + 5 annual), share count and net debt from the same. Cross-check any scraped estimate against equity_overview — scraped consensus numbers are frequently stale.
2. **Solve for implied expectations** with a small Python script (write it, don't estimate): a simple 10-yr FCF model at an 8–10% discount rate, terminal growth 2–3%. Anchor on TTM FCF built from the XBRL pulls — trailing-4q CFO minus trailing-4q capex (difference fiscal-YTD values where needed) — never a scraped "FCF" field on faith. Match PV to **enterprise value** (market cap + net debt) when the FCF is pre-financing firm FCF; match market cap only when modeling equity FCF — say which you used. The canonical solve is two-stage: take consensus estimates for years 1–2 as given (`equity_overview`) and solve for the growth the years 3–10 tail must deliver; quote the flat-CAGR solve alongside as the simple read (flat understates what's priced when near-term growth is front-loaded). Report the sentence: *"At $X, the market is paying for ~Y% revenue CAGR at Z% operating margins for a decade."*
3. **Test against base rates.** The reference-class question beats the inside view. Anchors from the base-rate literature (Mauboussin's corporate base-rate work): sustained 20%+ revenue CAGR over 10 years is achieved by roughly the top ~1–2% of companies; double-digit CAGR for a decade is roughly top decile, and the odds fall hard with starting revenue size ($10B+ companies almost never compound revenue >20% for 10 years). Margin expansion assumptions should be tested against the best margin the company — or its best-in-class peer — has *ever* printed.
4. **Locate the variant view.** State explicitly which implied assumption you disagree with, in which direction, and why you know something the consensus doesn't (structural change, misread cycle, forced sellers). No variant view → no trade, whatever the multiple says.

## Multiple-based cross-checks (fast path)

For a quick read, multiples work if you translate them into expectations rather than compare them to the sector average:

- **P/S is a margin assumption in disguise.** P/S of 15 at a 10% discount rate needs ~30%+ steady-state FCF margins on much larger revenue. Say the implied margin out loud.
- **P/E vs growth:** compare to the company's own 5–10yr multiple range (from `prices` history + EPS trend) before peers. A "cheap vs peers" stock in a structurally worse seat is correctly cheap.
- **Cyclicals: never multiply peak.** Low P/E on peak earnings is the most expensive look a cyclical ever has. Use mid-cycle earnings (average margin over a full cycle × current revenue) or P/B vs ROE history. The three-peaks ordering from `trading-plan` applies: momentum peak → price peak → profit peak, quarters apart.
- **SOTP only with a separation catalyst.** Sum-of-the-parts on a company that will never separate the parts is a permanent "discount" — consensus models on covered mega-caps already embed it.

## Failure modes

- **Precision theater:** reporting $147.23 from a model whose growth input is a guess. Report ranges keyed to scenarios, and label judgment as judgment.
- **Discount-rate laundering:** any stock is "cheap" at 7% and "expensive" at 11%. Fix the rate, argue about cash flows.
- **Cheapness as thesis:** cheap + deteriorating quality is the value-trap signature — run `fundamental-forensics` before trusting any low multiple; a variant view on a fraud is just being early to zero.
- Valuation alone has weak multi-week timing power. It sets asymmetry, not the entry — pair with `momentum-trend` or a catalyst from `event-driven` for the when.

End with **Call / Falsifier / Horizon**. The falsifier is usually the implied-expectation line: "wrong if the company actually delivers/keeps missing X% growth" — plus the nearest checkpoint (guidance, next print).
