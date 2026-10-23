"""Process-local EODHD call counters + periodic jsonl deltas.

Every HTTP attempt (including retries) bumps an in-memory window. At most once
per ``FLUSH_INTERVAL_S`` (lazy, on the next attempt), or on forced flush /
process exit, a **delta-only** line is appended to ``logs/eodhd-metrics.jsonl``.

Operators get daily / multi-hour burn by **summing ``delta`` fields** across
lines in a UTC window — there are no process-lifetime totals on disk.

Billable ``call_units`` follow EODHD's published rules for the endpoints we
use: multi-ticker live is 1 unit per symbol; intraday is 5 units per request;
other endpoints we hit are 1 unit per request.
"""

from __future__ import annotations

import atexit
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "logs"
METRICS_PATH = LOG_DIR / "eodhd-metrics.jsonl"
FLUSH_INTERVAL_S = 60.0

logger = logging.getLogger("hf.eodhd_metrics")

_lock = threading.Lock()
# (endpoint, status) -> {"requests": int, "call_units": int}
_window: dict[tuple[str, str], dict[str, int]] = {}
_window_started: float | None = None
_last_flush_at: float = 0.0
_atexit_registered = False


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def endpoint_from_path(path: str) -> str:
    """Collapse ``real-time/AAPL.US`` → ``real-time`` (low-cardinality)."""
    parts = [p for p in path.lstrip("/").split("/") if p]
    if not parts:
        return "unknown"
    # Multi-segment fixed paths (no per-symbol tail to strip).
    if parts[:2] == ["commodities", "historical"]:
        return "commodities/historical"
    if parts[:2] == ["ust", "yield-rates"]:
        return "ust/yield-rates"
    return parts[0]


def symbol_count(path: str, params: dict[str, Any] | None) -> int:
    """How many symbols this request covers (real-time multi-ticker via ``s=``)."""
    endpoint = endpoint_from_path(path)
    extra = (params or {}).get("s")
    if endpoint == "us-quote-delayed":
        return max(
            sum(1 for token in str(extra or "").split(",") if token.strip()),
            1,
        )
    if endpoint != "real-time":
        return 1
    n = 1
    if extra:
        n += sum(1 for tok in str(extra).split(",") if tok.strip())
    return max(n, 1)


def call_units_for(endpoint: str, symbols: int) -> int:
    if endpoint == "intraday":
        return 5 * max(symbols, 1)
    return max(symbols, 1)


def status_label(status: int | None, *, transport: bool = False) -> str:
    if transport:
        return "transport"
    if status is None:
        return "error"
    if status < 400:
        return "ok"
    if status in (402, 403, 404, 429):
        return str(status)
    if status < 500:
        return "4xx"
    return "5xx"


def _ensure_atexit() -> None:
    """Flush unwritten deltas when short-lived processes exit (probe, scripts)."""
    global _atexit_registered
    if _atexit_registered:
        return
    atexit.register(_atexit_flush)
    _atexit_registered = True


def _atexit_flush() -> None:
    flush(force=True)


def _bump(
    bucket: dict[tuple[str, str], dict[str, int]],
    endpoint: str,
    status: str,
    *,
    requests: int,
    call_units: int,
) -> None:
    key = (endpoint, status)
    row = bucket.get(key)
    if row is None:
        row = {"requests": 0, "call_units": 0}
        bucket[key] = row
    row["requests"] += requests
    row["call_units"] += call_units


def _rollup(bucket: dict[tuple[str, str], dict[str, int]]) -> dict[str, Any]:
    by_endpoint: dict[str, dict[str, int]] = {}
    requests = 0
    call_units = 0
    by_status: dict[str, int] = {}
    for (endpoint, status), row in sorted(bucket.items()):
        ep = by_endpoint.setdefault(endpoint, {"requests": 0, "call_units": 0})
        ep["requests"] += row["requests"]
        ep["call_units"] += row["call_units"]
        ep[status] = ep.get(status, 0) + row["requests"]
        requests += row["requests"]
        call_units += row["call_units"]
        by_status[status] = by_status.get(status, 0) + row["requests"]
    return {
        "requests": requests,
        "call_units": call_units,
        "by_endpoint": by_endpoint,
        "by_status": by_status,
    }


def record_attempt(
    path: str,
    params: dict[str, Any] | None = None,
    *,
    status: int | None = None,
    transport: bool = False,
) -> None:
    """Count one upstream HTTP attempt. Never raises."""
    try:
        _ensure_atexit()
        endpoint = endpoint_from_path(path)
        symbols = symbol_count(path, params)
        units = call_units_for(endpoint, symbols)
        label = status_label(status, transport=transport)
        now = time.time()
        with _lock:
            global _window_started, _last_flush_at
            if _window_started is None:
                _window_started = now
            _bump(_window, endpoint, label, requests=1, call_units=units)
            # Start the flush clock on the first attempt; write only after the
            # interval (lazy periodic — no background thread). Exit/aclose
            # force-flush covers short-lived processes that never hit the
            # interval.
            if _last_flush_at == 0.0:
                _last_flush_at = now
            elif now - _last_flush_at >= FLUSH_INTERVAL_S:
                _flush_locked(now)
    except Exception:
        logger.warning("eodhd metrics record failed", exc_info=True)


def _flush_locked(now: float) -> bool:
    """Single write path: emit one delta line if the window is non-empty.

    Caller holds ``_lock``. Empty windows never write (no idle zero lines).
    On write failure the window is kept so a later flush can retry.
    """
    global _window, _window_started, _last_flush_at
    if not _window:
        _last_flush_at = now
        return False
    started = _window_started if _window_started is not None else now
    payload = {
        "ts": _utc_now(),
        "event": "eodhd_usage",
        "window_s": round(max(now - started, 0.0), 3),
        "delta": _rollup(_window),
    }
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with METRICS_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, sort_keys=True) + "\n")
    except Exception:
        logger.warning("failed to append eodhd metrics", exc_info=True)
        return False
    _window = {}
    _window_started = now
    _last_flush_at = now
    return True


def flush(*, force: bool = False) -> bool:
    """Flush the current window via the single write path.

    ``force=True`` ignores the interval (exit / aclose). Always skips empty
    windows. Returns True only when a line was written.
    """
    try:
        with _lock:
            now = time.time()
            if (
                not force
                and _last_flush_at != 0.0
                and (now - _last_flush_at) < FLUSH_INTERVAL_S
            ):
                return False
            return _flush_locked(now)
    except Exception:
        logger.warning("eodhd metrics flush failed", exc_info=True)
        return False


def snapshot() -> dict[str, Any]:
    """Unflushed window counters (for tests / ad-hoc inspection)."""
    with _lock:
        return {
            "window": _rollup(_window),
            "window_started": _window_started,
            "last_flush_at": _last_flush_at,
            "metrics_path": str(METRICS_PATH),
        }


def reset_for_tests() -> None:
    """Clear the window. Tests only. Does not unregister atexit."""
    global _window, _window_started, _last_flush_at
    with _lock:
        _window = {}
        _window_started = None
        _last_flush_at = 0.0


__all__ = [
    "FLUSH_INTERVAL_S",
    "METRICS_PATH",
    "call_units_for",
    "endpoint_from_path",
    "flush",
    "record_attempt",
    "reset_for_tests",
    "snapshot",
    "status_label",
    "symbol_count",
]
