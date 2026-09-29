"""Isolated single-task runner for OSWorld V2 Python task classes."""

from __future__ import annotations

import contextlib
import json
import multiprocessing
import os
import queue
import shutil
import sys
import traceback
from dataclasses import replace
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from engiworld.scheduler.schemas import AgentConfig, EvalConfig, InstanceRecord, TaskResult, TaskSpec
from engiworld.scheduler.task_loader import _load_v2_task_class


def run_single_task_v2(
    task: TaskSpec,
    instance: InstanceRecord,
    eval_config: EvalConfig,
    agent_config: AgentConfig,
) -> TaskResult:
    """Execute V2 in a clean interpreter so V1/V2 module names never collide."""
    ctx = multiprocessing.get_context("spawn")
    result_queue = ctx.Queue(maxsize=1)
    process = ctx.Process(
        target=_run_v2_child,
        args=(result_queue, task, instance, eval_config, agent_config),
        name=f"arena-osworld-v2-{_safe_path_component(task.task_id)}",
    )
    process.start()
    process.join()
    try:
        payload = result_queue.get(timeout=1)
    except queue.Empty:
        payload = None
    finally:
        result_queue.close()

    if isinstance(payload, dict):
        return TaskResult(**payload)
    result_dir = _result_dir(task, eval_config, agent_config)
    result_dir.mkdir(parents=True, exist_ok=True)
    error = f"OSWorld V2 child runner exited with code {process.exitcode} without a result payload"
    (result_dir / "runner_error.txt").write_text(error + "\n", encoding="utf-8")
    return TaskResult(task.task_id, task.domain, task.example_id, 0.0, str(result_dir), error=error)


def _run_v2_child(
    result_queue: Any,
    task: TaskSpec,
    instance: InstanceRecord,
    eval_config: EvalConfig,
    agent_config: AgentConfig,
) -> None:
    result_dir = _result_dir(task, eval_config, agent_config)
    result_dir.mkdir(parents=True, exist_ok=True)
    cache_root = result_dir / ".osworld-cache"
    env = None
    try:
        v2_path = Path(eval_config.osworld_v2_path).expanduser().resolve()
        if not v2_path.exists():
            raise FileNotFoundError(f"OSWorld V2 checkout not found: {v2_path}")
        sys.path.insert(0, str(v2_path))
        _clear_conflicting_modules()
        import lib_run_single
        from desktop_env.desktop_env import DesktopEnv
        from desktop_env.task_base import BaseTask

        task_path = Path(eval_config.task_root).expanduser().resolve() / str(task.metadata["task_path"])
        example = _load_v2_task_class(task_path, BaseTask)
        task_agent_config = _agent_config_for_instance(agent_config, instance, task)
        agent = _load_agent(task_agent_config)
        args = SimpleNamespace(
            action_space=task_agent_config.action_space,
            observation_type=task_agent_config.observation_type,
            model=task_agent_config.name,
            platform=task_agent_config.platform,
            max_steps=task_agent_config.max_steps,
            sleep_after_execution=task_agent_config.sleep_after_execution,
            screen_width=task_agent_config.screen_width,
            screen_height=task_agent_config.screen_height,
            headless=task_agent_config.headless,
            result_dir=str(result_dir),
            checkpoint_eval_mode="off",
            checkpoint_steps="",
            trace_guest=False,
            save_model_eval_raw_info=False,
        )
        scores: list[float] = []
        with _v2_runtime_env(instance, task_agent_config):
            env = DesktopEnv(
                provider_name="volcengine",
                region=os.getenv("VOLCENGINE_REGION"),
                path_to_vm=instance.instance_id,
                action_space=task_agent_config.action_space,
                screen_size=(task_agent_config.screen_width, task_agent_config.screen_height),
                headless=task_agent_config.headless,
                os_type=instance.os_type,
                require_a11y_tree=task_agent_config.observation_type
                in {"a11y_tree", "screenshot_a11y_tree", "som"},
                enable_proxy=bool(getattr(example, "proxy", False)),
                client_password=task_agent_config.client_password or "osworld-public-evaluation",
                instance_type=task.metadata.get("instance_type") or None,
                volume_size=_optional_int(task.metadata.get("volume_size")),
                force_disable_vnc=bool(task.metadata.get("disable_vnc", False)),
                force_disable_recording=bool(task.metadata.get("disable_recording", False)),
            )
            lib_run_single.run_single_example(
                agent,
                env,
                example,
                task_agent_config.max_steps,
                str(getattr(example, "instruction", "")),
                args,
                str(result_dir),
                scores,
            )
        result = TaskResult(
            task_id=task.task_id,
            domain=task.domain,
            example_id=task.example_id,
            score=scores[-1] if scores else _read_score(result_dir),
            result_dir=str(result_dir),
        )
    except Exception as exc:
        _write_error(result_dir, exc)
        result = TaskResult(
            task_id=task.task_id,
            domain=task.domain,
            example_id=task.example_id,
            score=0.0,
            result_dir=str(result_dir),
            error=_error_message(exc),
            error_category=_error_category(exc),
        )
    finally:
        if env is not None:
            with contextlib.suppress(Exception):
                env.close()
        shutil.rmtree(cache_root, ignore_errors=True)
    result_queue.put(result.__dict__)


