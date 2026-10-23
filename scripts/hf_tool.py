#!/usr/bin/env python
"""Unified data-fetch CLI for research: Heurist Mesh + EODHD + yfinance + Exa web.

Agent-optimized (terse, JSON to stdout, errors to stderr + nonzero exit). Kills
the friction we kept hitting: no PYTHONPATH (ROOT is inserted below), automatic
envelope unwrapping and on-the-fly param discovery.

Examples:
  uv run python scripts/hf_tool.py describe yahoo price_history
  uv run python scripts/hf_tool.py tools fred
  uv run python scripts/hf_tool.py prices AAPL MSFT --period 5y --out /tmp/px.json
  uv run python scripts/hf_tool.py call fred macro_series_history series_key=ust_10y view=change limit=60
  uv run python scripts/hf_tool.py fred BAMLH0A0HYM2 T10Y3M --limit 250
  uv run python scripts/hf_tool.py quote AAPL NVDA
  uv run python scripts/hf_tool.py earnings NVDA --limit 8
  uv run python scripts/hf_tool.py options NVDA --expiry 2026-08-21
  uv run python scripts/hf_tool.py web "Apple iPhone 17 eSIM only US" --n 5

`--out FILE` works both before and after the subcommand.

Generic escape hatch: `call AGENT TOOL k=v ...` (values are JSON-coerced;
`k=a,b,c` becomes a list). Use `--json '{...}'` for full control.
"""

from __future__ import annotations

import argparse
import json
import sys
import math
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.clients.mesh import (  # noqa: E402
    EXA_SEARCH_DIGEST_AGENT,
    FRED_MACRO_AGENT,
    SEC_EDGAR_AGENT,
    SELECTED_MESH_TOOLS,
    YAHOO_FINANCE_AGENT,
    MeshApiError,
    MeshClient,
    unwrap_results,
)

AGENTS = {
    "yahoo": YAHOO_FINANCE_AGENT,
    "fred": FRED_MACRO_AGENT,
    "sec": SEC_EDGAR_AGENT,
    "exa": EXA_SEARCH_DIGEST_AGENT,
}
# generous calendar-day spans per period preset (for price pagination)
PERIOD_DAYS = {"5d": 7, "1mo": 31, "3mo": 93, "6mo": 186, "1y": 372, "2y": 744,
               "3y": 1116, "5y": 1830, "10y": 3660, "max": 3660}
MESH_TRIES = 3  # Mesh timeouts are transient; a retry almost always succeeds
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


def die(msg: str, code: int = 1) -> None:
    print(json.dumps({"error": str(msg)}), file=sys.stderr)
    sys.exit(code)


AGENT_OUT = ROOT / "logs" / "out"


def emit(obj, out: str | None) -> None:
    text = json.dumps(obj, indent=2, default=str)
    if out:
        path = Path(out).resolve()
        if os.getenv("HF_AGENT") and not path.is_relative_to(AGENT_OUT):
            die(f"--out must be under {AGENT_OUT} in agent runs")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        print(json.dumps({"written": out, "bytes": len(text)}))
    else:
        print(text)


def coerce(v: str):
    """k=v value -> JSON scalar/list/str. `a,b` (non-JSON) becomes a list."""
    try:
        return json.loads(v)
    except (ValueError, TypeError):
        if "," in v:
            return [coerce(p) for p in v.split(",")]
        return v


def kv_args(pairs: list[str]) -> dict:
    args: dict = {}
    for p in pairs:
        if "=" not in p:
            die(f"bad k=v pair: {p!r}")
        k, v = p.split("=", 1)
        args[k] = coerce(v)
    return args


def agent_id(name: str) -> str:
    if name not in AGENTS:
        die(f"unknown agent {name!r}; pick one of {list(AGENTS)}")
    return AGENTS[name]


def cmd_tools(a) -> None:
    if a.agent:
        emit({a.agent: list(SELECTED_MESH_TOOLS[agent_id(a.agent)])}, a.out)
    else:
        emit({k: list(SELECTED_MESH_TOOLS[v]) for k, v in AGENTS.items()}, a.out)


