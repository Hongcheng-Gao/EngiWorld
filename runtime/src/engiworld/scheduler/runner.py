"""EngiWorld GUI/CLI task execution and engineering-artifact evaluation."""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import sys
import traceback
from dataclasses import replace
from importlib import import_module
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

from engiworld.scheduler.schemas import AgentConfig, EvalConfig, InstanceRecord, TaskResult, TaskSpec
from engiworld.scheduler.task_loader import infer_engiworld_eval_mode
from engiworld.scheduler.model_action_outcome import ALT_F4_CATEGORY, ModelActionAudit
from engiworld.task_names import canonical_prefix, task_kind as canonical_task_kind

AgentFactory = Callable[[AgentConfig], Any]


def resolve_engine_path(configured_path: str | None = None) -> Path:
    """Find the packaged EngiWorld engine, accepting the old environment alias."""
    raw_path = os.getenv("ENGIWORLD_ENGINE_PATH") or os.getenv("OSWORLD_PATH") or configured_path
    if not raw_path or raw_path.replace("\\", "/") in {"engine", "third_party/OSWorld"}:
        source_engine = Path(__file__).resolve().parents[3] / "engine"
        return source_engine if source_engine.is_dir() else Path("engine").resolve()
    return Path(raw_path).expanduser().resolve()


