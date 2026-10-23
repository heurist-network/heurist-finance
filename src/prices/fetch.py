"""Upstream fetch + freshness policy for the price snapshot store.

Shared by the request path (absent-key single-flight) and the background
refresher (recurring hot-set fetches) so both write identical entries:

- ``quote:{sym}``    -> raw EODHD real-time row
- ``rich_quote:{sym}`` -> extended US quote details for asset pages
- ``bars:{sym}`` -> canonical daily bar series INCLUDING the indicator warm-up
  prefix; sparkline and indicators are projections of this one entry.

Freshness (``ttl``) and refresh cadence are deliberately decoupled: the
refresher re-fetches on ``fetched_at`` age, while ``fresh_until`` only
drives the `stale` flag on reads. RTH-linked classes go dormant outside US
regular hours (a settle window after the close lets the 15-min-delayed feed
land on the official close); crypto/FX/commodities run 24/7.
"""

from __future__ import annotations

import asyncio
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import yfinance as yf

from src.clients import eodhd
from src.instruments import resolver
from src.prices import calendar
from src.prices.store import Snapshot, store

log = logging.getLogger(__name__)

# EODHD is pay-per-call, so quote refresh is deliberately slow: 120s while
# the US market is open, 900s while it is closed. The closed cadence only
# applies to 24/7 classes (crypto/FX) — RTH-linked classes go dormant when
# closed. TTLs sit at 1.5× cadence so entries don't flick `stale` in the
# gap between scheduled refreshes.
QUOTE_CADENCE_OPEN_S = 120.0
QUOTE_CADENCE_CLOSED_S = 900.0
QUOTE_TTL_OPEN_S = 1.5 * QUOTE_CADENCE_OPEN_S
QUOTE_TTL_CLOSED_S = 1.5 * QUOTE_CADENCE_CLOSED_S
# Rich US snapshots are asset-page-only and include extended-hours trades.
# Keep them independently fresh through pre/post-market instead of freezing
# them on the regular-session schedule used by the homepage quote hot set.
RICH_QUOTE_TTL_S = 300.0
COMMODITY_QUOTE_TTL_S = 4 * 60 * 60.0
COMMODITY_QUOTE_CADENCE_S = COMMODITY_QUOTE_TTL_S
# Longest gap a FRED-backed commodity observation may carry and still be
# quoted as the current session. Sized to clear a Friday print read on the
# following Tuesday, so an ordinary weekend does not trip the fallback while
# the provider's real ~1-week lag always does.
COMMODITY_MAX_OBSERVATION_AGE_S = 4 * 24 * 60 * 60.0
BARS_TTL_S = 60 * 60.0
BARS_CADENCE_S = BARS_TTL_S
UNSUPPORTED_TTL_S = 1800.0
# A provider refusal proves nothing about the symbol, so this only has to
# damp the retry loop until the next scheduled refresh.
PROVIDER_REFUSED_TTL_S = 120.0
# Delayed feed settles on the official close ~15 min after the bell; keep
# refreshing through this window so frozen quotes hold the true close.
SETTLE_S = 1200.0

_BATCH_SIZE = 15
_BARS_CONCURRENCY = 4

_RTH_LINKED_CLASSES = frozenset({"equity", "equity_index", "etf", "vol", "rate"})

TIMEFRAME_CONFIG: dict[str, dict] = {
    "7d": {"display_days": 7},
    "30d": {"display_days": 30},
    "90d": {"display_days": 90},
    "1y": {"display_days": 365},
}

SERIES_BACK_DAYS = 400


# ── Keys ─────────────────────────────────────────────────────────────


def quote_key(symbol: str) -> str:
    return f"quote:{symbol}"


def bars_key(symbol: str) -> str:
    return f"bars:{symbol}"


def rich_quote_key(symbol: str) -> str:
    return f"rich_quote:{symbol}"


def _parse_bars_key(key: str) -> str:
    return key.removeprefix("bars:")


