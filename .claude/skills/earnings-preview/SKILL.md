---
name: earnings-preview
description: "Agent-swarm earnings preview for one company: five parallel research lanes, a bull/bear debate with a rebuttal round, an adversarial fact-check, a numbers-only baseline tested by a statistician, and a pre-registered verdict with probabilities that is committed before the print and scored after it. Use when asked to predict or preview an upcoming earnings report, call the stock and sector reaction, or check what a print means for the user's book. Trigger: `use earnings-preview skill`."
---

# Earnings Preview (agent swarm)

Shared plumbing and house rules: [../_shared/analyst-core.md](../_shared/analyst-core.md). Event mechanics (implied move, vol crush, post-earnings drift): [../earnings-play/SKILL.md](../earnings-play/SKILL.md). This skill is the orchestration layer: you are the orchestrator, subagents do the reading, and you own the verdict.

First run: META Q3 2026. The traps and rules below come from that run and are self-contained.

## Budget and shape

About 10 agents and 1-2 hours of wall time. Run independent agents in one message so they run concurrently, in the foreground when your next step needs all of them. Every agent writes its full report to a scratch file (`<scratchpad>/<ticker>/laneN-*.md`) and returns a structured summary with a source (URL or tool call) and a date on every number. Later agents read the files, so you never paste reports between agents.

## Phase 0: setup (you, about 5 minutes)

1. Read `profile.md`, `context/latest.md`, `context/index.md`, `trading/watches/` and any plan that names the ticker or its sector. Note what the user holds and which plan lines this print can trip.
2. Confirm the date and time of the report on the company's IR site, not an aggregator. Aggregator dates were wrong for INTC and META in this repo.
3. `hf_tool.py quote TICKER` and `hf_tool.py earnings TICKER` for spot and vendor EPS history. If vendors disagree on consensus by more than 5%, Lane 1 must explain why before anyone uses a number.
4. Write down the company's swing factor: what the market will actually trade on. META was 2027 capex and expense language; for GOOGL it is likely Cloud growth and backlog, the capex guide, and search revenue against AI substitution. Lane 2 is built around it.
5. **Write a blind estimate before any lane reports.** From the company's own guidance and its record against that guidance, put your number for each main line (revenue, the swing-factor line, next-quarter guide) in the scratch dir. Do not read consensus, previews or lane output first. This is the anchor the rest of the run has to argue against, not the Street.

## Phase 1: five research lanes (parallel, general-purpose agents)

Shared preamble for every lane: today's date; the training cutoff warning ("anything after mid-2026 comes from a tool call, never memory"); read `AGENTS.md` Market data and Primary evidence; use `hf_tool.py` plus WebSearch/WebFetch (load with ToolSearch `select:WebSearch,WebFetch`); every number gets a source and a date; mark unverified dates; save the full report to a scratch file; return at most about 1,000 words; do not edit repo files.

| Lane | Job | Must deliver |
|---|---|---|
| 1. Consensus and the print | Reconcile EPS and revenue consensus across vendors and explain the gaps (one-time charges, tax items, equity-investment gains). Read the last quarter's 8-K Ex.99.1 and 10-Q: guidance, segment numbers, legal and tax notes. Track the company's actuals against its own guidance or consensus for 8 quarters. | A "what a beat / in-line / miss looks like" table in numbers, ex-items and GAAP. |
| 2. The swing factor | Deep dive on the factor from Phase 0: guide history, the 10-Q notes (commitments, leases, joint ventures, guarantees), financing, Street numbers for next year, and management's exact words last quarter. | Base-case expectations for each guide line, with reasons. |
| 3. Demand and previews | Independent demand evidence: peers that already reported, channel checks, FX against what management assumed, sell-side previews (firm, date, number, key point). | An independent read on the top line with the evidence for and against. |
| 4. Options and reaction history | Implied move from the chain (straddle for the first expiry after the print, divided by spot); skew; realized day-1, 5-day and 20-day moves for the last 12 prints; which prints moved on guidance rather than results. | Implied against realized, and the reaction pattern by type of print. |
| 5. Read-through | Supplier and peer exposure; what the print means for every holding and plan line in the book; a scenario table of outcome against reaction for the stock, the sector ETF and the most sensitive names. Note any other mega-cap reporting the same evening, which confounds every historical read-through. | Scenario table with probabilities, and the plan lines at stake. |

Company-specific lanes are allowed (Alphabet: a Cloud/TPU lane; Microsoft: Azure and the OpenAI accounting). Keep the total at about five.

## Phase 2: debate and fact-check (parallel)

- **Bull and Bear** (two agents): each reads all lane files, builds the strongest honest case, predicts every line of the print, gives P(day-1 up or down) with an expected move, and lists the 2-3 points from the other side it cannot rebut.
- **Verifier** (one agent): tries to refute the 10-12 load-bearing claims from the lanes. It returns CONFIRMED / WRONG / UNVERIFIED with a source for each, a "must not use" list and a list of new facts. Recompute the implied move and the reaction history yourself from tool output; at META a secondary source said ±12.1% when the chain said ±7.2%.
- **Rebuttal round:** once the debaters return, use SendMessage to give each the other's file and ask them to rebut its three strongest points, concede what they can't, and give a final probability. Convergence shows which one or two variables decide the day. It is not confirmation: check whether both sides lean on the same input (a shared consensus number, a shared analog). If they do, that input gets verified before the verdict, because the debate counted it twice.

