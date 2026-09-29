import asyncio
import logging
from types import TracebackType
from typing import Any

import aiohttp
from aiohttp_retry import ExponentialRetry, RetryClient
from aiolimiter import AsyncLimiter
from pydantic import BaseModel

from agp_client.models import (
    AgPAuthError,
    AgPClientError,
    AgPRateLimitError,
    AgPRunResult,
    AgPServerError,
    AgPTaskRequest,
)
from agp_client.types import (
    TrajectoryChanges,
    TrajectoryStatus,
)

_LOGGER = logging.getLogger(__name__)


class AgPClientConfig(BaseModel):
    timeout: int = 1200

    # Exponential backoff polling — temporary until webhook/Redis replaces polling
    backoff_initial: float = 5.0
    backoff_maximum: float = 60.0
    backoff_multiplier: float = 1.5

    rate_limit_requests: int = 100
    rate_limit_period: float = 60.0


class AgPClient:
    """Client for AgP (Agent Platform) API. Use as async context manager."""

    def __init__(
        self,
        api_key: str,
        config: AgPClientConfig = AgPClientConfig(),
    ):
        self._base_url = "https://agp.hcompany.ai/api"
        self._headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        self._session: RetryClient | None = None
        self._config = config
        self._rate_limiter = AsyncLimiter(
            max_rate=self._config.rate_limit_requests,
            time_period=self._config.rate_limit_period,
        )

    async def __aenter__(self) -> "AgPClient":
        retry_options = ExponentialRetry(
            attempts=3,
            start_timeout=1.0,
            max_timeout=10.0,
            statuses={408, 429, 500, 502, 503, 504},
        )
        base_session = aiohttp.ClientSession(headers=self._headers)
        self._session = RetryClient(client_session=base_session, retry_options=retry_options)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    def _get_session(self) -> RetryClient:
        if self._session is None:
            raise AgPClientError("Client not initialized. Use 'async with AgPClient(...) as client:'")
        return self._session

    def _raise_for_status(self, status: int, error_text: str, operation: str) -> None:
        if status == 401:
            raise AgPAuthError(f"{operation}: Invalid or expired authentication token")
        elif status == 429:
            raise AgPRateLimitError(f"{operation}: Rate limit exceeded")
        elif 500 <= status < 600:
            raise AgPServerError(f"{operation}: Server error (HTTP {status}): {error_text}")
        else:
            raise AgPClientError(f"{operation}: HTTP {status}: {error_text}")

    async def create_trajectory(
        self,
        agent_identifier: str,
        task: AgPTaskRequest,
    ) -> str:
        session = self._get_session()

        url = f"{self._base_url}/v1/agents/{agent_identifier}/trajectories"
        payload = task.to_api_payload()

        async with self._rate_limiter:
            async with session.post(url, json=payload) as response:
                if not response.ok:
                    error_text = await response.text()
                    self._raise_for_status(response.status, error_text, "create_trajectory")

                data = await response.json()
                trajectory_id: str = data["id"]
                _LOGGER.info(f"[{trajectory_id}] Created trajectory")
                return trajectory_id

    async def _poll_changes(self, trajectory_id: str, from_index: int) -> TrajectoryChanges | None:
        session = self._get_session()
        url = f"{self._base_url}/v1/trajectories/{trajectory_id}/changes"
        async with self._rate_limiter:
            async with session.get(url, params={"from_index": from_index, "include_events": "false"}) as response:
                if response.status == 204:
                    return None
                if not response.ok:
                    error_text = await response.text()
                    self._raise_for_status(response.status, error_text, f"[{trajectory_id[:8]}] poll_changes")
                data = await response.json()
                return TrajectoryChanges.model_validate(data)

    async def _cancel_trajectory(self, trajectory_id: str) -> None:
        session = self._get_session()
        url = f"{self._base_url}/v1/trajectories/{trajectory_id}/status"
        async with self._rate_limiter:
            async with session.put(url, json={"status": TrajectoryStatus.INTERRUPTED.value}) as response:
                if response.status == 404:
                    _LOGGER.debug(f"[{trajectory_id[:8]}] Already finished, cancel ignored")
                    return
                if not response.ok:
                    error_text = await response.text()
                    self._raise_for_status(response.status, error_text, f"[{trajectory_id[:8]}] cancel_trajectory")
                _LOGGER.info(f"[{trajectory_id[:8]}] Cancelled")

    async def wait_for_completion(self, trajectory_id: str) -> AgPRunResult:
        assert self._config.timeout > 0, "timeout must be positive"

        short_id = trajectory_id[:8]
        last_status: TrajectoryStatus | None = None
        answer: str | dict[str, Any] | None = None
        interval = self._config.backoff_initial
        poll_index = 0

        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._config.timeout

        while loop.time() < deadline:
            changes = await self._poll_changes(trajectory_id, poll_index)

            if changes is None:
                _LOGGER.debug(f"[{short_id}] No changes, sleeping {interval:.1f}s")
                await asyncio.sleep(interval)
                interval = min(interval * self._config.backoff_multiplier, self._config.backoff_maximum)
                continue

            interval = self._config.backoff_initial

            if changes.answer:
                answer = changes.answer

            if changes.status != last_status:
                _LOGGER.info(f"[{short_id}] status: {changes.status.value}")
                last_status = changes.status

            if changes.status.is_terminal:
                return AgPRunResult(
                    trajectory_id=trajectory_id,
                    status=changes.status,
                    answer=answer,
                )

            await asyncio.sleep(interval)

        _LOGGER.warning(f"[{short_id}] Timed out after {self._config.timeout}s, cancelling...")
        # Best-effort cancel on timeout
        try:
            await self._cancel_trajectory(trajectory_id)
        except Exception as e:
            _LOGGER.warning(f"[{short_id}] Failed to cancel after timeout: {e}")

        return AgPRunResult(
            trajectory_id=trajectory_id,
            status=TrajectoryStatus.TIMED_OUT,
        )
