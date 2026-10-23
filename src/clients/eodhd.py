"""EODHD Financial Data API client.

Single paid API key (``EODHD_API_KEY`` — EOD+Intraday All World Extended).
The price path is async on one shared keep-alive ``AsyncClient`` so batched
fan-out never pays per-call TCP+TLS handshakes. Intraday from/to are Unix
seconds; EOD from/to are ISO dates.

Retry policy: 429/5xx and transport errors retry with backoff (429 honors
``Retry-After``). Other 4xx never retry — 403 in particular means the
endpoint is not in our subscription tier, and callers may branch on
``EodhdApiError.status``.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from src import config
from src.clients import eodhd_metrics

BASE = "https://eodhd.com/api"
_TIMEOUT = 15.0
_MAX_ATTEMPTS = 3
_BACKOFF_S = 0.5

_client: httpx.AsyncClient | None = None
_client_loop: asyncio.AbstractEventLoop | None = None


class EodhdApiError(Exception):
    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def _api_key() -> str:
    key = (config.EODHD_API_KEY or "").strip()
    if not key:
        raise EodhdApiError("EODHD_API_KEY not set")
    return key


def _params(params: dict[str, Any] | None) -> dict[str, Any]:
    p = dict(params or {})
    p.setdefault("fmt", "json")
    p["api_token"] = _api_key()
    return p


def _retry_delay(resp: httpx.Response | None, attempt: int) -> float:
    if resp is not None and resp.status_code == 429:
        try:
            return max(float(resp.headers.get("Retry-After", "")), _BACKOFF_S)
        except ValueError:
            pass
    return _BACKOFF_S * (2**attempt)


def _get_client() -> httpx.AsyncClient:
    # Re-create if bound to a dead loop (tests run one loop per case).
    global _client, _client_loop
    loop = asyncio.get_running_loop()
    if _client is None or _client.is_closed or _client_loop is not loop:
        _client = httpx.AsyncClient(
            base_url=BASE,
            timeout=_TIMEOUT,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=10),
        )
        _client_loop = loop
    return _client


async def aclose() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None
    # Best-effort: dump any unflushed window so a restart does not lose the
    # last <FLUSH_INTERVAL_S of attempts.
    eodhd_metrics.flush(force=True)


async def _call(path: str, params: dict[str, Any] | None = None) -> Any:
    p = _params(params)
    # Strip the token before metrics so call-unit math still sees ``s=`` but
    # we never log credentials if a future writer dumps params.
    metric_params = {k: v for k, v in p.items() if k != "api_token"}
    url = f"/{path.lstrip('/')}"
    for attempt in range(_MAX_ATTEMPTS):
        last = attempt == _MAX_ATTEMPTS - 1
        try:
            resp = await _get_client().get(url, params=p)
        except httpx.RequestError as exc:
            eodhd_metrics.record_attempt(path, metric_params, transport=True)
            if last:
                raise EodhdApiError(f"EODHD request failed: {path}") from exc
            await asyncio.sleep(_retry_delay(None, attempt))
            continue
        eodhd_metrics.record_attempt(path, metric_params, status=resp.status_code)
        if resp.status_code == 429 or resp.status_code >= 500:
            if last:
                raise EodhdApiError(
                    f"EODHD {resp.status_code}: {path}", status=resp.status_code
                )
            await asyncio.sleep(_retry_delay(resp, attempt))
            continue
        if resp.status_code >= 400:
            raise EodhdApiError(
                f"EODHD {resp.status_code}: {path}", status=resp.status_code
            )
        return resp.json()
    raise EodhdApiError(f"EODHD retries exhausted: {path}")  # unreachable


def _normalize_rows(raw: Any) -> list[dict]:
    if isinstance(raw, dict):
        return [raw]
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    return []


async def real_time_batch(symbols: list[str]) -> list[dict]:
    """Fetch quotes for up to ~15 EODHD symbols in one call.

    Returns raw EODHD quote dicts. Single-symbol responses come back as an
    object; we normalize to a list in all cases.
    """
    if not symbols:
        return []
    primary, *rest = symbols
    params: dict[str, Any] = {}
    if rest:
        params["s"] = ",".join(rest)
    return _normalize_rows(await _call(f"real-time/{primary}", params))


async def us_quote_batch(symbols: list[str]) -> dict[str, dict]:
    """Fetch the extended US quote snapshot for ``symbols``.

    The upstream response is keyed by EODHD symbol under ``data``.  Keep the
    provider-specific endpoint name inside this client; callers consume a
    neutral rich-quote contract.
    """
    if not symbols:
        return {}
    raw = await _call("us-quote-delayed", {"s": ",".join(symbols)})
    data = raw.get("data") if isinstance(raw, dict) else None
    if not isinstance(data, dict):
        return {}
    return {str(code): row for code, row in data.items() if isinstance(row, dict)}


async def intraday(
    symbol: str,
    *,
    interval: str,
    from_ts: int,
    to_ts: int,
) -> list[dict]:
    return await _call(
        f"intraday/{symbol}",
        {"interval": interval, "from": from_ts, "to": to_ts},
    )


async def eod(
    symbol: str,
    *,
    period: str = "d",
    from_date: str,
    to_date: str,
) -> list[dict]:
    return await _call(
        f"eod/{symbol}", {"period": period, "from": from_date, "to": to_date}
    )


async def commodities_historical(
    code: str,
    *,
    from_date: str,
    to_date: str,
) -> list[dict]:
    return await _call(
        f"commodities/historical/{code}",
        {"interval": "daily", "from": from_date, "to": to_date},
    )


async def ust_yield_rates(*, from_date: str, to_date: str) -> list[dict]:
    return await _call("ust/yield-rates", {"from": from_date, "to": to_date})


__all__ = [
    "EodhdApiError",
    "aclose",
    "commodities_historical",
    "eod",
    "intraday",
    "real_time_batch",
    "us_quote_batch",
    "ust_yield_rates",
]