## Phase 3: numbers baseline and statistics

1. Build the outcome table (agent or you): per past print, the revenue surprise against the company's own guide midpoint where it guides (META) or against consensus where it doesn't (GOOGL gives no revenue guide), guide changes, and the day-1, 5-day and 20-day moves against QQQ.
2. **Price-data trap:** EODHD mixes an adjusted close with a raw open. That broke the overnight-gap and open-to-close columns twice in this repo. Use consistently adjusted bars (Yahoo OHLC) for any gap or open-based return. Close-to-close is safe.
3. **Adversarial statistician** (one agent): test every candidate rule (for example "revenue beat of 3.5% or more means an up day") with a cutoff sweep, a permutation p corrected for choosing the cutoff, a 2023-24 against 2025-26 holdout, leave-one-out, and controls for the numbers. Then the timing test, which decides tradability: does the rule predict the next open-to-close move, or only the after-hours gap? At META everything was in the gap.
4. Count the tests, compare the hits against a permutation null, and kill seasonal and "N of N" patterns (at META, "October calls fall 3 of 3" had p 0.125).

## Phase 4 (optional): language

The META study found no tradable language signal: dictionary tone, filing changes, XBRL tags, a regex non-answer rate and six pre-registered word-choice tests all failed or did not replicate at MSFT and GOOGL. An LLM-scored evasion metric failed its validity gate. So:

- **Use the language channel as a checklist, not a signal.** Have a close-read agent compare the last quarter's outlook paragraph and call with the one before it, word by word. List the pledge sentences the company repeats (META: "operating income above 2025"), what was dropped or added, and which questions were deflected. Each becomes a scorable item for tomorrow.
- **Look-ahead rule:** the model has read the company's history up to its training cutoff. Any backtest score must come from deterministic code, never from a model reading old calls.

## Phase 5: the verdict (you)

1. Write a table of 10-15 scorable items: each line of the print, each guide line, each pledge sentence, financing language, the day-1 direction for the stock, the next-day direction for the sector ETF, and the label of any watch file. Give a probability or range for each.
2. Add **conditional rules** for the direction call (if revenue is at least X and the guide is at least Y, then up with probability P) and a **falsifier** for each major claim: what result would prove the reasoning wrong, and what that would teach.
3. Stay with the numbers baseline unless you have evidence it does not carry and that survived Phase 3. Untested narratives (an analog to a past quarter, a management "habit", "the Street expects") do not move it. Every deviation gets one line: the evidence, and how far it moves the number. On the first run, shading a tested baseline on an untested analog made the forecast worse.
3a. **No resting at 50-60%.** For each item, either commit to the side the evidence supports with a probability, or write "no edge" for that item. A verdict where most items sit between 50% and 60% is a hedge, not a forecast.
3b. **List the overrides you cannot estimate** (an unannounced capital-structure action, a litigation outcome, a regulator) once, as named unknowns, instead of shading every probability for them.
4. Append the verdict to `research/YYYY-MM-DD-<ticker>-<quarter>-preview.md` and **commit and push before the release**. The commit timestamp is the pre-registration. Update the watch file's "known before the print" section with corrected facts, and add one bullet under the newest run's `### Open threads` in `context/latest.md`.
5. Tell the user the call in terms of their book: which plan lines are at stake, and whether any position needs to be sized for the implied move against it (see `earnings-play`).

## Phase 6: after the print

Score every item: hit or miss for ranges, a Brier score for probabilities, and day-1 against the conditional rules. Append a `## Scored` section to the preview, add the quarter to the outcome table, and rerun Phase 3 when the sample grows. Lessons about the process go to `trade-postmortem`; never edit the pre-print verdict.

## Traps found on the first run

- EPS "consensus" can be a mix of analysts who include a known one-time charge and analysts who don't (META Q3: 5.54 mixed, about 6.8 ex-charge, about 3.6 with it). Read the company's own disclosure of the charge.
- A single-source consensus number that the verifier cannot trace is dropped, along with everything derived from it.
- Fiscal calendars: Microsoft's September quarter is its FY Q1. Say which basis each capex number uses (cash PP&E or including finance leases).
- Peers reporting the same evening (META and MSFT shared every 2025-26 date) contaminate historical read-through.
- Agents in the sandbox may be denied outbound calls to new APIs. Report the exact command and ask the user for a permission rule; don't route around the denial.
- Stop rules: if a measurement fails its validity gate, write down in advance how many rebuilds are allowed, then honor the limit.

## Paste-in prompt for a new session

> Use the earnings-preview skill (`.claude/skills/earnings-preview/SKILL.md`) to preview TICKER's QUARTER earnings on DATE. You are the orchestrator: run the five lanes in parallel, then bull, bear and verifier, then a rebuttal round, then the statistician on the numbers baseline. Write the verdict table with probabilities, conditional rules and falsifiers into research/, update the watch file and context open threads, and commit and push before the release. Tell me which of my plan lines the print can trip.