# ── Schedule policy ──────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class MarketPhase:
    """US-market clock state for one refresher tick / fetch batch.

    A single value for the whole tick — compute it once via ``market_phase``
    and thread it through the per-symbol cadence/TTL calls instead of each
    of them re-hitting the calendar for every symbol.
    """

    is_open: bool
    in_settle: bool
    seconds_to_open: float


def market_phase(now: datetime | None = None) -> MarketPhase:
    if now is None:
        now = datetime.now(timezone.utc)
    return MarketPhase(
        is_open=calendar.is_open(now),
        in_settle=(now - calendar.previous_close(now)).total_seconds() <= SETTLE_S,
        seconds_to_open=(calendar.next_open(now) - now).total_seconds() + 60.0,
    )


def _rth_linked(symbol: str) -> bool:
    inst = resolver.get(symbol)
    return inst is not None and inst.asset_class in _RTH_LINKED_CLASSES


def _phase(phase: MarketPhase | None) -> MarketPhase:
    return phase if phase is not None else market_phase()


def quote_ttl(symbol: str, phase: MarketPhase | None = None) -> float:
    if resolver.is_commodity_future(symbol):
        return COMMODITY_QUOTE_TTL_S
    p = _phase(phase)
    if not _rth_linked(symbol):
        return QUOTE_TTL_OPEN_S if p.is_open else QUOTE_TTL_CLOSED_S
    # A fetch inside the settle window must NOT take the long freeze: the
    # delayed feed has not landed the official close yet, so stamping it
    # fresh-until-open would hold a mid-settle price out as final all night.
    # Keeping it short means the entry goes stale when the window ends and the
    # next reader's request refetches the real close.
    if p.is_open or p.in_settle:
        return QUOTE_TTL_OPEN_S
    return p.seconds_to_open


def bars_ttl(symbol: str, phase: MarketPhase | None = None) -> float:
    base = BARS_TTL_S
    if not _rth_linked(symbol):
        return base
    p = _phase(phase)
    if p.is_open or p.in_settle:
        return base
    return max(base, p.seconds_to_open)


def quote_cadence(symbol: str, phase: MarketPhase | None = None) -> float | None:
    """Refresher re-fetch interval; None = dormant (bootstrap-only)."""
    if resolver.is_commodity_future(symbol):
        return COMMODITY_QUOTE_CADENCE_S
    p = _phase(phase)
    if not _rth_linked(symbol):
        return QUOTE_CADENCE_OPEN_S if p.is_open else QUOTE_CADENCE_CLOSED_S
    return QUOTE_CADENCE_OPEN_S if (p.is_open or p.in_settle) else None


def bars_cadence(symbol: str, phase: MarketPhase | None = None) -> float | None:
    if not _rth_linked(symbol):
        return BARS_CADENCE_S
    p = _phase(phase)
    return BARS_CADENCE_S if (p.is_open or p.in_settle) else None


# ── Quote fetching ───────────────────────────────────────────────────


async def quote_snapshots(
    symbols: list[str], *, bars: bool = False
) -> dict[str, Snapshot | None]:
    """Serve quote snapshots for `symbols`: peek the store, single-flight
    absent AND stale keys. `bars=True` also hots sparkline demand.

    Stale must be refetched, not flagged: a stale RTH-linked entry can hold the
    previous session's close (its TTL ran to the opening bell). Upstream
    failure falls back to the stored snapshot.
    """
    store.touch(symbols, bars=bars)
    snaps: dict[str, Snapshot | None] = {}
    refetch: list[str] = []
    for sym in symbols:
        snap = store.peek(quote_key(sym))
        snaps[sym] = snap
        if snap is None or snap.stale:
            refetch.append(sym)
    if refetch:
        fetched = await store.fetch_many(
            [quote_key(s) for s in refetch], fetch_quote_entries
        )
        for sym in refetch:
            got = fetched.get(quote_key(sym))
            if got is not None:
                snaps[sym] = got
    return snaps