def cmd_describe(a) -> None:
    aid = agent_id(a.agent)
    for t in MeshClient().selected_tools([aid]):
        if t.name == a.tool:
            props = t.parameters.get("properties", {})
            emit({"agent": a.agent, "tool": t.name, "description": t.description,
                  "required": t.parameters.get("required", []),
                  "properties": props}, a.out)
            return
    die(f"tool {a.tool!r} not found for agent {a.agent!r}")


def mesh_call(agent: str, tool: str, args: dict, tries: int = MESH_TRIES):
    """call_tool with retry on transient Mesh errors; raises MeshApiError after."""
    client = MeshClient()
    for attempt in range(tries):
        try:
            return unwrap_results(client.call_tool(agent, tool, args))
        except MeshApiError as e:
            if attempt == tries - 1:
                raise
            print(f"mesh retry {attempt + 1}/{tries - 1}: {e}", file=sys.stderr)
    raise AssertionError("unreachable")


def cmd_call(a) -> None:
    args = {}
    if a.json:
        try:
            args.update(json.loads(a.json))
        except ValueError as e:
            die(f"--json parse error: {e}")
    args.update(kv_args(a.kv))
    try:
        res = mesh_call(agent_id(a.agent), a.tool, args)
    except MeshApiError as e:
        die(f"mesh error: {e}")
    if a.agent == "yahoo" and a.tool == "news_search":
        from src.research.event_time import annotate_payload
        res = annotate_payload(res)
    emit(res, a.out)


# max plausible calendar-day spacing between adjacent bars / at window edges
BAR_GAP_SLACK_DAYS = 7  # a long weekend plus a holiday


def _fetch_bars(symbols, start, end, full):
    """Daily bars per symbol from the EODHD-backed price path."""
    import asyncio

    from src.clients import eodhd
    from src.prices import fetch as price_fetch

    from_dt = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(end, datetime.min.time(), tzinfo=timezone.utc)

    async def one(sym: str):
        try:
            return await price_fetch.daily_bars(sym, from_dt, end_dt), None
        except Exception as exc:
            return [], f"{type(exc).__name__}: {exc}"

    async def collect():
        try:
            syms = [s.upper() for s in symbols]
            return dict(zip(syms, await asyncio.gather(*(one(s) for s in syms))))
        finally:
            await eodhd.aclose()

    out = {}
    for sym, (bars, error) in asyncio.run(collect()).items():
        ds = [b["t"] for b in bars]
        rec = {"dates": ds, "bars": len(ds)}
        rec["ohlcv" if full else "closes"] = (
            [
                {"open": b["o"], "high": b["h"], "low": b["l"],
                 "close": b["c"], "volume": b["v"]}
                for b in bars
            ]
            if full
            else [b["c"] for b in bars]
        )
        gaps = [
            {"from": d1, "to": d2}
            for d1, d2 in zip(ds, ds[1:])
            if (date.fromisoformat(d2[:10]) - date.fromisoformat(d1[:10])).days
            > BAR_GAP_SLACK_DAYS
        ]
        if gaps:
            rec["gaps"] = gaps
        if error:
            rec["error"] = error
            print(f"WARNING: {sym}: {error}", file=sys.stderr)
        elif not bars:
            print(f"WARNING: no bars returned for {sym}", file=sys.stderr)
        out[sym] = rec
    return out


def cmd_prices(a) -> None:
    if a.start:
        start = date.fromisoformat(a.start)
        end = date.fromisoformat(a.end) if a.end else date.today() + timedelta(days=1)
    else:
        span = PERIOD_DAYS.get(a.period)
        if span is None:
            die(f"unknown --period {a.period!r}; use one of {list(PERIOD_DAYS)}")
        end = date.today() + timedelta(days=1)
        start = end - timedelta(days=span)
    emit(_fetch_bars(a.symbols, start, end, a.full), a.out)


def cmd_web(a) -> None:
    try:
        res = mesh_call(EXA_SEARCH_DIGEST_AGENT, "exa_web_search",
                        {"search_term": a.query, "num_results": a.n})
    except MeshApiError as e:
        die(f"mesh error: {e}")
    emit(res, a.out)


