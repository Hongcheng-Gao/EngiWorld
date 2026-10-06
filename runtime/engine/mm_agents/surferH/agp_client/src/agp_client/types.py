import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class TrajectoryStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    INTERRUPTED = "interrupted"

    @property
    def is_terminal(self) -> bool:
        return self in {
            TrajectoryStatus.COMPLETED,
            TrajectoryStatus.FAILED,
            TrajectoryStatus.TIMED_OUT,
            TrajectoryStatus.INTERRUPTED,
        }


class TrajectoryChanges(BaseModel):
    status: TrajectoryStatus
    started_at: datetime.datetime | None = None
    finished_at: datetime.datetime | None = None
    answer: str | dict[str, Any] | None = None