async def rich_quote_snapshot(symbol: str) -> Snapshot | None:
    """Return the optional rich US snapshot for an asset-page quote.

    This is intentionally demand-driven rather than part of the homepage hot
    set: only the asset detail surface needs the extra statistics and extended
    session fields.
    """
    inst = resolver.get(symbol)
    if inst is not None and inst.asset_class not in {"equity", "etf"}:
        return None
    if not resolver.to_eodhd(symbol).endswith(".US"):
        return None
    key = rich_quote_key(symbol)
    snap = store.peek(key)
    if snap is None:
        fetched = await store.fetch_many([key], fetch_rich_quote_entries)
        return fetched.get(key)
    if snap.stale:
        store.refresh_soon(key, fetch_rich_quote_entries)
    return snap


async def fetch_rich_quote_entries(
    keys: list[str],
) -> dict[str, tuple[dict | None, float]]:
    symbols = [key.removeprefix("rich_quote:") for key in keys]
    pairs = [(symbol, resolver.to_eodhd(symbol)) for symbol in symbols]
    chunks = [pairs[i : i + _BATCH_SIZE] for i in range(0, len(pairs), _BATCH_SIZE)]
    out: dict[str, tuple[dict | None, float]] = {}
    for chunk in chunks:
        try:
            rows = await eodhd.us_quote_batch([code for _, code in chunk])
        except eodhd.EodhdApiError as exc:
            log.warning("EODHD rich quote batch failed: %s", exc)
            if exc.status in (400, 401, 403, 404):
                for symbol, _ in chunk:
                    out[rich_quote_key(symbol)] = (None, PROVIDER_REFUSED_TTL_S)
            continue
        for symbol, code in chunk:
            row = rows.get(code)
            out[rich_quote_key(symbol)] = (
                row,
                RICH_QUOTE_TTL_S if row is not None else UNSUPPORTED_TTL_S,
            )
    return out


async def fetch_quote_entries(
    keys: list[str],
) -> dict[str, tuple[dict | None, float]]:
    """Store fetcher for ``quote:*`` keys — one batched call per 15 symbols.

    A symbol that came back with data caches its row. A symbol that was
    successfully queried but returned no row is **negative-cached** (value
    None) so an unresolvable/delisted ticker isn't re-fetched on every FE
    poll and every refresher tick — that would burn the single key's minute
    limit. Symbols whose whole chunk failed (transient 429/5xx) are omitted
    so the next round retries them.

    A symbol only the *fallback* failed to cover is a different case: EODHD
    never answered for it, so "unresolvable" is unproven and the long TTL
    would keep it blank long after the provider recovers. Those get a short
    TTL — enough to stop a hot retry loop, short enough to self-heal.
    """
    symbols = [k.removeprefix("quote:") for k in keys]
    commodity_symbols = [s for s in symbols if resolver.is_commodity_future(s)]
    yahoo_futures = [s for s in symbols if resolver.is_unmapped_future(s)]
    real_time_symbols = [
        s
        for s in symbols
        if not resolver.is_commodity_future(s) and not resolver.is_unmapped_future(s)
    ]
    rows, queried, refused = await _batch_real_time(real_time_symbols)
    phase = market_phase()
    out: dict[str, tuple[dict | None, float]] = {}
    for s in real_time_symbols:
        row = rows.get(s)
        if row is not None:
            out[quote_key(s)] = (row, quote_ttl(s, phase))
        elif s in queried:
            out[quote_key(s)] = (None, UNSUPPORTED_TTL_S)
        elif s in refused:
            out[quote_key(s)] = (None, PROVIDER_REFUSED_TTL_S)
    out.update(await _commodity_quote_entries(commodity_symbols))
    if yahoo_futures:
        try:
            yrows = await _yahoo_quote_rows(yahoo_futures)
        except Exception as exc:
            log.warning("Yahoo unmapped-future quote failed: %s", exc)
            yrows = {}
        for s in yahoo_futures:
            row = yrows.get(s)
            out[quote_key(s)] = (
                (row, quote_ttl(s, phase))
                if row is not None
                else (None, PROVIDER_REFUSED_TTL_S)
            )
    return out


