---
name: fundamental-forensics
description: "Earnings-quality forensics on a stock: accruals analysis, cash-flow-vs-earnings divergence, pre-restatement red-flag clusters (rising DSO, auditor churn, related-party revenue), Beneish/Piotroski-style scoring from live XBRL data. Use when asked whether earnings are real, whether a cheap stock is a value trap, to vet a holding's accounting, or before trusting any fundamental thesis. Trigger: `use forensics skill`."
---

# Fundamental Forensics

Shared plumbing, integrity rules, and output contract: [../\_shared/analyst-core.md](../_shared/analyst-core.md). This skill answers one question: **are the reported earnings real, and is the market about to find out otherwise?**

## Why this beats reading the income statement

Reported EPS is the single most managed number in markets. The documented anomalies all live in the gap between earnings and cash: Sloan (1996) found top-decile-accrual firms underperform bottom-decile by ~10% over the next year; Dechow's AAER work shows restatement firms cluster on the same handful of precursors years in advance. A smart agent's edge here is that the inputs are free (XBRL) and most market participants still don't look.

## The workflow

1. **Pull 8–12 quarters of the core facts** via `sec xbrl_fact_trends` (exact XBRL names; dedupe restatements by period-end): `NetIncomeLoss`, `NetCashProvidedByUsedInOperatingActivities`, `AccountsReceivableNetCurrent`, `Revenues` (or `RevenueFromContractWithCustomerExcludingAssessedTax`), `InventoryNet`, `Assets`, `PaymentsToAcquirePropertyPlantAndEquipment`. Cross-check headline figures against `yahoo equity_overview`.
2. **Compute the diagnostics** (in Python from the pulled JSON, not by eyeball):
   - **Cash conversion:** CFO ÷ NI, trailing 4q. **< 0.8 sustained over ~3 years is the classic pre-restatement cluster** (Dechow et al. 2011) — especially paired with rising DSO.
   - **Total accruals / assets** = (NI − CFO) ÷ avg assets. Sustained > ~5% is the Sloan red zone. Split working-capital accruals from long-term/investment accruals (capex, acquisitions) — Richardson et al. (2005): the long-term kind predicts underperformance harder.
   - **DSO trend** = AR ÷ (revenue/91). Rising DSO while revenue accelerates = revenue being pulled forward (channel stuffing signature). Same logic for inventory days on product companies.
   - **Growth-vs-cash test:** revenue growth > 30% with CFO/NI < 0.5 for 2+ years is the canonical blow-up profile (this exact pattern preceded most famous frauds).
   - **NI-vs-OpInc bridge:** if net income grows faster than operating income, pull the non-operating lines (`InvestmentIncomeInterest`, `OtherNonoperatingIncomeExpense`) and attribute the gap — interest on a cash pile is real income but not operating leverage, and a thesis priced off the NI line inherits the rate cycle.
3. **Read the qualitative tripwires** via `sec filing_timeline` + `filing_diff` on the last two 10-Ks: auditor change, new related-party disclosures (> ~5% of revenue is serious), CFO departure, changes in revenue-recognition language, growing "unbilled receivables." `filing_diff` on the risk-factors section is the cheap way to catch what management's lawyers just added.
4. **Check who's acting on it:** `sec insider_activity` (are officers selling into the growth story?) and short interest context (`yahoo equity_screen screen_name=most_shorted_stocks`, `equity_overview`).
5. **For cheap stocks specifically**, run the Piotroski F-Score logic (9 binary points: profitability, leverage/liquidity direction, efficiency) — but only after confirming cheapness (bottom-of-range P/B or EV/EBITDA vs the name's own history and sector); Piotroski's spread lives inside the cheap bucket, and F-scoring a richly valued name proves nothing. Piotroski (2000): high-F cheap stocks beat low-F cheap stocks by ~7.5%/yr in-sample. The point isn't the score — it's that **cheap + deteriorating = trap, cheap + improving = candidate.** Never let "it's cheap on P/E" stand alone.

## Reading the result

- One flag is noise; forensic signal is a **cluster** (e.g., CFO/NI fading + DSO rising + auditor churn). Say explicitly how many independent flags fired out of those checked.
- Sector-adjust before flagging: SaaS deferred revenue makes CFO/NI look great (check billings instead); financials and REITs break accrual math entirely — say so and use sector-native metrics (or decline the framework).
- A clean forensic pass is a real, reportable result: it upgrades any bull thesis. A dirty pass doesn't auto-generate a short — overvalued-and-managed can stay bid for years; hand a short idea to `short-thesis`, which adds the catalyst and squeeze-risk gates.
- Where retail has edge: these signals play out over quarters, not minutes — exactly the user's horizon. Where it doesn't: trading the restatement headline itself.

End with **Call / Falsifier / Horizon** per the core contract — the falsifier here is usually the next 10-Q's cash-conversion print.
