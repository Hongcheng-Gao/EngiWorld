"""Task time budgets exclude registered framework pauses, never agent WAIT actions."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import json
import signal
import time


BUDGET_EXHAUSTED = "active_time_budget_exhausted"
LEDGER_FIELD = "active_time_ledger"
_pause_callback = ContextVar("engiworld_pause_callback", default=None)


class ActiveTimeBudgetExceeded(BaseException):
    """Escape nested action/API exception handlers when the task budget is used."""


class PauseTrackingError(RuntimeError):
    error_category = "infra"


def _matching_ledger(raw, field):
    ledger = json.loads(raw.get(field) or "{}")
    if not ledger:
        return {}
    if (str(ledger.get("attempt")) != str(raw.get("attempt"))
            or ledger.get("instance_id") != raw.get("instance_id")):
        return {}  # A new attempt must not inherit another attempt's pauses.
    tolerance = 1.0 if field == "user_active_time_ledger" else 0.0
    if abs(float(ledger["original_started_at"]) - float(raw["started_at"])) > tolerance:
        raise PauseTrackingError("Task start changed within the same active-time ledger")
    return ledger


def pause_mapping(raw, reason: str, paused: bool, now: float):
    """Update one pause reason; overlapping reasons are deducted only once."""
    ledger = _matching_ledger(raw, LEDGER_FIELD) or {
        "attempt": str(raw["attempt"]), "instance_id": raw["instance_id"],
        "original_started_at": float(raw["started_at"]), "closed": [], "open": {},
    }
    opened = ledger["open"]
    if paused:
        opened.setdefault(reason, float(now))
    elif reason in opened:
        start = opened.pop(reason)
        if now < start:
            raise PauseTrackingError("Pause end precedes its start")
        ledger["closed"].append([start, float(now)])
    return {LEDGER_FIELD: json.dumps(ledger, separators=(",", ":"))}


def active_time_metrics(raw, now: float):
    start = float(raw.get("started_at") or 0)
    if not start:
        return {"wall_duration_seconds": 0.0, "paused_seconds": 0.0,
                "active_duration_seconds": 0.0}
    end = max(start, float(now))
    intervals = []
    ledger = _matching_ledger(raw, LEDGER_FIELD)
    if ledger:
        intervals.extend(ledger["closed"])
        intervals.extend((value, end) for value in ledger["open"].values())
    # Read the late-main-experiment ledger without changing its attempt/start.
    legacy = _matching_ledger(raw, "user_active_time_ledger")
    if legacy:
        intervals.extend((item["start"], item["end"]) for item in legacy["closed"])
        if legacy.get("open") and raw.get("user_paused") == "1":
            intervals.append((legacy["open"]["start"], end))
    if raw.get("user_paused") == "1" and float(raw.get("user_paused_at") or 0) > 0:
        intervals.append((float(raw["user_paused_at"]), end))
    merged = []
    for left, right in sorted((max(start, float(a)), min(end, float(b))) for a, b in intervals):
        if right <= left:
            continue
        if merged and left <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], right)
        else:
            merged.append([left, right])
    paused = sum(right - left for left, right in merged)
    return {"wall_duration_seconds": end - start, "paused_seconds": paused,
            "active_duration_seconds": end - start - paused}


def budget_outcome():
    return {"evaluation_status": "completed", "score": 0.0,
            "failure_reason_code": BUDGET_EXHAUSTED,
            "scoring_basis": "active_time_budget", "native_evaluator_executed": False}


@contextmanager
def track_task_pauses(callback):
    counts = {}

    def transition(reason, paused):
        count = counts.get(reason, 0)
        if paused:
            if not count:
                callback(reason, True)
            counts[reason] = count + 1
        elif count:
            if count == 1:
                callback(reason, False)
                counts.pop(reason)
            else:
                counts[reason] = count - 1

    token = _pause_callback.set(transition)
    try:
        yield
    finally:
        _pause_callback.reset(token)


@contextmanager
def task_paused(reason: str):
    """Register before waiting/stopping; close the same interval on resume."""
    callback = _pause_callback.get()
    if callback is None:
        yield
        return
    callback(reason, True)
    try:
        yield
    finally:
        callback(reason, False)


class ActiveTaskDeadline:
    """Linux local-run deadline, using monotonic time and pause-aware SIGALRM."""

    def __init__(self, seconds):
        self.seconds = float(seconds)
        self.started = time.monotonic()
        self.paused_seconds = 0.0
        self.pause_started = None
        self.reasons = {}
        self.stopped = None

    def metrics(self):
        end = self.stopped if self.stopped is not None else time.monotonic()
        paused = self.paused_seconds
        if self.pause_started is not None:
            paused += end - self.pause_started
        wall = max(0.0, end - self.started)
        return {"wall_duration_seconds": wall, "paused_seconds": paused,
                "active_duration_seconds": max(0.0, wall - paused)}

    def _arm(self):
        remaining = self.seconds - self.metrics()["active_duration_seconds"]
        if remaining <= 0:
            raise ActiveTimeBudgetExceeded(f"Task used {self.seconds:g} active seconds")
        signal.setitimer(signal.ITIMER_REAL, remaining)

    def pause(self, reason, paused):
        if paused:
            if not self.reasons:
                # Do not let a pause entered after exhaustion hide a spent budget.
                self._arm()
                signal.setitimer(signal.ITIMER_REAL, 0)
                self.pause_started = time.monotonic()
            self.reasons[reason] = self.reasons.get(reason, 0) + 1
        else:
            count = self.reasons.get(reason, 0)
            if count <= 1:
                self.reasons.pop(reason, None)
            else:
                self.reasons[reason] = count - 1
            if not self.reasons and self.pause_started is not None:
                self.paused_seconds += time.monotonic() - self.pause_started
                self.pause_started = None
                self._arm()

    def _expired(self, signum, frame):
        self.stopped = time.monotonic()
        raise ActiveTimeBudgetExceeded(f"Task used {self.seconds:g} active seconds")

    @contextmanager
    def running(self):
        previous = signal.signal(signal.SIGALRM, self._expired)
        try:
            self.started = time.monotonic()
            self._arm()
            with track_task_pauses(self.pause):
                yield self
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            if self.stopped is None:
                self.stopped = time.monotonic()
            signal.signal(signal.SIGALRM, previous)
