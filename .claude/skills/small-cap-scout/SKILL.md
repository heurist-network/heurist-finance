---
name: small-cap-scout
description: "Small- and micro-cap analysis where liquidity is the first risk: ADV-based tradeability gates, spread-tax arithmetic, pump/manipulation red flags, and the quality filters that separate the real small-cap premium from the junk that eats it. Use when asked to evaluate a small-cap idea, screen for small caps, or vet a low-priced/low-volume stock. Trigger: `use smallcap skill`."
---

# Small-Cap Scout

Shared plumbing and output contract: [../\_shared/analyst-core.md](../_shared/analyst-core.md). Small caps are where retail's structural *advantage* lives (institutions can't buy what won't absorb their size) and where retail gets *hunted* (illiquidity, promotion, information vacuum). The skill is running the tradeability and integrity gates **before** falling in love with the story — in that order, because the story is always good; that's what promotions are for.

## Gate 1 — Tradeability arithmetic (before any analysis)

From `quote_snapshot` + `prices SYM --period 6mo --full --out FILE` compute average daily dollar volume (ADV) and typical spread:

- **Spread tax:** names under ~$1M ADV cost 1–3% round trip in spread and slippage. Annualized over the user's multi-week turnover, any thesis must clear that hurdle *before* having edge. State the number.
- **Position-vs-ADV rule:** intended position ≤ ~1–5% of ADV, sized so a **3-day exit** without moving price >1–2% is realistic. The Amihud illiquidity premium (~0.5–1%/month in-sample) is real but non-linear — the bottom liquidity decile is where the premium lives *and* where retail size can't actually enter and exit; owning it on paper and capturing it are different things.
- **Exit stress test:** what does getting out look like on the worst day (halt reopens, guidance cut)? If the answer is "I'm trapped," the position size is the problem even when the thesis is right.

## Gate 2 — Integrity screen (is this a business or a promotion?)

The microcap manipulation profile is well-defined — check all of these (`equity_overview`, `insider_activity`, `filing_timeline`, `web` for promotion history):

- **The pump signature:** < $300M cap + < $5M daily volume + recent +100% move on no filing-linked news + paid-promotion trail (stock "newsletters," X spam) → halt/manipulation risk dominates any thesis; decline the name and say why.
- **Dilution machine check:** history of shelf offerings, convertibles, warrants (S-1/S-3/424B in `filing_timeline`; share count trend via `xbrl_fact_trends`). A company that funds operations by printing shares transfers your upside to itself — cash runway < 4 quarters makes the next offering *your* event risk.
- Reverse-split history, auditor tier, going-concern language, insider selling into strength, and float held by insiders (small real float = squeeze/rug both ways).
- Sub-$50M-float runners after +100%: you are the exit liquidity for insiders; hard pass regardless of narrative.

## Gate 3 — Quality (the part that actually earns the premium)

The naive size premium is weak and confounded — small-cap outperformance concentrates in **profitable, non-distressed** small caps (the Fama-French size effect strengthens dramatically after controlling for quality/profitability). So screen like Piotroski, not like a lottery-ticket buyer:

- Feed candidates from `equity_screen` (`small_cap_gainers`, `aggressive_small_caps`, `undervalued_growth_stocks`) or a thesis-driven list, then demand: positive and improving CFO, F-Score-style trajectory (run `fundamental-forensics` — it matters *more* here, where audit scrutiny and analyst coverage are thin), insider *buying* clusters (strongest in small caps — `event-driven`), and a real product/customer base verifiable outside company PR (`web`, `yahoo news_search`).
- **The information vacuum is the edge:** zero analyst coverage means the price can be wrong for a long time in either direction. Primary-source work (filings, customer checks, industry sources via web) is proportionally more valuable than in large caps — this is the one arena where retail doing homework is *structurally* ahead of institutions that can't justify the position size.
- Binary-catalyst names (biotech FDA dates) are a different game: position = lottery-ticket sizing or defined-risk options only, and competing with specialist desks on trial handicapping is a no-edge zone — say so.
- Before recommending fresh entries, establish the current `market-health` gate (run its quick dashboard if not already known this session) and name it in the Call; a REDUCE_ONLY tape caps fresh-entry recommendations — small caps most of all, since they fall hardest in distribution phases.

## No-edge honesty

Day-trading microcap momentum against promoters and their bots; front-running "hidden gem" screens whose output everyone with the same screener sees; buying illiquidity you can't exit. The durable retail seat: **quality small caps with insider buying, real cash generation, and a liquidity plan, held on the multi-week-to-multi-month clock** while the information vacuum closes.

End with **Call / Falsifier / Horizon** — and in small caps the call must include the position-size ceiling implied by ADV, because here size *is* part of the call.