def ensure_engine_importable(engine_path: Path) -> None:
    if not engine_path.exists():
        raise FileNotFoundError(
            f"EngiWorld engine not found at {engine_path}. "
            "Set ENGIWORLD_ENGINE_PATH or restore the runtime/engine directory."
        )
    path_str = str(engine_path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def load_task_config(eval_config: EvalConfig, task: TaskSpec) -> dict[str, Any]:
    if "task_json" in task.metadata:
        example = deepcopy(task.metadata["task_json"])
        _absolutize_task_local_paths(eval_config, task, example)
        _annotate_engiworld_task(eval_config, task, example)
        return example

    engine_path = resolve_engine_path(eval_config.osworld_path or eval_config.engine_path)
    task_file = (
        engine_path
        / eval_config.test_config_base_dir
        / "examples"
        / task.domain
        / f"{task.example_id}.json"
    )
    with task_file.open("r", encoding="utf-8") as file:
        return json.load(file)


def _absolutize_task_local_paths(
    eval_config: EvalConfig,
    task: TaskSpec,
    example: dict[str, Any],
) -> None:
    task_root = Path(eval_config.task_root).expanduser().resolve()
    domain_root = task_root / task.domain

    def rewrite_setup_items(items: list[dict[str, Any]]) -> None:
        for item in items:
            if item.get("type") != "upload_file":
                continue
            files = item.get("parameters", {}).get("files", [])
            for file_item in files:
                local_path = file_item.get("local_path")
                if not local_path:
                    continue
                local = Path(str(local_path)).expanduser()
                if not local.is_absolute():
                    file_item["local_path"] = str((domain_root / local).resolve())

    rewrite_setup_items(example.get("config", []))
    evaluator = example.get("evaluator", {})
    rewrite_setup_items(evaluator.get("postconfig", []))


def _annotate_engiworld_task(
    eval_config: EvalConfig,
    task: TaskSpec,
    example: dict[str, Any],
) -> None:
    """Attach runtime-only context used by EngiWorld integrity policies."""
    task_root = Path(eval_config.task_root).expanduser().resolve()
    task_dir = task_root / str(task.metadata.get("task_dir") or task.task_id.split("@", 1)[0])
    task_path = task_root / str(task.metadata.get("task_path") or "")
    task_kind = canonical_task_kind(str(task.metadata.get("task_kind") or "").lower())

    if task_kind:
        example["_engiworld_task_family"] = task_kind
    profile = example.get("_engiworld_experiment_profile") or example.get("experiment_profile")
    if profile:
        example["_engiworld_experiment_profile"] = profile
    policy_domain = str(task.metadata.get("app") or "").strip()
    if not policy_domain or policy_domain == "unknown":
        policy_domain = task.domain.rsplit("/", 1)[-1]
    example["_engiworld_domain"] = policy_domain
    if task_path.is_file():
        example["_engiworld_config_path"] = str(task_path)

    ground_truth_dir = task_dir / "ground_truth"
    if ground_truth_dir.is_dir():
        example["_engiworld_expected_outputs"] = sorted(
            path.relative_to(ground_truth_dir).as_posix()
            for path in ground_truth_dir.rglob("*")
            if path.is_file()
        )


def default_agent_factory(agent_config: AgentConfig) -> Any:
    if agent_config.agent_factory:
        return _load_agent_factory(agent_config.agent_factory)(agent_config)

    from mm_agents.example_rl_agent import ExampleRLAgent

    return ExampleRLAgent(
        action_space=agent_config.action_space,
        observation_type=agent_config.observation_type,
        checkpoint_path=agent_config.checkpoint_path,
        max_steps=agent_config.max_steps,
    )


def _load_agent_factory(factory_path: str) -> AgentFactory:
    if ":" not in factory_path:
        raise ValueError(
            "agent_factory must be formatted as package.module:function, "
            f"got {factory_path!r}"
        )
    module_name, function_name = factory_path.split(":", 1)
    factory = getattr(import_module(module_name), function_name)
    if not callable(factory):
        raise TypeError(f"Agent factory is not callable: {factory_path}")
    return factory


def build_run_args(eval_config: EvalConfig, agent_config: AgentConfig) -> SimpleNamespace:
    return SimpleNamespace(
        action_space=agent_config.action_space,
        observation_type=agent_config.observation_type,
        eval_mode=agent_config.eval_mode,
        experiment_profile=agent_config.experiment_profile,
        model=agent_config.name,
        platform=agent_config.platform,
        max_steps=agent_config.max_steps,
        bash_timeout=agent_config.bash_timeout,
        record_video=agent_config.record_video,
        resume=agent_config.resume,
        sleep_after_execution=agent_config.sleep_after_execution,
        screen_width=agent_config.screen_width,
        screen_height=agent_config.screen_height,
        headless=agent_config.headless,
        result_dir=str(Path(eval_config.result_dir) / eval_config.run_id),
        vm_secret_mount=agent_config.vm_secret_mounts,
    )


def run_single_task(
    task: TaskSpec,
    instance: InstanceRecord,
    eval_config: EvalConfig,
    agent_config: AgentConfig,
    agent_factory: AgentFactory | None = None,
    *,
    provider_name: str = "volcengine",
    path_to_vm: str | None = None,
) -> TaskResult:
    """Run one task on a leased ECS instance or an explicit local VM image."""

    if task.metadata.get("benchmark") == "osworld-v2" or eval_config.benchmark == "osworld-v2":
        from engiworld.scheduler.osworld_v2_runner import run_single_task_v2

        return run_single_task_v2(task, instance, eval_config, agent_config)

    engine_path = resolve_engine_path(eval_config.osworld_path or eval_config.engine_path)
    ensure_engine_importable(engine_path)

    import lib_run_single
    from desktop_env.desktop_env import DesktopEnv

    task_agent_config = _agent_config_for_task(
        _agent_config_for_instance(agent_config, instance, task),
        task,
    )
    result_dir = (
        Path(eval_config.result_dir)
        / eval_config.run_id
        / task_agent_config.action_space
        / task_agent_config.observation_type
        / task_agent_config.name
        / _safe_path_component(task.task_id)
        / f"attempt-{int(task.metadata.get('attempt', 1))}"
    )
    result_dir.mkdir(parents=True, exist_ok=True)
    cache_root = result_dir / ".engiworld-cache"

    scores: list[float] = []
    env = None
    action_audit = ModelActionAudit(task, instance, eval_config.run_id, result_dir)
    try:
        example = load_task_config(eval_config, task)
        args = build_run_args(eval_config, task_agent_config)
        agent = (agent_factory or default_agent_factory)(task_agent_config)
        provider_context = (
            _volcengine_private_ip_env(instance)
            if provider_name == "volcengine" else contextlib.nullcontext()
        )
        with provider_context:
            env = DesktopEnv(
                provider_name=provider_name,
                path_to_vm=path_to_vm or instance.instance_id,
                action_space=task_agent_config.action_space,
                screen_size=(task_agent_config.screen_width, task_agent_config.screen_height),
                headless=task_agent_config.headless,
                os_type=instance.os_type,
                require_a11y_tree=task_agent_config.observation_type
                in {"a11y_tree", "screenshot_a11y_tree", "som"},
                client_password=task_agent_config.client_password or "",
                vm_secret_mounts=task_agent_config.vm_secret_mounts,
                cache_dir=str(cache_root),
            )
            if provider_name == "volcengine":
                action_audit.attach(env)
            run_example = (
                lib_run_single.run_single_example_terminal
                if task_agent_config.eval_mode in {"cli", "cli-text", "extreme"}
                else lib_run_single.run_single_example
            )
            run_example(
                agent,
                env,
                example,
                task_agent_config.max_steps,
                example["instruction"],
                args,
                str(result_dir),
                scores,
            )
        return TaskResult(
            task_id=task.task_id,
            domain=task.domain,
            example_id=task.example_id,
            score=scores[-1] if scores else 0.0,
            result_dir=str(result_dir),
        )
    except Exception as exc:
        _write_task_error(result_dir, exc)
        error = _task_error_message(exc)
        category = _error_category(exc)
        decision = action_audit.resolve(error, category) if provider_name == "volcengine" else None
        return TaskResult(
            task_id=task.task_id,
            domain=task.domain,
            example_id=task.example_id,
            score=None if category == "infra" and not decision else 0.0,
            result_dir=str(result_dir),
            error=error,
            error_category=ALT_F4_CATEGORY if decision else category,
        )
    finally:
        # The cloud scheduler owns ECS lifecycle; local invocations own their container.
        if env is not None and provider_name != "volcengine":
            with contextlib.suppress(Exception):
                env.close()
        shutil.rmtree(cache_root, ignore_errors=True)


def _task_error_message(exc: Exception) -> str:
    frames = traceback.extract_tb(exc.__traceback__)
    if not frames:
        return f"{type(exc).__name__}: {exc}"
    frame = frames[-1]
    return (
        f"{type(exc).__name__}: {exc} "
        f"at {frame.filename}:{frame.lineno} in {frame.name}"
    )


def _error_category(exc: Exception) -> str | None:
    current: BaseException | None = exc
    while current is not None:
        category = getattr(current, "error_category", None)
        if category:
            return str(category)
        current = current.__cause__ or current.__context__
    return None


def _write_task_error(result_dir: Path, exc: Exception) -> None:
    try:
        result_dir.mkdir(parents=True, exist_ok=True)
        (result_dir / "runner_error.txt").write_text(
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            encoding="utf-8",
        )
    except Exception:
        pass


def _safe_path_component(value: str) -> str:
    return value.replace("/", "__").replace(":", "_")


@contextlib.contextmanager
def _volcengine_private_ip_env(instance: InstanceRecord):
    if not instance.private_ip:
        yield
        return

    previous_mapping = os.environ.get("VOLCENGINE_INSTANCE_PRIVATE_IPS")
    previous_instance_id = os.environ.get("VOLCENGINE_INSTANCE_ID")
    previous_private_ip = os.environ.get("VOLCENGINE_INSTANCE_PRIVATE_IP")
    mapping: dict[str, str] = {}
    if previous_mapping:
        try:
            loaded = json.loads(previous_mapping)
        except json.JSONDecodeError:
            loaded = {}
        if isinstance(loaded, dict):
            mapping = {str(key): str(value) for key, value in loaded.items() if value}
    mapping[instance.instance_id] = instance.private_ip
    os.environ["VOLCENGINE_INSTANCE_PRIVATE_IPS"] = json.dumps(mapping, ensure_ascii=False)
    os.environ["VOLCENGINE_INSTANCE_ID"] = instance.instance_id
    os.environ["VOLCENGINE_INSTANCE_PRIVATE_IP"] = instance.private_ip
    try:
        yield
    finally:
        _restore_env_value("VOLCENGINE_INSTANCE_PRIVATE_IPS", previous_mapping)
        _restore_env_value("VOLCENGINE_INSTANCE_ID", previous_instance_id)
        _restore_env_value("VOLCENGINE_INSTANCE_PRIVATE_IP", previous_private_ip)


def _restore_env_value(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


def _agent_config_for_instance(
    agent_config: AgentConfig,
    instance: InstanceRecord,
    task: TaskSpec,
) -> AgentConfig:
    if agent_config.platform:
        return agent_config
    return replace(
        agent_config,
        platform=_platform_from_os_type(instance.os_type or task.metadata.get("os_type")),
    )


def _agent_config_for_task(agent_config: AgentConfig, task: TaskSpec) -> AgentConfig:
    base_task_id = str(
        task.metadata.get("base_task_id") or task.task_id.split("@", 1)[0]
    )
    task_kind = str(task.metadata.get("task_kind") or "").strip().lower()
    if not task_kind:
        task_kind = base_task_id.split("/", 1)[0].lower()
    task_kind = canonical_task_kind(task_kind)

    experiment_profile = (
        task.metadata.get("experiment_profile")
        or agent_config.experiment_profile
        or os.getenv("ARENA_EXPERIMENT_PROFILE")
    )
    eval_mode = agent_config.eval_mode
    if str(experiment_profile or "").strip().lower() in {
        "open_engineering",
        "open-engineering",
        "extreme",
    }:
        eval_mode = "extreme"
    if eval_mode == "auto":
        eval_mode = str(task.metadata.get("eval_mode") or "").strip().lower()
        if not eval_mode:
            eval_mode = infer_engiworld_eval_mode(base_task_id)

    # Open-ended tasks start without engineering applications. Their terminal
    # interface must allow installing tools and choosing an unrestricted workflow.
    if task_kind == "open-ended" and eval_mode in {"cli", "cli-text", "extreme"}:
        eval_mode = "extreme"
        experiment_profile = "open_engineering"

    if not experiment_profile and canonical_prefix(base_task_id).startswith("image-based-modeling/"):
        experiment_profile = (
            "cli_message_no_readimg" if eval_mode == "cli-text"
            else "cli_message_initial" if eval_mode in {"cli", "extreme"}
            else "gui_message_initial"
        )

    if eval_mode not in {
        "gui",
        "computer13",
        "gui-a11y",
        "gui-screenshot-a11y",
        "cli",
        "cli-text",
        "extreme",
    }:
        raise ValueError(f"Unsupported EngiWorld eval mode: {eval_mode!r}")

    observation_type = agent_config.observation_type
    action_space = agent_config.action_space
    if eval_mode in {"cli", "cli-text", "extreme"}:
        observation_type = "terminal"
        action_space = "pyautogui"
    elif eval_mode == "computer13":
        action_space = "computer_13"
    elif eval_mode == "gui-a11y":
        observation_type = "a11y_tree"
        action_space = "pyautogui"
    elif eval_mode == "gui-screenshot-a11y":
        observation_type = "screenshot_a11y_tree"
        action_space = "pyautogui"

    terminal_mode = eval_mode in {"cli", "cli-text", "extreme"}
    open_ended_limit = (agent_config.top10_max_steps if agent_config.top10_max_steps is not None
                        else agent_config.open_ended_max_steps)
    if task_kind == "open-ended" and open_ended_limit is not None:
        max_steps = open_ended_limit
    elif (
        task_kind == "multi-software"
        and terminal_mode
        and agent_config.cli_multi_max_steps is not None
    ):
        max_steps = agent_config.cli_multi_max_steps
    elif (
        task_kind == "multi-software"
        and not terminal_mode
        and agent_config.gui_multi_max_steps is not None
    ):
        max_steps = agent_config.gui_multi_max_steps
    elif task_kind == "multi-software" and agent_config.multi_max_steps is not None:
        max_steps = agent_config.multi_max_steps
    elif task_kind == "software-selection" and agent_config.open_max_steps is not None:
        max_steps = agent_config.open_max_steps
    elif terminal_mode and agent_config.cli_max_steps is not None:
        max_steps = agent_config.cli_max_steps
    elif not terminal_mode and agent_config.gui_max_steps is not None:
        max_steps = agent_config.gui_max_steps
    else:
        max_steps = agent_config.max_steps

    return replace(
        agent_config,
        eval_mode=eval_mode,
        experiment_profile=experiment_profile,
        action_space=action_space,
        observation_type=observation_type,
        max_steps=max_steps,
    )


def _platform_from_os_type(os_type: Any) -> str:
    value = str(os_type or "").strip().lower()
    if "win" in value:
        return "windows"
    if "ubuntu" in value or "linux" in value:
        return "ubuntu"
    return value or "ubuntu"
