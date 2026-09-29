"""Cross-process RPM (requests-per-minute) limiter for the eval pool.

The eval framework spawns N worker processes that each fire LLM API calls in
parallel. Some upstreams (e.g. the gemini-3-flash account capped at 50 RPM)
count *every* request against the quota — including the ones they reject —
so a naive fan-out of 100 envs against 50 RPM spins in a sustained-429 loop
and never makes forward progress. The client must self-throttle.

Design
------
A tiny ``BaseManager`` subclass owns one ``RpmLimiter`` instance. Worker
processes hold a proxy; each ``reserve()`` is one RPC round-trip handled
serially in the manager process, so reads-modify-write of the timestamp
window is atomic by construction (no separate Lock proxy or finicky
ListProxy slice assignments).

The window is a sliding 60s deque of timestamps. ``reserve()`` records the
timestamp **before** the request fires, so server-rejected requests still
consume budget — matching how the upstream account-level quota counts.

Each worker stores the proxy as a module-level singleton via
``set_active_limiter``. Agent ``_call_llm_once`` paths consult it through
``acquire_rpm_slot()`` (a no-op when no limiter is configured, so existing
callers and unit tests are unaffected).
"""
from __future__ import annotations

import logging
import time
from collections import deque
from multiprocessing.managers import BaseManager
from typing import Any, Optional

logger = logging.getLogger("desktopenv.agent")


class RpmLimiter:
    def __init__(self, rpm: int, window_sec: float = 60.0):
        self._rpm = int(rpm)
        self._window = float(window_sec)
        self._stamps: "deque[float]" = deque()

    def reserve(self) -> float:
        """Atomically reserve a request slot.

        Returns 0.0 when a slot was reserved (timestamp recorded). Otherwise
        returns the seconds the caller should sleep before retrying — derived
        from when the oldest in-window request will fall off.
        """
        if self._rpm <= 0:
            return 0.0
        now = time.time()
        cutoff = now - self._window
        while self._stamps and self._stamps[0] <= cutoff:
            self._stamps.popleft()
        if len(self._stamps) < self._rpm:
            self._stamps.append(now)
            return 0.0
        return max(0.05, self._stamps[0] + self._window - now)

    def stats(self) -> tuple[int, int]:
        """Return (current in-window count, configured rpm). For diagnostics."""
        now = time.time()
        cutoff = now - self._window
        while self._stamps and self._stamps[0] <= cutoff:
            self._stamps.popleft()
        return len(self._stamps), self._rpm


class RpmManager(BaseManager):
    pass


RpmManager.register("RpmLimiter", RpmLimiter)


_active_limiter: Optional[Any] = None
_LOG_THRESHOLD_SEC = 1.0


def set_active_limiter(limiter: Optional[Any]) -> None:
    """Install the limiter proxy for this process. Pass ``None`` to disable."""
    global _active_limiter
    _active_limiter = limiter


def acquire_rpm_slot() -> None:
    """Block until a request slot is available under the active limiter; record
    the timestamp atomically before returning. No-op if no limiter is set."""
    lim = _active_limiter
    if lim is None:
        return
    while True:
        wait = lim.reserve()
        if wait <= 0:
            return
        if wait >= _LOG_THRESHOLD_SEC:
            logger.info(
                "RPM cap reached; sleeping %.2fs before next request", wait
            )
        time.sleep(wait)


__all__ = [
    "RpmLimiter",
    "RpmManager",
    "acquire_rpm_slot",
    "set_active_limiter",
]