def cmd_primary(a) -> None:
    from src.research.primary import PrimaryClient, preview
    client = PrimaryClient()
    try:
        if a.cmd == "document":
            result = preview(client.document(a.url), chars=a.chars)
        elif a.cmd == "trials":
            result = client.trials(a.query, limit=a.limit, nct=a.nct)
        elif a.cmd == "papers":
            result = client.papers(a.query, limit=a.limit)
        else:
            result = client.company(a.ticker, limit=a.limit, science=a.science)
        emit(result, a.out)
    except Exception as exc:
        die(f"primary source: {type(exc).__name__}: {exc}")
    finally:
        client.client.close()


def cmd_fred(a) -> None:
    """Direct FRED pull (fredgraph.csv) — any series id, not just the curated set."""
    import httpx

    out = {}
    for sid in a.series:
        sid = sid.upper()
        r = httpx.get(FRED_CSV_URL, params={"id": sid}, timeout=30,
                      follow_redirects=True)
        if r.status_code != 200 or not r.text.startswith("observation_date"):
            die(f"FRED series {sid!r} not found (HTTP {r.status_code})")
        dates, values = [], []
        for line in r.text.strip().splitlines()[1:]:
            d, _, v = line.partition(",")
            if v in ("", "."):
                continue  # FRED marks missing observations with "."
            if a.start and d < a.start:
                continue
            if a.end and d > a.end:
                continue
            dates.append(d)
            values.append(float(v))
        if a.limit:
            dates, values = dates[-a.limit:], values[-a.limit:]
        out[sid] = {"dates": dates, "values": values, "obs": len(dates)}
    emit(out, a.out)


QUOTE_FIELDS = (
    "regularMarketPrice", "marketCap", "trailingPE", "forwardPE",
    "dividendRate", "dividendYield", "trailingAnnualDividendYield",
    "exDividendDate", "payoutRatio", "fiveYearAvgDividendYield",
    "sharesShort", "shortPercentOfFloat", "shortRatio",
    "bid", "ask", "bidSize", "askSize", "averageVolume", "beta",
    "fiftyTwoWeekLow", "fiftyTwoWeekHigh", "earningsTimestamp",
)

# EODHD us-quote-delayed field -> the key this command emits. Yahoo reports
# dividendYield as a percent and EODHD as a fraction, so that one is scaled.
# The 52-week range is deliberately absent: EODHD's precomputed value is wrong
# on some symbols (SPY reports a low of 69.005 against an actual 629.28).
EODHD_QUOTE_FIELDS = {
    "lastTradePrice": "regularMarketPrice",
    "marketCap": "marketCap",
    "pe": "trailingPE",
    "forwardPE": "forwardPE",
    "dividend": "dividendRate",
    "payoutRatio": "payoutRatio",
    "bidPrice": "bid",
    "askPrice": "ask",
    "bidSize": "bidSize",
    "askSize": "askSize",
    "averageVolume": "averageVolume",
}


def cmd_quote(a) -> None:
    """Quote facts for a ticker: valuation, dividend, short interest, NBBO spread.

    EODHD covers US listings; short interest and beta have no EODHD equivalent
    on this plan, so those fields still come from Yahoo.
    """
    import asyncio

    import yfinance as yf

    from src.clients import eodhd
    from src.instruments import resolver

    codes = {sym: resolver.to_eodhd(sym.upper()) for sym in a.symbols}

    async def collect():
        try:
            return await eodhd.us_quote_batch(list(codes.values()))
        finally:
            await eodhd.aclose()

    rows = asyncio.run(collect())

    out = {}
    for sym in a.symbols:
        info = yf.Ticker(sym).info or {}
        rec = {k: info[k] for k in QUOTE_FIELDS if info.get(k) is not None}
        row = rows.get(codes[sym]) or {}
        rec.update({
            key: row[src]
            for src, key in EODHD_QUOTE_FIELDS.items()
            if row.get(src)
        })
        if row.get("dividendYield") is not None:
            rec["dividendYield"] = round(row["dividendYield"] * 100, 4)
        for k in ("exDividendDate", "earningsTimestamp"):
            if isinstance(rec.get(k), (int, float)):
                rec[k] = datetime.fromtimestamp(rec[k], tz=timezone.utc).date().isoformat()
        for side in ("bid", "ask", "bidSize", "askSize"):
            if not rec.get(side):
                rec.pop(side, None)
        bid, ask = rec.get("bid"), rec.get("ask")
        if bid and ask and ask > bid:
            rec["spread_bps"] = round((ask - bid) / ((ask + bid) / 2) * 10_000, 2)
        out[sym.upper()] = rec
    emit(out, a.out)


