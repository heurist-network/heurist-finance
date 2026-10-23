"""US market calendar — local XNYS calendar, no network.

Replaces the EODHD ``/exchange-details`` clock. Holidays and early closes
come from ``exchange_calendars``; open state and next open/close are answered
locally in microseconds, so the refresher and request path can consult the
schedule freely. The calendar is built over a bounded window and rebuilt
lazily as the window ages out.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import exchange_calendars as xcals
import pandas as pd

_WINDOW_BACK = timedelta(days=30)
_WINDOW_FWD = timedelta(days=400)
_REBUILD_MARGIN = timedelta(days=30)

_cal: xcals.ExchangeCalendar | None = None
_cal_end: date | None = None


@dataclass(frozen=True)
class Clock:
    open: bool
    next_open: str | None
    next_close: str | None


def _calendar() -> xcals.ExchangeCalendar:
    global _cal, _cal_end
    today = datetime.now(timezone.utc).date()
    if _cal is None or _cal_end is None or today > _cal_end - _REBUILD_MARGIN:
        start = today - _WINDOW_BACK
        end = today + _WINDOW_FWD
        _cal = xcals.get_calendar("XNYS", start=str(start), end=str(end))
        _cal_end = end
    return _cal


def _ts(at: datetime | None) -> pd.Timestamp:
    if at is None:
        return pd.Timestamp.now(tz="UTC")
    stamp = pd.Timestamp(at)
    return stamp.tz_convert("UTC") if stamp.tzinfo else stamp.tz_localize("UTC")


def is_open(at: datetime | None = None) -> bool:
    return bool(_calendar().is_open_at_time(_ts(at)))


def next_open(at: datetime | None = None) -> datetime:
    return _calendar().next_open(_ts(at)).to_pydatetime()


def next_close(at: datetime | None = None) -> datetime:
    return _calendar().next_close(_ts(at)).to_pydatetime()


def previous_close(at: datetime | None = None) -> datetime:
    return _calendar().previous_close(_ts(at)).to_pydatetime()


def get() -> Clock:
    now = datetime.now(timezone.utc)
    return Clock(
        open=is_open(now),
        next_open=next_open(now).isoformat(),
        next_close=next_close(now).isoformat(),
    )
