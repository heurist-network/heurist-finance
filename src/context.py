"""Session context written by the brief: context/latest.md keeps the two most recent runs
(one trading day), context/index.md keeps recent high-confidence facts per ticker."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from pathlib import Path

RUNS_KEPT = 2
INDEX_DAYS = 30
INDEX_PER_TICKER = 10

LATEST_HEAD = """# Market context

The two most recent brief runs, newest first. Each run is stamped with the time it was
written; numbers inside carry their own as-of times. Re-pull before using a number in a plan.
"""

INDEX_HEAD = """# Ticker index

Recent developments per ticker that a model's training data cannot contain: dated facts from
primary sources or established publishers, kept {days} days. Background, commentary and
price moves are not here. Line format: `- YYYY-MM-DD · TYPE · fact URL`.
"""

RUN_MARK = re.compile(r"^<!-- run as_of=(\S+) .*?-->$", re.M)
TICKER = re.compile(r"^[A-Z0-9][A-Z0-9.\-^=]{0,11}$")
ENTRY = re.compile(r"^- (\d{4}-\d{2}-\d{2}) · ")


def run_section(as_of: datetime, slot: str, slot_desc: str, brief: str, notes: str) -> str:
    """One run's block: a parseable marker, a dated heading, and the notes one level down."""
    notes = re.sub(r"^## ", "### ", notes.strip(), flags=re.M)
    heading = as_of.strftime("%Y-%m-%d %a %H:%M %Z")
    return (f"<!-- run as_of={as_of.isoformat(timespec='minutes')} slot={slot} brief={brief} -->\n"
            f"## {heading} · {slot} ({slot_desc})\n\n{notes}\n")


def update_latest(path: Path, section: str) -> None:
    """Put this run on top and keep the previous RUNS_KEPT - 1 runs below it."""
    old = path.read_text() if path.exists() else ""
    starts = [m.start() for m in RUN_MARK.finditer(old)]
    runs = [old[a:b].strip() + "\n" for a, b in zip(starts, starts[1:] + [len(old)])]
    kept = [section.strip() + "\n", *runs][:RUNS_KEPT]
    path.parent.mkdir(exist_ok=True)
    path.write_text(LATEST_HEAD + "\n" + "\n".join(kept))


def parse_entries(text: str) -> tuple[list[tuple[str, str]], list[str]]:
    """`TICKER | YYYY-MM-DD | TYPE | fact | URL` lines -> (ticker, index line); bad lines back."""
    entries, bad = [], []
    for line in text.splitlines():
        line = line.strip().lstrip("-* ").strip()
        if not line or line.upper() == "NONE":
            continue
        parts = [p.strip() for p in line.split("|")]
        try:
            ticker, day, kind, url = parts[0].upper(), parts[1], parts[2].upper(), parts[-1]
            fact = " | ".join(parts[3:-1])
            date.fromisoformat(day)
            assert TICKER.match(ticker) and fact and url.startswith("http") and len(parts) >= 5
        except (IndexError, ValueError, AssertionError):
            bad.append(line)
            continue
        entries.append((ticker, f"- {day} · {kind} · {fact} {url}"))
    return entries, bad


def merge_index(path: Path, entries: list[tuple[str, str]], today: date) -> None:
    """Add entries under their ticker, drop duplicates and dated lines older than INDEX_DAYS,
    newest first, at most INDEX_PER_TICKER dated lines per ticker. Undated lines are kept."""
    tickers: dict[str, list[str]] = {}
    current = None
    for line in (path.read_text() if path.exists() else "").splitlines():
        if line.startswith("## "):
            current = tickers.setdefault(line[3:].strip(), [])
        elif current is not None and line.strip():
            current.append(line.rstrip())
    for ticker, line in entries:
        lines = tickers.setdefault(ticker, [])
        if line not in lines:
            lines.append(line)

    cutoff = (today - timedelta(days=INDEX_DAYS)).isoformat()
    out = [INDEX_HEAD.format(days=INDEX_DAYS)]
    for ticker in sorted(tickers):
        dated = [l for l in tickers[ticker] if ENTRY.match(l)]
        dated = sorted((l for l in dated if ENTRY.match(l).group(1) >= cutoff),
                       key=lambda l: ENTRY.match(l).group(1), reverse=True)[:INDEX_PER_TICKER]
        lines = dated + [l for l in tickers[ticker] if not ENTRY.match(l)]
        if lines:
            out.append(f"## {ticker}\n" + "\n".join(lines) + "\n")
    path.parent.mkdir(exist_ok=True)
    path.write_text("\n".join(out))
