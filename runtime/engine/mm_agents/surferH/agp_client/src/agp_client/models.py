from typing import Any, Literal

from pydantic import BaseModel

from agp_client.types import TrajectoryStatus


class DirectEnvironmentConnection(BaseModel):
    """Direct URL environment connection."""

    type: Literal["direct_url"] = "direct_url"
    url: str
    api_key: str | None = None

class AgPTaskRequest(BaseModel):
    objective: str
    start_url: str | None = None
    is_public: bool = False
    environment: DirectEnvironmentConnection | None = None

    def public(self) -> "AgPTaskRequest":
        return self.model_copy(update={"is_public": True})

    def to_api_payload(self) -> dict[str, Any]:
        task_payload: dict[str, Any] = {
            "objective": self.objective,
        }
        if self.start_url is not None:
            task_payload["start_url"] = self.start_url

        payload: dict[str, Any] = {
            "task": task_payload,
            "is_public": self.is_public,
        }

        if self.environment is not None:
            payload["environment"] = self.environment.model_dump(mode="json")

        return payload


class AgPRunResult(BaseModel):
    trajectory_id: str
    status: TrajectoryStatus
    answer: str | dict[str, Any] | None = None

    @property
    def success(self) -> bool:
        return self.status == TrajectoryStatus.COMPLETED


class AgPClientError(Exception):
    pass


class AgPAuthError(AgPClientError):
    pass


class AgPRateLimitError(AgPClientError):
    pass


class AgPServerError(AgPClientError):
    pass
