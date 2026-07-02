"""Shared retry primitives for agent LLM calls.

The agents in this package treat an empty / whitespace-only LLM response as
a soft refusal (typically a silently-swallowed rate-limit, content filter, or
upstream error). Each agent decides locally how to detect emptiness — the
shape of the SDK return differs (str / dict / SDK object) — and raises
``EmptyResponseError`` so the retry policy retries with exponential backoff +
jitter instead of returning ``""`` and dropping the step.

Two entry points are provided:

* ``llm_retry`` — a decorator with a fixed ``max_attempts``. Convenient for
  module-level / class-level cases where the budget is known at import time.
* ``make_llm_retry`` — a ``tenacity.Retrying`` factory. Use as
  ``for attempt in make_llm_retry(max_attempts=self.max_retries, ...): with attempt: ...``
  when the retry budget is per-instance (e.g. driven by a CLI flag).

Both share the same backoff schedule: exponential with full jitter, capped at
``max_wait`` seconds. With ``max_wait=60`` and ``initial=1``, attempts settle
to a uniform ~30s mean wait once past the ramp-up — useful when sustained
rate-limits force the call rate down to the API's allowed RPM.
"""
from __future__ import annotations

import logging
from typing import Tuple, Type

from tenacity import (
    Retrying,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)


class EmptyResponseError(RuntimeError):
    """LLM returned an empty/whitespace response. Treated as a transient refusal."""


_DEFAULT_EXCEPTIONS: Tuple[Type[BaseException], ...] = (EmptyResponseError,)


def make_llm_retry(
    *,
    exceptions: Tuple[Type[BaseException], ...] = _DEFAULT_EXCEPTIONS,
    max_attempts: int = 10,
    initial_wait: float = 1.0,
    max_wait: float = 60.0,
    logger_name: str = "desktopenv.agent",
) -> Retrying:
    """Build a fresh :class:`tenacity.Retrying` for one LLM call.

    Iterate over the returned object as ``for attempt in make_llm_retry(...):
    with attempt: ...``. ``max_attempts`` is read at call time, so the same
    agent instance can use a per-run budget threaded in via ``--llm_retries``.
    """
    sleep_logger = logging.getLogger(logger_name)
    return Retrying(
        retry=retry_if_exception_type(exceptions),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(initial=initial_wait, max=max_wait),
        before_sleep=before_sleep_log(sleep_logger, logging.WARNING),
        reraise=True,
    )


def llm_retry(
    *,
    exceptions: Tuple[Type[BaseException], ...] = _DEFAULT_EXCEPTIONS,
    max_attempts: int = 10,
    initial_wait: float = 1.0,
    max_wait: float = 60.0,
    logger_name: str = "desktopenv.agent",
):
    """Decorator form. ``max_attempts`` is fixed at decoration time; for a
    runtime-configurable budget, use :func:`make_llm_retry` inside the method."""
    sleep_logger = logging.getLogger(logger_name)
    return retry(
        retry=retry_if_exception_type(exceptions),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(initial=initial_wait, max=max_wait),
        before_sleep=before_sleep_log(sleep_logger, logging.WARNING),
        reraise=True,
    )