def cmd_earnings(a) -> None:
    """Historical + upcoming earnings dates with EPS estimate/actual/surprise."""
    import yfinance as yf

    out = {}
    for sym in a.symbols:
        df = yf.Ticker(sym).get_earnings_dates(limit=a.limit)
        rows = []
        if df is not None:
            for ts, row in df.iterrows():
                rec = {"date": ts.date().isoformat()}
                for col, key in (("EPS Estimate", "eps_estimate"),
                                 ("Reported EPS", "eps_actual"),
                                 ("Surprise(%)", "surprise_pct")):
                    v = row.get(col)
                    if v is not None and v == v:  # drop NaN
                        rec[key] = round(float(v), 4)
                rows.append(rec)
        # yfinance ignores its own limit arg; enforce it here (rows are newest-first)
        out[sym.upper()] = rows[:a.limit]
    emit(out, a.out)


def _bs_delta(spot: float, strike: float, iv: float, t_years: float,
              rate: float, is_call: bool) -> float | None:
    if not (spot > 0 and strike > 0 and iv > 0 and t_years > 0):
        return None
    d1 = (math.log(spot / strike) + (rate + iv * iv / 2) * t_years) / (iv * math.sqrt(t_years))
    n_d1 = (1 + math.erf(d1 / math.sqrt(2))) / 2
    return round(n_d1 if is_call else n_d1 - 1, 4)


