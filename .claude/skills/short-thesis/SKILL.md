---
name: short-thesis
description: "Build and stress-test a short case: overvaluation forensics, the catalyst requirement, squeeze-risk gating (short interest, borrow, float), and structure selection (puts vs borrow). Use when asked whether to short a stock, evaluate an overvalued name, analyze a potential fraud or broken growth story, or vet an existing short position. Trigger: `use short skill`."
---

# Short Thesis

Shared plumbing and output contract: [../\_shared/analyst-core.md](../_shared/analyst-core.md). Shorting has inverted math (losses unbounded, winners shrink as they work, position grows against you when wrong) — so a short thesis needs *more* than a mirrored long: it needs a **reason**, a **catalyst**, and a **squeeze gate**. Overvaluation alone is none of these.

## The three-legged test — all three or no short

**1. The reason (why it's wrong, not just rich).** The durable short archetypes, roughly in order of reliability:
- **Fading fundamentals dressed as growth** — the forensic cluster from `fundamental-forensics` (run it; it's the evidence engine for this skill): revenue >30% with CFO/NI <0.5 for 2+ years, DSO rising, receivables outgrowing revenue.
- **Quadratic cost structures** (Chanos): the model only works if customer acquisition scales geometrically while unit economics never close — growth *is* the liability.
- **Broken cyclical still priced as secular** — the three-peaks logic: momentum peak, then price peak, then profit peak; the short window is after the price peak while consensus still extrapolates the profit line. Run the EPS sensitivity (revenue ≈ P×Q on a fixed cost base) to show what a 30% ASP giveback does to consensus.
- **Structural obsolescence with a levered balance sheet** — the debt turns a slow decline into an event (refinancing wall = your catalyst, check maturities via `xbrl_fact_trends`/filings).
- Pure valuation shorts ("it's at 40× sales") are the weakest class — they require the multiple to compress *on schedule*, which is a timing bet with no timer.

**2. The catalyst.** "Being early is being wrong" is the short seller's first law — overvalued names can double while you wait, and the borrow bill runs the whole time. Catalysts that qualify: refinancing wall inside 12–18 months, covenant proximity, lockup expiry (supply), guidance that can't be walked up, auditor/CFO departure, index deletion, regulatory decision with a date. Check `filing_timeline`, `equity_overview` (earnings dates), lockup terms via `web`. No catalyst inside the horizon → the honest output is "right thesis, no trade yet — here are the tripwires to watch" (and write them into the plan file as watch items).

**3. The squeeze gate — mechanical, non-negotiable.** Pull short interest / days-to-cover (`hf_tool.py quote SYM`), float (`equity_overview`), borrow-fee context (`web` — borrow fees are web-only in this stack), and insider/institutional concentration (`institutional_holders`). **SI > ~20% of float, high borrow fee, small float, or an options-active retail crowd → naked borrow is disqualified.** GME-class squeezes are gamma + forced-cover cascades; being fundamentally right didn't save anyone mid-squeeze. Crowdedness also means the thesis is consensus among shorts — the easy leg is done.

## Structure selection

- **Default for retail: defined-risk puts / put spreads**, not borrow. Costs are explicit (premium + IV), max loss known, no recall risk, no unlimited tail. Buy time generously — expiry at least 2× the distance from today to the catalyst — because early-and-right still loses on short-dated puts. Check IV first (`options-strategist`): post-collapse IV can make puts price in the rest of the decline already.
- Borrow-based shorts only for liquid large caps with modest SI and cheap borrow — and even then size at half a long's risk budget: the position moves against you by growing.
- **Shorts are trading positions, not investments.** Cover into capitulation; a working short's expected further gain shrinks while its squeeze tail doesn't. Pre-write the cover levels.
- Pair construction (short the weak name vs long the strong peer, `pairs-relative-value`) isolates the idiosyncratic leg when the sector direction is the risk.

## Honesty items

- Competing on *fraud discovery* against dedicated forensic shops with subpoena-adjacent resources is not the retail edge; the retail edge is **patience on already-visible deterioration** the market is still discounting slowly (PEAD works downward too — see `earnings-play`).
- Never short a momentum regime on valuation (2020's lesson); check `momentum-trend` staging first — Stage 2 names are disqualified as shorts regardless of multiple. The short window opens at trend break (Stage 3→4), not at peak absurdity.
- Report the cost of being wrong in dollars *and* the cost of being early in months of theta/borrow.

End with **Call / Falsifier / Horizon** — a short's falsifier must include the squeeze/crowding condition and a "thesis-confirming but position-killing" scenario (right and squeezed anyway), which is precisely what the structure choice must survive.
