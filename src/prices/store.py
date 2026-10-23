"""Snapshot store for price data — stale-while-revalidate semantics.

Entries are ``{value, fetched_at, fresh_until}`` and are never deleted on
read: expiry marks a snapshot stale, it does not evict it (an LRU cap bounds
memory instead). Concurrent fetches for an absent key coalesce onto one
in-flight future (single-flight), and multi-key callers batch their owned
misses into a single upstream call.

The store also tracks the hot set: ``touch()`` records demand, ``hot()``
answers what the background refresher should keep fresh.

Loop-confined by design — all callers (async handlers, the refresher) run on
the one server event loop, so there are no locks. The public surface
(peek/put/touch/hot/fetch_many/refresh_soon) is the seam for a Redis
implementation at the multi-worker milestone.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)

_MAX_ENTRIES = 4096

# Batch fetcher contract: keys -> {key: (value, ttl_s)}. A key absent from
# the result is an upstream failure for this round — its future resolves to
# None and nothing is stored, so a later attempt retries.
Fetcher = Callable[[list[str]], Awaitable[dict[str, tuple[Any, float]]]]


@dataclass(frozen=True, slots=True)
class Snapshot:
    value: Any
    fetched_at: float  # epoch seconds
    fresh_until: float  # epoch seconds

    @property
    def stale(self) -> bool:
        return time.time() >= self.fresh_until


class SnapshotStore:
    def __init__(self, max_entries: int = _MAX_ENTRIES) -> None:
        self._entries: OrderedDict[str, Snapshot] = OrderedDict()
        self._max_entries = max_entries
        self._inflight: dict[str, asyncio.Future] = {}
        self._touched: dict[str, float] = {}
        self._touched_bars: dict[str, float] = {}
        self._refresh_tasks: set[asyncio.Task] = set()

    def peek(self, key: str) -> Snapshot | None:
        snap = self._entries.get(key)
        if snap is not None:
            self._entries.move_to_end(key)
        return snap

    def put(
        self,
        key: str,
        value: Any,
        ttl_s: float,
        *,
        fetched_at: float | None = None,
    ) -> Snapshot:
        now = time.time()
        snap = Snapshot(
            value=value,
            fetched_at=fetched_at if fetched_at is not None else now,
            fresh_until=now + ttl_s,
        )
        self._entries[key] = snap
        self._entries.move_to_end(key)
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)
        return snap

    # ── hot set ──────────────────────────────────────────────────────

    def touch(self, symbols: list[str], *, bars: bool = False) -> None:
        """Record demand. ``bars=True`` additionally marks sparkline/chart
        demand — only these symbols drive the refresher's per-symbol daily
        fetches, so a quote-only consumer doesn't multiply upstream load."""
        now = time.monotonic()
        for sym in symbols:
            self._touched[sym] = now
            if bars:
                self._touched_bars[sym] = now

    def hot(self, within_s: float) -> list[str]:
        return self._hot(self._touched, within_s)

    def hot_bars(self, within_s: float) -> list[str]:
        return self._hot(self._touched_bars, within_s)

    @staticmethod
    def _hot(touched: dict[str, float], within_s: float) -> list[str]:
        cutoff = time.monotonic() - within_s
        # Prune while answering so the map tracks the hot set, not history.
        cold = [s for s, t in touched.items() if t < cutoff]
        for s in cold:
            del touched[s]
        return list(touched)

    # ── single-flight fetch ──────────────────────────────────────────

    async def fetch_many(
        self, keys: list[str], fetcher: Fetcher
    ) -> dict[str, Snapshot | None]:
        """Fetch absent keys, coalescing with concurrent callers.

        Returns key -> Snapshot, or None where upstream failed. Keys already
        in flight are awaited, not re-fetched; the rest go to `fetcher` as
        one batch.
        """
        loop = asyncio.get_running_loop()
        futures: dict[str, asyncio.Future] = {}
        mine: list[str] = []
        for key in keys:
            fut = self._inflight.get(key)
            if fut is None:
                fut = loop.create_future()
                self._inflight[key] = fut
                mine.append(key)
            futures[key] = fut

        if mine:
            results: dict[str, tuple[Any, float]] = {}
            try:
                results = await fetcher(mine)
            except Exception:
                log.warning("price snapshot fetch failed: %s", mine, exc_info=True)
            finally:
                # Resolve unconditionally (even on cancellation) so waiters
                # coalesced onto these futures never hang.
                for key in mine:
                    fut = self._inflight.pop(key, None)
                    if fut is None or fut.done():
                        continue
                    got = results.get(key)
                    fut.set_result(
                        self.put(key, got[0], got[1]) if got is not None else None
                    )

        return {key: await fut for key, fut in futures.items()}

    def refresh_soon(self, key: str, fetcher: Fetcher) -> None:
        """Fire-and-forget refresh of a stale entry; never blocks the caller.

        Coalesces with any in-flight fetch for the same key.
        """
        if key in self._inflight:
            return
        task = asyncio.get_running_loop().create_task(self.fetch_many([key], fetcher))
        self._refresh_tasks.add(task)
        task.add_done_callback(self._refresh_tasks.discard)

    def clear(self) -> None:
        self._entries.clear()
        self._touched.clear()
        self._touched_bars.clear()
        self._inflight.clear()
        self._refresh_tasks.clear()


store = SnapshotStore()

# The server event loop the store is confined to. Bound once at app startup
# so threadpool code (sync routes, agent tools) can reach the store via
# ``asyncio.run_coroutine_threadsafe`` instead of duplicating upstream fetches.
_server_loop: asyncio.AbstractEventLoop | None = None


def bind_server_loop() -> None:
    global _server_loop
    _server_loop = asyncio.get_running_loop()


def server_loop() -> asyncio.AbstractEventLoop | None:
    # `is_running` matters as much as `is_closed`: a stopped-but-open loop
    # accepts work it will never execute, so a caller would block on the
    # future until its timeout instead of taking the direct path.
    if _server_loop is None or _server_loop.is_closed() or not _server_loop.is_running():
        return None
    return _server_loop


def run_sync(make_coro, timeout: float = 10.0):
    """Run a store coroutine from a sync caller.

    Uses the loop that owns the store when one is bound, so sync routes and
    agent tools share its cache. Scripts and tests have no such loop and get a
    throwaway one.
    """
    loop = server_loop()
    if loop is None:
        return asyncio.run(make_coro())
    return asyncio.run_coroutine_threadsafe(make_coro(), loop).result(timeout=timeout)
