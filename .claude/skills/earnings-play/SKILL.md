---
name: earnings-play
description: "Earnings-event analysis: implied move vs the stock's own realized earnings-move history, vol-crush economics, hold-through-vs-trade-around decisions, and post-earnings drift (PEAD) — the one earnings edge retail can actually harvest. Use when asked how to play an upcoming earnings report, whether to hold a position through earnings, or what to do after a big earnings gap. Trigger: `use earnings skill`."
---

# Earnings Play

Shared plumbing and output contract: [../\_shared/analyst-core.md](../_shared/analyst-core.md). Earnings is where retail loses money by trading the *event* and where the documented edge is in the *aftermath*. Keep those separate — and branch first on where the print sits (`hf_tool.py earnings SYM`): if it's ahead, run the implied-vs-realized workbench; if it already happened, skip straight to PEAD.

## Before the print: the implied-vs-realized workbench

1. **Get the date and the implied move.** `yahoo equity_overview symbol=SYM` (or `hf_tool.py earnings`) for the earnings date; `options_chain` for the expiry just after it. Implied move ≈ ATM straddle price ÷ spot (use mid here; both legs). Report it as a %. If no expiry just after the event is listed yet, strip the event variance from the term structure: total ATM variance (σ²T) of the nearest expiry containing the event minus that of the last expiry before it — the difference is the event's implied variance; label the derived move as term-structure-derived.
2. **Build the realized history — never skip this.** Pull `prices SYM --period 3y --out FILE`, find the last 8+ earnings dates (`hf_tool.py earnings SYM` / equity_overview / web for the dates), and compute the actual close-to-next-open and close-to-next-close moves. The comparison of *this straddle* vs *this stock's own history* is the entire pre-event edge, and almost nobody retail computes it.
3. **The base rate:** roughly 70% of realized earnings moves come in under the implied move (CBOE/sell-side studies — cite as base rate, varies by regime and name). That's why systematically *buying* the pre-earnings straddle loses, and why selling it isn't free either: the 30% that exceed include the 3× overshoots that dominate expectancy. Gap risk is not diversifiable within one name.
4. **Vol-crush mechanics:** front-expiry IV typically drops 30–50% at the open after the print. Every long-options position held through earnings pays this toll — a long call can be right on direction and still lose. If the view is "big move coming," the clean expression is buying vol **weeks before** the event hump inflates and exiting **into** the print, not through it (see `options-strategist`).

Decision rules: sell the event premium only with defined risk (iron fly/condor), sized so the 3× tail is survivable, and only when the straddle is rich vs the name's own history. Buy the event only with a genuine variant view on *magnitude* (not just direction) — "I think they beat" is priced; "the market is pricing a ±5% move on a binary that's historically ±12%" is a trade.

**Hold-through decision for stock positions:** the question is not "will they beat" (coin-flip on the reaction even when they do) but whether the position survives the implied move against you. If a straddle-sized adverse gap would force a panic exit, the position is oversized for the event — trim before, or pre-commit via the trading-plan invalidation list.

## After the print: PEAD, the retail-legal edge

Post-earnings-announcement drift is the oldest documented anomaly in accounting research (Ball & Brown 1968; Bernard & Thomas 1989): stocks with the biggest positive earnings surprises keep drifting up ~2–4% over the following ~60 trading days, and vice versa. Weaker in mega-caps, stronger in small/mid. Crucially, **the entry window is days 2–20, not minute 1** — retail's seat is fine here because the edge is slow diffusion, not speed.

Qualifying a drift candidate (data: `equity_overview` for surprise/revisions, `yahoo news_search`, `technical_snapshot`, the print-day price/volume from `prices`):

- **Surprise quality > surprise size:** revenue beat + raised guidance + margin beat drifts; EPS-only beats from a tax line or buyback don't. Guidance revision is the strongest single input — analyst estimates chase it for weeks (that lag *is* the drift).
- **Day-1 confirmation:** the drift signal is a big surprise *plus* a big same-direction day-1 reaction on heavy volume. A beat that gets sold on day 1 is the market telling you the whisper was higher — do not fade that reaction ("it beat, why is it down, must be cheap" is the classic PEAD-in-reverse trap).
- **Gap-and-crap filter:** entry on day 2–5 pullbacks toward the top of the gap, not into the day-1 spike; falsifier is a close back inside the pre-earnings range (gap fill = drift thesis dead).
- Short-side PEAD (missed + guided down + broke down) drifts too and is usually cleaner via put spreads than borrow (see `short-thesis` for squeeze gates).

**No-edge honesty:** the first minutes/hours after the release are HFT territory; reacting to the headline number in real time has zero edge from a retail seat, and by day 1's close the *obvious* read is priced. The drift edge is specifically in the market's slow adjustment to *magnitude* — that's what the days-2–20 window harvests.

End with **Call / Falsifier / Horizon** — for pre-event trades the horizon is the event itself; for PEAD entries it's the ~60-trading-day drift window with the gap-fill falsifier.
