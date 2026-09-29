"""Shared scheduler schemas.

These types describe EngiWorld tasks, GUI/CLI agent settings, environments,
and evaluation results. Task definitions live in the release task directory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RunStatus(str, Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    DRAINING = "draining"
    COMPLETED = "completed"
    FAILED = "failed"
    TEARING_DOWN = "tearing_down"


class TaskStatus(str, Enum):
    PENDING = "pending"
    LEASED = "leased"
    RUNNING = "running"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    API_INCOMPLETE = "api_incomplete"
    INFRA_INCOMPLETE = "infra_incomplete"
    DEAD_LETTER = "dead_letter"


class InstanceStatus(str, Enum):
    PROVISIONING = "provisioning"
    AVAILABLE = "available"
    LEASED = "leased"
    RECYCLING = "recycling"
    QUARANTINED = "quarantined"
    TERMINATING = "terminating"
    TERMINATED = "terminated"


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    domain: str
    example_id: str
    max_attempts: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InstanceRecord:
    instance_id: str
    private_ip: str
    os_type: str = "Ubuntu"
    public_ip: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentConfig:
    name: str = "example-rl-agent"
    agent_factory: str | None = None
    checkpoint_path: str | None = None
    platform: str | None = None
    action_space: str = "computer_13"
    observation_type: str = "screenshot"
    eval_mode: str = "gui"
    experiment_profile: str | None = None
    max_steps: int = 15
    gui_max_steps: int | None = None
    cli_max_steps: int | None = None
    gui_multi_max_steps: int | None = None
    cli_multi_max_steps: int | None = None
    open_ended_max_steps: int | None = None
    # Historical run records used this name for Open-ended tasks.
    top10_max_steps: int | None = None
    # Retained so retry runs serialized by older masters remain readable.
    open_max_steps: int | None = None
    multi_max_steps: int | None = None
    history_turns: int | None = None
    bash_timeout: int = 120
    record_video: bool = True
    resume: bool = False
    sleep_after_execution: float = 2.0
    screen_width: int = 1920
    screen_height: int = 1080
    headless: bool = True
    client_password: str | None = None
    vm_secret_mounts: list[str] | None = None


@dataclass(frozen=True)
class EvalConfig:
    run_id: str
    benchmark: str = "engiworld"
    engine_path: str = "engine"
    osworld_path: str | None = None  # Compatibility with saved run configurations.
    osworld_v2_path: str = "third_party/OSWorld-V2"
    task_root: str = "task"
    test_config_base_dir: str = "evaluation_examples"
    test_all_meta_path: str = "evaluation_examples/test_all.json"
    result_dir: str = "results"
    redis_url: str = "redis://127.0.0.1:6379/0"
    s3_bucket: str = "agent-eval-results"
    s3_upload: bool = True
    keep_local_results: bool = False


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    domain: str
    example_id: str
    score: float | None
    result_dir: str
    artifact_uri: str | None = None
    error: str | None = None
    error_category: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None
