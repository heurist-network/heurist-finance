---
name: event-driven
description: "Corporate-event playbooks with per-event honesty about where retail has edge: M&A arb, spinoffs, index adds/deletes, lockup expiries, insider buying clusters, buybacks, activist stakes. Use when asked how to trade a deal announcement, spinoff, index change, lockup, insider filing, or any discrete corporate event. Trigger: `use event skill`."
---

# Event-Driven

Shared plumbing and output contract: [../\_shared/analyst-core.md](../_shared/analyst-core.md). The governing fact — say it to the user when relevant: **most tradable-looking news carries no edge by the time retail reads it.** Liquid names price headlines in minutes. The events below are the exceptions, and each is an exception for a *structural* reason (forced flows, institutional constraints, slow diffusion) — when the reason doesn't apply, neither does the edge.

## Per-event playbooks

**M&A arbitrage.** Edge test first: the spread compensates for break risk, and the pros price legal/regulatory risk with counsel and scenario trees. Retail's viable corner is **small ($500M–$2B), simple, cash deals** — base rate: announced cash deals close at ~95%+ (Mitchell & Pulvino 2001); the annualized spread on a clean one is the price of break risk, not free money. Workflow: deal terms from `web` + the merger 8-K via `sec filing_timeline`; compute spread, annualize over expected close; check financing condition, regulatory overlap, and go-shop. **Skip:** horizontal deals with antitrust tails, stock-for-stock (you're implicitly short the acquirer), anything where the spread looks generous — the market knows something. Position asymmetry is brutal (earn the spread, lose the pre-deal gap), so size accordingly. Sourcing: no tool enumerates pending deals — build the candidate set iteratively via `web` queries (e.g. "pending all-cash acquisitions under $2B"), then verify each candidate's terms in the merger 8-K/proxy via `filing_timeline`.

**Spinoffs — the best structural edge on this list.** Parent+spinco outperform benchmarks by ~10–20% over 12–24 months in the classic studies (Cornell/Qiao and predecessors) because the selling is *forced*: index funds and mandate-constrained holders must dump a spinco that doesn't fit (too small, wrong sector, no dividend), regardless of price. The dislocation window is roughly **days 30–180 post-separation**. Workflow: Form 10 via `filing_timeline`; who's forced to sell (parent's index membership vs spinco's); insider/management incentives in the spinco (equity grants struck post-spin are a tell); let the forced selling exhaust (volume decay + base formation on `technical_snapshot`) before entering. Garbage-barge spinoffs (debt-stuffed liability dumps) exist — read the Form 10 balance sheet, don't buy "it's a spinoff" as a thesis.

**Index adds/deletes.** The announcement pop (~3–8% historically for S&P 500 adds) happens in minutes and the effective-date flow is fully arbed — **retail has no seat at this table**; say so. The residual plays: fading the post-inclusion hangover (adds tend to underperform after the flow completes), and deletion-driven overshoots in small caps where forced selling exceeds real float appetite — only with an independent fundamental view.

**Lockup expirations.** IPO lockup expiry days average −1 to −3% abnormal return (Brav & Gompers) — a known supply shock that still isn't fully priced because it's uncertain *how much* insiders sell. Tradable mostly as: don't *buy* into one, close shorts into the flush, and treat heavy insider selling at expiry as information only if valuation is stretched too. Dates via `web`/S-1 terms — and read the actual lockup terms rather than assuming one 180-day cliff: modern lockups are often staged (multiple tranche dates) or conditional (price-triggered early release, where strength itself unlocks supply); map each tranche date and trigger before calling the event's size.

**Insider buying clusters — the strongest cheap signal here.** Filter hard via `sec insider_activity`: **open-market buys** (never option exercises, never 10b5-1 plan purchases), **3+ distinct insiders within ~90 days**, ideally CEO+CFO, size meaningful vs their comp. That cluster carries ~4–6% abnormal return over 12 months (Lakonishok & Lee; Seyhun), strongest in small caps. Insider *selling* is mostly noise (comp, diversification) — asymmetry is the point. A cluster after a big decline in a name that passes `fundamental-forensics` is the setup.

**Activists.** `sec activist_watch` + 13D. The pop is on the filing (gone in minutes); the edge is the slow campaign: does the activist have a track record, a real lever (board seats, sale process), and an exit story? Multi-month horizon, and the coattail rides the *campaign milestones*, not the stake headline.

**Buybacks.** Authorization headlines are noise (many are never executed). Signal = actual share-count decline (`xbrl_fact_trends` on shares outstanding) + cheap valuation + insider buying alongside. A buyback at 30× funded by debt is capital destruction with good PR.

## Cross-event rules

- **Name the forced flow.** Every event trade should answer: *who is transacting for non-economic reasons, and am I on the other side of them?* No forced flow → it's just a news trade → no edge.
- **The calendar is the risk map:** deal votes, expiry dates, effective dates, court rulings. Build it explicitly (`macro_release_calendar` for macro overlaps, `equity_overview` for earnings collisions mid-event).
- Events stack with other skills: forensics on the spinco, valuation on the post-arb equity, options (`options-strategist`) when the event has a date and the vol surface hasn't noticed.

End with **Call / Falsifier / Horizon** — event falsifiers are usually calendar-anchored (deal breaks, lockup passes without flush, campaign stalls).
