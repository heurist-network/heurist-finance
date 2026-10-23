---
name: trade-postmortem
description: "Grade completed trades on process, not P&L: the plan-adherence × outcome 2×2, hindsight-bias-proof attribution using as-of-then data, expectancy tracking across the trade log, and pattern mining for repeated errors. Use when asked to review a closed trade, learn from a win or loss, compute win rate/expectancy, or find recurring mistakes across past trades. Trigger: `use postmortem skill`."
---

# Trade Postmortem

Shared plumbing and output contract: [../\_shared/analyst-core.md](../_shared/analyst-core.md). The feedback loop is where a trader either compounds skill or compounds superstition — and P&L alone teaches the wrong lessons, because markets pay bad process often enough to reinforce it. This skill closes the loop that `trading-plan` opens: the plan documents in `trading/plans/` are the exam answer key; the postmortem grades against them.

## The 2×2 (grade every trade on both axes)

| | **Followed the plan** | **Broke the plan** |
|---|---|---|
| **Made money** | Skill (or well-bought variance). Reinforce. | **The dangerous quadrant** — a paid mistake trains repetition; flag it louder than any loss |
| **Lost money** | Tuition — the plan bought variance and variance arrived. Check whether the plan itself was sound; often *change nothing* | Compound error — but the fix is one process rule, not a new system |

The paid-mistake quadrant is the reason this skill exists: profitable rule-breaking is the most reinforcing event in trading and the most corrosive. Say it plainly when found.

## Hindsight-proof attribution (the hard part done honestly)

Judging a decision by information available *after* it is the universal postmortem failure. Reconstruct the as-of-then view before grading:

- **What was knowable at entry:** the plan document's thesis and scenario table; the as-of-then narrative, reconstructed from dated articles via WebSearch; macro *as then reported* — use `fred macro_vintage_history` (this is exactly what vintage data exists for: the payroll number the user traded on, not its later revision); prices/IV at the time from `prices`.
- **If the reported fills conflict with the verified tape** (a price that never traded that day, a date with no such move): don't silently accept or correct. Grade the *reported* structure on process, flag the tape conflict explicitly, and cross-check whether the narrative's shape (direction, rough timing) survives on the real bars — if it doesn't, the postmortem's first finding is the record-keeping.
- Then the four-way attribution, each scored right/wrong *given that reconstruction*: **Thesis** (did the predicted mechanism operate?), **Timing** (right thesis, wrong clock is the most common split verdict — note it feeds sizing, not thesis, next time), **Sizing** (did size force a behavioral exit before the thesis resolved? cross-ref `position-sizing`'s 11pm test), **Exit** (against the plan's invalidation list: did they exit on signal, on noise, or on pulse? — the field card's noise/signal split, applied retroactively).
- **Counterfactual honestly bounded:** "would've made X if held" uses the *plan's* exit rule as the counterfactual, never the peak price — the peak was only visible in hindsight, and grading against it manufactures regret, which drives the next oversize.

## The log level (≥10 trades: where the real lessons live)

Single-trade postmortems are anecdotes; the log is data. From `trading/plans/` + `trading/trades.md` (each fill names the plan level it executed, or `unplanned` — the share of `unplanned` fills and fills at the wrong level is the plan-adherence measure):

- **Expectancy** = (win% × avg win) − (loss% × avg loss), and the payoff ratio. A 40% win rate with 3:1 winners is a healthy trend-following profile; a 70% win rate with 0.5:1 is premium-selling shape — **neither is better, but each has a signature failure** (the first dies by abandoning the system mid-losing-streak; the second by one unmanaged tail). Diagnose which system the user is *actually* running vs the one they think they are running.
- **Pattern mining, the recurring retail set:** winners cut early while losers ride (compare average hold time of winners vs losers — the asymmetry is diagnostic); size creep after win streaks (overconfidence is measurable: correlate position size with trailing 3-trade P&L); repeated thesis-type failures (all the losses are one skill's domain — e.g. every loser was a crowded momentum name → route future entries through the `sentiment-positioning` filter); event-day exits (panic-selling on headlines the plan had pre-classified as noise).
- **Streak math for context:** a 55%-win-rate system has a ~99% chance of a 5-loss streak within 100 trades — losing streaks are an *expected feature*, and the postmortem's job is distinguishing "variance within a sound system" from "the edge is gone," which needs the thesis-type breakdown, not the streak length.

## Anti-patterns this skill must not commit

- **System-hopping on noise:** changing the approach after every loss guarantees always trading an untested system. One process change per review, maximum, and only on a pattern (≥3 occurrences), never on a single outcome.
- **Outcome-flattering narratives:** "I knew it would recover" (they added risk on no signal and got paid — dangerous quadrant). The grade goes to the decision, and the reconstruction above is what makes that enforceable rather than rhetorical.
- Grading trades that predate plan documents: reconstruct a minimal plan from what the user says they believed (as `trading-plan` does mid-trade), grade gently, and use it as the argument for writing plans going forward.

Write the verdict as a `## Postmortem` section at the end of the plan file and set its frontmatter `status` to `closed` (or `invalidated`). When a pattern across 3+ trades supports a process change, add one dated line to the Lessons section of `profile.md`; a single trade never changes the profile.

End with **Call / Falsifier / Horizon** — here the Call is the process verdict + the one change (if any); the falsifier is what would revise it (e.g., "if the next 10 trades show the same early-cut pattern after this fix, the fix failed"); the horizon is the next review checkpoint (every ~10 closed trades or monthly).