async def _commodity_quote_entries(
    symbols: list[str],
) -> dict[str, tuple[dict | None, float]]:
    """Synthesize quote rows from the last two FRED-backed daily values."""
    now = datetime.now(timezone.utc)
    from_date = (now - timedelta(days=14)).strftime("%Y-%m-%d")
    to_date = now.strftime("%Y-%m-%d")

    async def one(symbol: str) -> tuple[str, tuple[dict | None, float] | None]:
        code = resolver.to_eodhd(symbol)
        try:
            raw = await eodhd.commodities_historical(
                code, from_date=from_date, to_date=to_date
            )
        except eodhd.EodhdApiError as exc:
            if exc.status in (400, 404):
                return quote_key(symbol), (None, UNSUPPORTED_TTL_S)
            log.warning("EODHD commodity quote failed for %s: %s", symbol, exc)
            if exc.status == 402:
                try:
                    row = (await _yahoo_quote_rows([symbol])).get(symbol)
                except Exception as fallback_exc:
                    log.warning(
                        "Yahoo commodity quote fallback failed for %s: %s",
                        symbol,
                        fallback_exc,
                    )
                    return quote_key(symbol), None
                if row is not None:
                    return quote_key(symbol), (row, COMMODITY_QUOTE_TTL_S)
            return quote_key(symbol), None
        row = _commodity_quote_row(code, raw)
        if row is None:
            return quote_key(symbol), (None, UNSUPPORTED_TTL_S)
        if _observation_too_old(row):
            try:
                fresh = (await _yahoo_quote_rows([symbol])).get(symbol)
            except Exception as exc:
                log.warning(
                    "Yahoo commodity freshness fallback failed for %s: %s",
                    symbol,
                    exc,
                )
            else:
                if fresh is not None:
                    return quote_key(symbol), (fresh, COMMODITY_QUOTE_TTL_S)
        return quote_key(symbol), (row, COMMODITY_QUOTE_TTL_S)

    resolved = await asyncio.gather(*(one(s) for s in symbols))
    return {key: entry for key, entry in resolved if entry is not None}


def _observation_too_old(row: dict) -> bool:
    """True when a synthesized commodity row is too old to quote as current.

    The FRED-backed commodities series runs roughly a week behind: measured
    2026-08-18, the newest ``WTI`` observation was 2026-08-11, and its
    ``as_of`` did not advance between refreshes. Serving that day's move as
    the current session's change puts a stale and often wrong-signed number
    on a live strip (2026-08-18: CL showed +1.21% while crude was down
    1.50%), so anything older than a long weekend hands off to Yahoo, which
    quotes the actual front-month contract.

    Deliberately a freshness check rather than a permanent reroute: if EODHD
    closes the gap, the documented FRED path resumes serving on its own.
    """
    ts = row.get("timestamp")
    if not isinstance(ts, (int, float)):
        return False
    age = datetime.now(timezone.utc).timestamp() - float(ts)
    return age > COMMODITY_MAX_OBSERVATION_AGE_S


