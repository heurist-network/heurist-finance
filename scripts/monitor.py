#!/usr/bin/env python
"""Check active plans for crossed price levels and due events; notify via Telegram.

Run from cron on the always-on machine, e.g. every 15 minutes:
  cd ~/heurist-finance && uv run python scripts/monitor.py

A level `when` is "<metric> <op> <number|metric>" with spaces, e.g. "price <= 480",
"close < sma200". Metrics: price (last trade), close (last daily close), sma200,
chg (today's % change vs the previous close, signed) and move (its absolute value).
A `fred:<SERIES>` ticker (e.g. fred:BAMLH0A0HYM2, HY OAS in %) reads the latest FRED
observation as both price and close; FRED posts these with about a one-day lag.
Each level/event fires once; the fire time is written back into the plan and pushed.
A level may carry `from` / `until` dates (inclusive) to bound when it is checked, e.g.
around a stock split. Levels sharing an `id` are one level: once any of them has
fired, the others are skipped. A level with `repeat: daily` re-arms each UTC day: its
`fired` stamp only blocks it on the day it was written.
"""

from __future__ import annotations

import asyncio
import operator
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.clients import eodhd  # noqa: E402
from src.instruments import resolver  # noqa: E402
from src import agent  # noqa: E402
from src.notify import telegram  # noqa: E402

PLANS = ROOT / "trading" / "plans"
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
OPS = {"<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge}


def split_frontmatter(text: str) -> tuple[dict | None, str]:
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    return (yaml.safe_load(m.group(1)), m.group(2)) if m else (None, text)


async def fred_metrics(series: str) -> dict[str, float]:
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        r = await client.get(FRED_CSV_URL, params={"id": series})
    r.raise_for_status()
    rows = [line.partition(",") for line in r.text.strip().splitlines()[1:]]
    last = float([v for _, _, v in rows if v not in ("", ".")][-1])  # "." marks a missing day
    return {"price": last, "close": last}


async def metrics(ticker: str) -> dict[str, float]:
    if ticker.startswith("fred:"):
        return await fred_metrics(ticker.removeprefix("fred:"))
    code = resolver.to_eodhd(ticker)
    quote = (await eodhd.real_time_batch([code]))[0]
    today = date.today()
    bars = await eodhd.eod(code, from_date=(today - timedelta(days=320)).isoformat(),
                           to_date=today.isoformat())
    closes = [float(b["adjusted_close"]) for b in bars if b.get("adjusted_close")]
    out = {"price": float(quote["close"]), "close": closes[-1],
           "sma200": sum(closes[-200:]) / 200}
    try:
        out["chg"] = (float(quote["close"]) / float(quote["previousClose"]) - 1) * 100
        out["move"] = abs(out["chg"])
    except (KeyError, TypeError, ValueError, ZeroDivisionError):  # "NA" before the first trade
        pass
    return out


def crossed(when: str, m: dict[str, float]) -> bool:
    lhs, op, rhs = when.split()
    if lhs not in m:
        return False
    return OPS[op](m[lhs], float(rhs) if re.fullmatch(r"[\d.]+", rhs) else m[rhs])


def is_fired(lv: dict, day: date) -> bool:
    if "fired" not in lv:
        return False
    return lv.get("repeat") != "daily" or str(lv["fired"])[:10] == day.isoformat()


async def main() -> None:
    now_utc = datetime.now(timezone.utc)
    now = now_utc.isoformat(timespec="minutes")
    today = date.today()
    changed: list[str] = []
    try:
        for path in sorted(PLANS.glob("*.md")):
            fm, body = split_frontmatter(path.read_text())
            if not fm or fm.get("status") != "active":
                continue
            levels = [lv for lv in fm.get("levels", [])
                      if lv.get("from", today) <= today <= lv.get("until", today)]
            tickers = {lv.get("ticker", fm["ticker"]) for lv in levels} | {fm["ticker"]}
            per_ticker = {t: await metrics(t) for t in tickers}
            m = per_ticker[fm["ticker"]]
            hits = []
            fired_ids = {lv["id"] for lv in fm.get("levels", []) if is_fired(lv, now_utc.date())}
            for lv in levels:
                if lv["id"] not in fired_ids and crossed(lv["when"], per_ticker[lv.get("ticker", fm["ticker"])]):
                    fired_ids.add(lv["id"])
                    lv["fired"] = now
                    hits.append(f"{lv.get('ticker', fm['ticker'])} {lv['id']}: {lv['when']} -> {lv['action']}")
            for ev in fm.get("events", []):
                if "fired" not in ev and ev["date"] <= today:
                    ev["fired"] = now
                    hits.append(f"event {ev['date']}: {ev['what']}")
            if hits:
                chg = f" ({m['chg']:+.1f}%)" if "chg" in m else ""
                telegram(f"{fm['ticker']} {m['price']:.2f}{chg} ({path.stem})\n" + "\n".join(hits))
                front = yaml.safe_dump(fm, sort_keys=False, default_flow_style=None,
                                       allow_unicode=True, width=1000)
                path.write_text(f"---\n{front}---\n{body}")
                changed.append(str(path.relative_to(ROOT)))
    finally:
        await eodhd.aclose()
    if changed:
        subprocess.run(["git", "add", *changed], cwd=ROOT, check=True)
        subprocess.run(["git", "commit", "-q", "-m", f"monitor: {', '.join(Path(c).stem for c in changed)}"],
                       cwd=ROOT, check=True)
        agent.push()


if __name__ == "__main__":
    asyncio.run(main())