def cmd_options(a) -> None:
    """Options chain with IV and Black-Scholes delta (no expiry -> list expiries)."""
    import yfinance as yf

    tk = yf.Ticker(a.symbol)
    expiries = list(tk.options)
    if not a.expiry:
        emit({"symbol": a.symbol.upper(), "expiries": expiries}, a.out)
        return
    if a.expiry not in expiries:
        die(f"expiry {a.expiry!r} not listed; available: {expiries}")
    spot = tk.info.get("regularMarketPrice") or tk.fast_info.get("lastPrice")
    t_years = max((date.fromisoformat(a.expiry) - date.today()).days, 0) / 365.0
    chain = tk.option_chain(a.expiry)
    out = {"symbol": a.symbol.upper(), "expiry": a.expiry, "spot": spot,
           "rate_assumed": a.rate, "calls": [], "puts": []}
    for side, df in (("calls", chain.calls), ("puts", chain.puts)):
        for _, row in df.iterrows():
            iv = row.get("impliedVolatility")
            rec = {"strike": float(row["strike"]),
                   "bid": float(row["bid"]) if row.get("bid") == row.get("bid") else None,
                   "ask": float(row["ask"]) if row.get("ask") == row.get("ask") else None,
                   "last": float(row["lastPrice"]) if row.get("lastPrice") == row.get("lastPrice") else None,
                   "volume": int(row["volume"]) if row.get("volume") == row.get("volume") else 0,
                   "open_interest": int(row["openInterest"]) if row.get("openInterest") == row.get("openInterest") else 0,
                   "iv": round(float(iv), 4) if iv and iv == iv else None}
            if rec["iv"] and spot:
                rec["delta"] = _bs_delta(spot, rec["strike"], rec["iv"],
                                         t_years, a.rate, side == "calls")
            out[side].append(rec)
    emit(out, a.out)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hf_tool", description=__doc__)
    p.add_argument("--out", default=None,
                   help="write JSON result to this file instead of stdout")
    # accepted postfix too (SUPPRESS so an absent postfix flag keeps the prefix value)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--out", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    sub = p.add_subparsers(dest="cmd", required=True, parser_class=lambda **kw:
                           argparse.ArgumentParser(parents=[common], **kw))

    s = sub.add_parser("tools", help="list mesh tool names")
    s.add_argument("agent", nargs="?", choices=list(AGENTS))
    s.set_defaults(fn=cmd_tools)

    s = sub.add_parser("describe", help="show a mesh tool's param schema")
    s.add_argument("agent", choices=list(AGENTS))
    s.add_argument("tool")
    s.set_defaults(fn=cmd_describe)

    s = sub.add_parser("call", help="invoke any mesh tool (auto-unwrapped)")
    s.add_argument("agent", choices=list(AGENTS))
    s.add_argument("tool")
    s.add_argument("--json", help="args as a JSON object")
    s.add_argument("kv", nargs="*", help="k=v args (JSON-coerced; a,b -> list)")
    s.set_defaults(fn=cmd_call)

    s = sub.add_parser("prices", help="daily bars from the EODHD price path")
    s.add_argument("symbols", nargs="+")
    s.add_argument("--period", default="1y", choices=list(PERIOD_DAYS))
    s.add_argument("--start")
    s.add_argument("--end")
    s.add_argument("--full", action="store_true", help="full OHLCV instead of closes")
    s.set_defaults(fn=cmd_prices)

    s = sub.add_parser("fred", help="direct FRED pull, any series id (not just curated)")
    s.add_argument("series", nargs="+", help="FRED series ids, e.g. BAMLH0A0HYM2 T10Y3M DTWEXBGS")
    s.add_argument("--start", help="ISO date lower bound")
    s.add_argument("--end", help="ISO date upper bound")
    s.add_argument("--limit", type=int, default=250, help="keep last N obs; 0 = all")
    s.set_defaults(fn=cmd_fred)

    s = sub.add_parser("quote", help="valuation / dividend / short interest / NBBO spread (EODHD + Yahoo)")
    s.add_argument("symbols", nargs="+")
    s.set_defaults(fn=cmd_quote)

    s = sub.add_parser("earnings", help="historical + upcoming earnings dates (yfinance)")
    s.add_argument("symbols", nargs="+")
    s.add_argument("--limit", type=int, default=12)
    s.set_defaults(fn=cmd_earnings)

    s = sub.add_parser("options", help="options chain with IV + BS delta (yfinance)")
    s.add_argument("symbol")
    s.add_argument("--expiry", help="YYYY-MM-DD; omit to list available expiries")
    s.add_argument("--rate", type=float, default=0.04,
                   help="risk-free rate for delta calc")
    s.set_defaults(fn=cmd_options)

    s = sub.add_parser("web", help="Exa web search (deterministic)")
    s.add_argument("query")
    s.add_argument("--n", type=int, default=5)
    s.set_defaults(fn=cmd_web)

    s = sub.add_parser("document", help="full HTML/PDF source with immutable snapshot and change tracking")
    s.add_argument("url")
    s.add_argument("--chars", type=int, default=8000, help="context excerpt size; complete extracted text always saved")
    s.set_defaults(fn=cmd_primary)

    s = sub.add_parser("primary", help="company IR, SEC, regulatory documents; curated watchlist")
    s.add_argument("ticker")
    s.add_argument("--limit", type=int, choices=range(1, 6), default=2)
    s.add_argument("--science", action="store_true", help="also query candidate aliases in trial/publication databases")
    s.set_defaults(fn=cmd_primary)

    s = sub.add_parser("trials", help="ClinicalTrials.gov design, endpoints, status, results and snapshot changes")
    s.add_argument("query", nargs="?", default="")
    s.add_argument("--nct", help="exact NCT identifier")
    s.add_argument("--limit", type=int, choices=range(1, 101), default=20)
    s.set_defaults(fn=cmd_primary)

    s = sub.add_parser("papers", help="PubMed abstracts with study types and electronic/print dates")
    s.add_argument("query")
    s.add_argument("--limit", type=int, choices=range(1, 51), default=10)
    s.set_defaults(fn=cmd_primary)

    return p


def main() -> None:
    args = build_parser().parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