def _clear_conflicting_modules() -> None:
    for name in list(sys.modules):
        if name == "desktop_env" or name.startswith("desktop_env.") or name == "mm_agents" or name.startswith("mm_agents."):
            sys.modules.pop(name, None)


def _load_agent(agent_config: AgentConfig) -> Any:
    if not agent_config.agent_factory:
        raise ValueError("OSWorld V2 runs require a run-pinned --agent/agent_factory")
    module_name, function_name = agent_config.agent_factory.split(":", 1)
    factory = getattr(import_module(module_name), function_name)
    return factory(agent_config)


def _result_dir(task: TaskSpec, config: EvalConfig, agent: AgentConfig) -> Path:
    return (
        Path(config.result_dir)
        / config.run_id
        / "osworld-v2"
        / agent.action_space
        / agent.observation_type
        / agent.name
        / _safe_path_component(task.task_id)
        / f"attempt-{int(task.metadata.get('attempt', 1))}"
    )


@contextlib.contextmanager
def _v2_runtime_env(instance: InstanceRecord, agent: AgentConfig):
    updates = {
        "VOLCENGINE_INSTANCE_PRIVATE_IPS": json.dumps({instance.instance_id: instance.private_ip}),
        "VOLCENGINE_INSTANCE_ID": instance.instance_id,
        "VOLCENGINE_INSTANCE_PRIVATE_IP": instance.private_ip,
        "VOLCENGINE_IMAGE_ID": str(instance.metadata.get("image_id") or "arena-managed"),
        "VOLCENGINE_DEFAULT_PASSWORD": agent.client_password or "osworld-public-evaluation",
        "VOLCENGINE_TERMINATE_ON_CLOSE": "false",
    }
    previous = {key: os.environ.get(key) for key in updates}
    os.environ.update(updates)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _agent_config_for_instance(agent: AgentConfig, instance: InstanceRecord, task: TaskSpec) -> AgentConfig:
    if agent.platform:
        return agent
    platform = "windows" if "win" in (instance.os_type or "").lower() else "ubuntu"
    return replace(agent, platform=platform)


def _optional_int(value: Any) -> int | None:
    try:
        return int(value) if value not in {None, ""} else None
    except (TypeError, ValueError):
        return None


def _read_score(result_dir: Path) -> float:
    try:
        return float((result_dir / "result.txt").read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return 0.0


def _error_message(exc: Exception) -> str:
    frames = traceback.extract_tb(exc.__traceback__)
    if not frames:
        return f"{type(exc).__name__}: {exc}"
    frame = frames[-1]
    return f"{type(exc).__name__}: {exc} at {frame.filename}:{frame.lineno} in {frame.name}"


def _error_category(exc: Exception) -> str | None:
    current: BaseException | None = exc
    while current is not None:
        category = getattr(current, "error_category", None)
        if category:
            return str(category)
        current = current.__cause__ or current.__context__
    return None


def _write_error(result_dir: Path, exc: Exception) -> None:
    (result_dir / "runner_error.txt").write_text(
        "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)), encoding="utf-8"
    )


def _safe_path_component(value: str) -> str:
    return value.replace("/", "__").replace(":", "_")
