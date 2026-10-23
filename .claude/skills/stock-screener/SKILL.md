---
name: stock-screener
description: "Thesis-driven stock screening: every screen must name the mispricing hypothesis it hunts and who's on the other side, then funnel candidates through quality/tradeability gates instead of dumping a list. Use when asked to find stocks matching criteria, generate ideas, screen for value/growth/momentum/short candidates, or turn a theme into names. Trigger: `use screener skill`."
---

# Stock Screener

Shared plumbing and output contract: [../\_shared/analyst-core.md](../_shared/analyst-core.md). A screen is a hypothesis about *why a group of stocks is systematically mispriced*, executed as a filter. A screen without that hypothesis is a list — and the failure mode of all public screening content — because every popular filter's output is visible to everyone running the same screener, so the raw list itself carries no edge. The edge is in the **hypothesis + the funnel behind the list**.

## Step 1 — Name the hypothesis (before touching a screener)

Force the one-sentence form: *"These stocks are cheap/misjudged because [mechanism], and the seller/avoider is [who], so the mispricing closes when [what]."* Examples that qualify:

- "Profitable small caps with insider-buying clusters are under-covered because no institution can size them; closes as results force coverage." (→ `small-cap-scout` + `event-driven` gates)
- "Post-guidance-raise names drift because analysts update in steps." (→ `earnings-play` PEAD funnel)
- "Cheap cyclicals near capitulation are avoided because last cycle's losses are recent memory; closes on the cycle turn." (→ `valuation-expectations` mid-cycle math)
- "High-FCF-yield + improving F-Score value names are lumped with value traps; the quality split is the edge." (Piotroski's actual finding — the *combination* is the screen)

If the user can't name the mechanism, help construct it — or say plainly the screen is a list, not an edge, and what would make it one.

## Step 2 — Execute (curated screens + SQL-style discipline)

`yahoo equity_screen` offers the curated set (`describe` for the enum): `undervalued_large_caps`, `undervalued_growth_stocks`, `growth_technology_stocks`, `small_cap_gainers`, `aggressive_small_caps`, `most_shorted_stocks`, `day_gainers/losers`, `most_actives`. These are *candidate feeds*, not answers — map the hypothesis to the nearest feed(s), pull generously (`limit=25`), and treat the day-based screens as flow/attention samplers rather than idea sources. For hypotheses the curated screens can't express, build the universe from other angles: sector ETF holdings (`fund_snapshot`), tickers named in theme news (`yahoo news_search`, `web`), insider-cluster names (`insider_activity`), and screen *those* with per-name pulls.

## Step 3 — The funnel (where the actual work happens)

Public screens fail at the funnel stage — they stop at the list. Run every candidate through, cheapest test first, kill fast:

1. **Tradeability:** ADV/spread gate from `small-cap-scout` for anything small; skip untradeable "bargains" immediately.
2. **Staleness check:** screener data lags — verify the load-bearing metric live (`equity_overview`, `quote_snapshot`) before it survives. A "12 P/E" that's actually 18 after last week's guidance cut is a data artifact, not a candidate.
3. **The trap filter matched to the screen type:** value screens → `fundamental-forensics` (cheap+deteriorating is the default state of a value screen's output — Piotroski's insight is that this filter *is* the strategy); growth screens → expectations math (`valuation-expectations`: what does the price already assume?); momentum screens → staging and extension checks (`momentum-trend`); short screens → squeeze gates (`short-thesis`).
4. **The differentiator question, per survivor:** *what do I know about this name that the screen doesn't?* One paragraph per finalist — catalyst, insider activity, recent news (`yahoo news_search`), sector tide (`sector-rotation`). Names with no answer stay on a watchlist, not a buy list.

Output shape: hypothesis restated → feed(s) used → funnel kill-count at each stage (e.g. "25 → 11 tradeable → 6 verified → 3 pass forensics → 2 with a differentiator") → finalists with one-line theses. The kill-count line is mandatory — it shows the work and calibrates how selective the funnel actually was.

## Honesty rules

- **Survivorship humility:** screens tested on today's members of an index inherit survivorship bias; historical "this screen returned X%" claims from screener sites are usually in-sample and cost-free — label them.
- **Factor screens are factor bets:** a value screen's output moves together; ten finalists from one screen are one trade, diversified in name only (see `portfolio-review` correlated-bets test).
- Screening is idea *generation* — nothing from a screen is buyable without the funnel, and the finalists still route through `trading-plan` for sizing and entry. Before recommending finalists as fresh entries, establish the current `market-health` gate (run its quick dashboard if not already known this session) and name it in the Call; a REDUCE_ONLY tape caps fresh-entry recommendations.

End with **Call / Falsifier / Horizon** per finalist (compact form is fine) — the falsifier is per-name, but also state the screen-level one: the condition under which the whole hypothesis is wrong.
