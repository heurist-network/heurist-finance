---
name: sentiment-positioning
description: "Sentiment and positioning analysis: contrarian indicators with their real (small) effect sizes, crowding detection, insider clusters as the strongest signal, and the catalyst requirement for positioning unwinds. Use when asked if a trade is crowded, what sentiment says about the market, whether to fade euphoria/panic, or how to read put/call ratios, fund flows, or insider filings. Trigger: `use sentiment skill`."
---

# Sentiment & Positioning

Shared plumbing and output contract: [../\_shared/analyst-core.md](../_shared/analyst-core.md). Two distinct objects, one skill: **sentiment** (what people say/feel — weak, noisy contrarian value) and **positioning** (what they actually hold — stronger, because unwinding it forces flow). The unifying law: **crowding is a risk amplifier, not a timer.** Crowded stays crowded until a catalyst forces the unwind; sentiment extremes justify sizing and structure changes, rarely standalone entries.

## The indicator battery, with honest effect sizes

Pull via `web` (AAII, CBOE put/call, II survey, fund flows are all free/public), `insider_activity`, `institutional_holders`, `equity_screen screen_name=most_shorted_stocks`, VIX via `^VIX`, and news flow (`yahoo news_search`, `web`) for narrative temperature.

- **Insider buying clusters — the strongest item here** (open-market, 3+ insiders / 90 days, CEO+CFO within 30 days is the premium version; exclude 10b5-1 plans and exercises): ~4–6% abnormal 12-month returns documented (Lakonishok & Lee; Cohen, Malloy & Pomorski's "opportunistic vs routine" split). Insider *selling* is noise — asymmetry is structural. Full playbook in `event-driven`.
- **Equity-only put/call ratio** (10-day MA > ~1.0): historically coincides with above-average 30-day forward returns — a panic-washout marker. **Post-2020 caveat:** retail options flow and hedged structures have muddied it; single-name P/C is nearly uninterpretable (synthetic longs). Weak contrarian, index-level only.
- **AAII bulls or bears > 50%:** documented contrarian spread of only ~2–3% with many false positives (Fisher & Statman) — bull markets stay over-loved for quarters. Extreme *bearishness* at index level is the more reliable side (panic is sharper than euphoria).
- **Fund flows:** peak retail equity inflows precede below-median 1-year returns (Frazzini & Lamont, "Dumb Money") — a valuation-of-mood indicator on quarters, useless on weeks.
- **VIX regime:** level + term structure. Spot > 30 with inverted VIX futures curve = stress regime where forced deleveraging dominates fundamentals; VIX < 13 for months = complacency that makes hedges cheap (buy them then, not after). More signal in the *term structure flip* than the level.
- **Short interest:** high SI is double-edged — informed shorts predict underperformance on average, but SI > ~20% float + small float = squeeze fuel (see `short-thesis`). Days-to-cover contextualizes it.
- **Narrative temperature:** news frequency and tone on a theme over time (`yahoo news_search`, `web`) is a crude crowding proxy — when a theme dominates news flow for weeks and the marginal story adds no new facts, the marginal buyer is being recruited by narrative, not information.

## The decision framework

1. **Diagnose, then demand a catalyst.** Crowded-long + no catalyst = size down, tighten falsifiers, maybe buy cheap tail protection — *not* short it. Crowded-long + a dated catalyst that could disappoint (earnings, product event, macro print) = the actual fade setup, because disappointment forces the unwind flow.
2. **Positioning outranks sentiment on conflicts.** Surveyed bears who are fully invested are bulls; believe holdings (13F drift via `institutional_holders`, flows, SI), not mood surveys.
3. **Sentiment extremes work best as *filters* on other skills:** momentum entries into euphoric crowding get the size haircut; forensic shorts into max-pessimism get deferred (the easy leg is done); washout panic readings upgrade quality-name pullback buys (`technical-evidence` Tier 1 reversal).
4. **Contrarian-too-early is the failure mode** — 2020–21 growth crowding punished faders for a year. The protection is structural: express fades with defined risk (options), demand the catalyst, and let `position-sizing` cap the bet.

## No-edge honesty

X/Twitter velocity is the *slowest* feed in the market — by the time a theme trends, systematic desks have traded its derivatives; treat social buzz as a crowding thermometer, never as alpha. Composite "fear & greed" indices are entertainment-grade repackaging of the inputs above — use the raw inputs. And a sentiment read with no positioning confirmation and no catalyst is commentary; say so rather than dressing it as a signal.

End with **Call / Falsifier / Horizon** — sentiment-based falsifiers should name the *unwind evidence* (flows reversing, SI covering, narrative breaking) rather than a price level alone.