def _commodity_quote_row(code: str, raw: object) -> dict | None:
    rows = raw.get("data") if isinstance(raw, dict) else raw
    if not isinstance(rows, list):
        return None
    points: list[tuple[str, float]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        date = row.get("date")
        try:
            value = float(row.get("value"))
        except (TypeError, ValueError):
            continue
        if isinstance(date, str) and date and math.isfinite(value):
            points.append((date, value))
    points.sort(key=lambda point: point[0])
    if len(points) < 2:
        return None

    _, prev_close = points[-2]
    last_date, last = points[-1]
    if prev_close == 0:
        return None
    try:
        # Date-only FRED observations are stamped at UTC noon to avoid implying
        # a market-session close while still providing a stable epoch `as_of`.
        timestamp = int(
            datetime.strptime(last_date, "%Y-%m-%d")
            .replace(hour=12, tzinfo=timezone.utc)
            .timestamp()
        )
    except ValueError:
        return None
    return {
        "code": code,
        "close": last,
        "previousClose": prev_close,
        "change_p": (last - prev_close) / abs(prev_close) * 100.0,
        "timestamp": timestamp,
    }


def _row_has_no_live_price(row: dict) -> bool:
    """True when EODHD answered with a row that carries no quotable price.

    The vendor signals "I have no live data for this symbol" with the string
    ``"NA"`` in every price field rather than an error or a null, so the row
    looks structurally valid while holding nothing but ``previousClose``.
    Measured 2026-08-18: ``XAUUSD.FOREX`` and ``DXY.INDX`` return NA on every
    call while ``EURUSD.FOREX``, ``GSPC.INDX`` and ``VIX.INDX`` in the same
    batch come back complete, so this is per-symbol coverage, not an outage.

    Accepting such a row is worse than having none: ``normalize_quote`` then
    reports ``last == prev_close`` with a change of exactly 0.00%, which the
    UI renders as a confident "unchanged" tick on a market that has moved.
    """
    close = row.get("close")
    if close is None:
        return True
    return isinstance(close, str) and close.strip().upper() == "NA"


async def _batch_real_time(
    symbols: list[str],
) -> tuple[dict[str, dict], set[str], set[str]]:
    """Return (rows by symbol, symbols EODHD answered for, symbols it fell back for).

    The second value lets the caller tell a genuine no-data miss (chunk
    responded, symbol absent) from a transient batch failure (chunk threw).
    The third covers symbols we handed to the Yahoo fallback: provider
    refusals (402), where EODHD never rendered a verdict, and symbols whose
    row came back priceless (see ``_row_has_no_live_price``).
    """
    pairs = [(sym, resolver.to_eodhd(sym)) for sym in symbols]
    chunks = [pairs[i : i + _BATCH_SIZE] for i in range(0, len(pairs), _BATCH_SIZE)]
    fetched = await asyncio.gather(
        *(eodhd.real_time_batch([code for _, code in chunk]) for chunk in chunks),
        return_exceptions=True,
    )
    result: dict[str, dict] = {}
    queried: set[str] = set()
    fallback_symbols: list[str] = []
    for chunk, rows in zip(chunks, fetched):
        if isinstance(rows, BaseException):
            log.warning("EODHD quote batch failed: %s", rows)
            if isinstance(rows, eodhd.EodhdApiError) and rows.status in (402, 422):
                fallback_symbols.extend(sym for sym, _ in chunk)
            continue
        queried.update(sym for sym, _ in chunk)
        by_code = {r.get("code", ""): r for r in rows}
        for sym, code in chunk:
            row = by_code.get(code)
            # Single-symbol request: EODHD sometimes echoes a normalized code
            # that doesn't string-match ours (exchange-suffix quirks). With
            # exactly one row there's no ambiguity — trust it. Multi-symbol
            # batches keep strict code matching (can't guess which row is which).
            if row is None and len(chunk) == 1 and len(rows) == 1:
                row = rows[0]
            if not row:
                continue
            if _row_has_no_live_price(row):
                fallback_symbols.append(sym)
                continue
            result[sym] = row
    if fallback_symbols:
        try:
            result.update(await _yahoo_quote_rows(fallback_symbols))
        except Exception as exc:
            log.warning("Yahoo quote fallback failed: %s", exc)
    return result, queried, set(fallback_symbols)


async def _yahoo_quote_rows(symbols: list[str]) -> dict[str, dict]:
    return await asyncio.to_thread(_download_yahoo_quote_rows, symbols)


def _finite(value: object) -> float | None:
    try:
        out = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _download_yahoo_quote_rows(symbols: list[str]) -> dict[str, dict]:
    """Quote symbols from Yahoo's quote endpoint, one call per symbol.

    Reads ``fast_info`` rather than differencing a daily bar download, so the
    last price is the live quote instead of an in-progress bar close.

    The previous close comes from ``regularMarketPreviousClose``, NOT from
    ``previousClose``. They are different numbers and only the former is the
    one every venue publishes. Measured 2026-08-18: for SNDK ``previousClose``
    was 1804.00 against a regular-market close of 1786.85, which is a daily
    change of -9.88% versus the -9.01% Google Finance and Yahoo's own site
    both showed; MU disagreed the same way (-7.51% versus -7.02%). The prior
    daily bar close matches ``regularMarketPreviousClose`` exactly on every
    symbol checked, so that is the field the published change is built on.

    Per-symbol calls also contain failure: one unquotable ticker is skipped
    instead of perturbing a shared frame.
    """
    out: dict[str, dict] = {}
    for symbol in symbols:
        try:
            info = yf.Ticker(symbol).fast_info
            last = _finite(info.get("lastPrice"))
            prev_close = _finite(info.get("regularMarketPreviousClose")) or _finite(
                info.get("previousClose")
            )
        except Exception as exc:
            log.warning("Yahoo quote failed for %s: %s", symbol, exc)
            continue
        if last is None or not prev_close:
            continue
        row = {
            "code": resolver.to_eodhd(symbol),
            "close": last,
            "previousClose": prev_close,
            "change_p": (last - prev_close) / abs(prev_close) * 100.0,
            # A live quote is as-of the moment we read it. The old bar-derived
            # stamp reported the last bar's date, which read as days stale.
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
        }
        for key, field in (
            ("open", "open"),
            ("high", "dayHigh"),
            ("low", "dayLow"),
            ("volume", "lastVolume"),
        ):
            value = _finite(info.get(field))
            if value is not None:
                row[key] = int(value) if key == "volume" else value
        out[symbol] = row
    return out


# ── Bars fetching ────────────────────────────────────────────────────


async def fetch_bars_entries(keys: list[str]) -> dict[str, tuple[list[dict], float]]:
    """Store fetcher for ``bars:*`` keys.

    Coverage holes (400/404 upstream, or an empty series) negative-cache an
    empty list so unsupported assets don't re-hit EODHD every cycle;
    transient failures omit the key so the next round retries.
    """
    sem = asyncio.Semaphore(_BARS_CONCURRENCY)
    phase = market_phase()

    async def one(key: str) -> tuple[str, tuple[list[dict], float] | None]:
        symbol = _parse_bars_key(key)
        async with sem:
            try:
                series = await fetch_series(symbol, datetime.now(timezone.utc))
            except eodhd.EodhdApiError as exc:
                if exc.status in (400, 403, 404, 422):
                    return key, ([], UNSUPPORTED_TTL_S)
                log.warning("EODHD bars fetch failed for %s: %s", key, exc)
                return key, None
        if not series:
            return key, ([], UNSUPPORTED_TTL_S)
        return key, (series, bars_ttl(symbol, phase))

    resolved = await asyncio.gather(*(one(k) for k in keys))
    return {key: entry for key, entry in resolved if entry is not None}


async def daily_bars(symbol: str, from_dt: datetime, end_dt: datetime) -> list[dict]:
    """Daily bars for an explicit window, routed by asset class.

    Treasury yields and commodity futures are not on the standard EOD
    endpoint, so each takes its own upstream path.
    """
    if resolver.is_ust_yield(symbol):
        return await _bars_from_yield(from_dt, end_dt)
    if resolver.is_commodity_future(symbol):
        return await _bars_commodity(symbol, from_dt, end_dt)
    if resolver.is_unmapped_future(symbol):
        return []
    return await _bars_standard(symbol, from_dt, end_dt)


async def fetch_series(symbol: str, end_dt: datetime) -> list[dict]:
    """Fetch the canonical series (display window + indicator warm-up prefix).

    Raises EodhdApiError on upstream failure so callers can distinguish
    failures from genuinely empty coverage.
    """
    return await daily_bars(symbol, end_dt - timedelta(days=SERIES_BACK_DAYS), end_dt)


def display_slice(series: list[dict], timeframe: str, end_dt: datetime) -> list[dict]:
    """Project the display window out of a canonical (warm-up-prefixed) series.

    All paths are daily. Comparing on the date prefix keeps the cutoff date
    inclusive and makes the projection robust to legacy cached timestamps.
    """
    cfg = TIMEFRAME_CONFIG[timeframe]
    cutoff = (end_dt - timedelta(days=cfg["display_days"])).strftime("%Y-%m-%d")
    return [b for b in series if b["t"][:10] >= cutoff]


async def _bars_standard(symbol: str, from_dt: datetime, end_dt: datetime) -> list[dict]:
    eodhd_sym = resolver.to_eodhd(symbol)
    raw = await eodhd.eod(
        eodhd_sym,
        period="d",
        from_date=from_dt.strftime("%Y-%m-%d"),
        to_date=end_dt.strftime("%Y-%m-%d"),
    )
    return [_eod_to_bar(r) for r in (raw or []) if _valid_eod(r)]


async def _bars_commodity(
    symbol: str, from_dt: datetime, end_dt: datetime
) -> list[dict]:
    raw = await eodhd.commodities_historical(
        resolver.to_eodhd(symbol),
        from_date=from_dt.strftime("%Y-%m-%d"),
        to_date=end_dt.strftime("%Y-%m-%d"),
    )
    rows = raw.get("data") if isinstance(raw, dict) else raw
    # Like /ust/yield-rates, this endpoint ignores from/to and returns its
    # whole series, so the window is applied here.
    lo = from_dt.strftime("%Y-%m-%d")
    hi = end_dt.strftime("%Y-%m-%d")
    bars = [
        _commodity_to_bar(r)
        for r in (rows or [])
        if _valid_commodity_eod(r) and lo <= r["date"][:10] <= hi
    ]
    bars.sort(key=lambda bar: bar["t"])
    return bars


async def _bars_from_yield(from_dt: datetime, end_dt: datetime) -> list[dict]:
    # /ust/yield-rates is daily-only: one value per day, no OHLCV. The
    # endpoint wraps long-format (date, tenor, rate) rows in a {meta, data}
    # envelope and ignores from/to, so unwrap and filter dates here.
    raw = await eodhd.ust_yield_rates(
        from_date=from_dt.strftime("%Y-%m-%d"),
        to_date=end_dt.strftime("%Y-%m-%d"),
    )
    rows = raw.get("data") if isinstance(raw, dict) else raw
    if not isinstance(rows, list):
        return []
    lo = from_dt.strftime("%Y-%m-%d")
    hi = end_dt.strftime("%Y-%m-%d")
    bars: list[dict] = []
    for r in rows:
        if not isinstance(r, dict) or r.get("tenor") != "10Y":
            continue
        date = r.get("date")
        try:
            v = float(r.get("rate"))
        except (TypeError, ValueError):
            continue
        if not isinstance(date, str) or not lo <= date <= hi or not math.isfinite(v):
            continue
        bars.append({"t": date, "o": v, "h": v, "l": v, "c": v, "v": 0.0})
    bars.sort(key=lambda bar: bar["t"])
    return bars


def _eod_to_bar(r: dict) -> dict:
    return {
        "t": r.get("date", ""),
        "o": float(r.get("open") or 0),
        "h": float(r.get("high") or 0),
        "l": float(r.get("low") or 0),
        "c": float(r.get("adjusted_close") or r.get("close") or 0),
        "v": float(r.get("volume") or 0),
    }


def _commodity_to_bar(r: dict) -> dict:
    value = float(r["value"])
    return {"t": r["date"], "o": value, "h": value, "l": value, "c": value, "v": 0.0}


def _valid_eod(r: dict) -> bool:
    return bool(r.get("date") and (r.get("adjusted_close") or r.get("close")))


def _valid_commodity_eod(r: dict) -> bool:
    if not isinstance(r, dict) or not r.get("date"):
        return False
    try:
        return math.isfinite(float(r.get("value")))
    except (TypeError, ValueError):
        return False
