"""Run an EngiWorld GUI/CLI task with a local QCOW2 environment."""

from __future__ import annotations

import argparse
import contextlib
from dataclasses import asdict, replace
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import sys
import uuid

from engiworld.agents.profiles import get_agent_profile
from engiworld.active_time import ActiveTaskDeadline, ActiveTimeBudgetExceeded, budget_outcome
from engiworld.prepare_tasks import TASK_ROOT, asset_entries, asset_path, canonical_task, verify_asset
from engiworld.scheduler.runner import (
    _agent_config_for_instance, _agent_config_for_task, ensure_engine_importable,
    load_task_config, run_single_task,
)
from engiworld.scheduler.schemas import EvalConfig, InstanceRecord
from engiworld.scheduler.task_loader import load_tasks

RUNTIME_ROOT = Path(__file__).resolve().parents[2]


LocalTaskTimeout = ActiveTimeBudgetExceeded  # Compatibility for existing callers.


@contextlib.contextmanager
def task_deadline(seconds: float):
    with ActiveTaskDeadline(seconds).running() as budget:
        yield budget


def preflight(root: Path, task_id: str):
    task_id = canonical_task(root, task_id)
    tasks = [task for task in load_tasks(root, path_prefixes=[task_id + "/"])
             if task.task_id == task_id]
    if len(tasks) != 1:
        raise ValueError(f"Unknown task directory ID: {task_id}")
    task = tasks[0]
    example = load_task_config(EvalConfig(run_id="check", task_root=str(root)), task)
    missing = []
    for item in [*example.get("config", []), *example.get("evaluator", {}).get("postconfig", [])]:
        if item.get("type") == "upload_file":
            for resource in item.get("parameters", {}).get("files", []):
                if not Path(resource["local_path"]).is_file():
                    missing.append(resource["local_path"])
    _, entries = asset_entries(root, task_id)
    missing.extend(entry["path"] for entry in entries
                   if not verify_asset(asset_path(root, entry["path"]), entry))
    if missing:
        raise ValueError(f"Missing or modified task resources: {sorted(set(missing))}. "
                         f"Run python -m engiworld.prepare_tasks --task {task_id}")
    return task


def smoke_test(task, instance, config, agent_config, image: str, output: Path):
    ensure_engine_importable(Path(config.engine_path))
    from desktop_env.desktop_env import DesktopEnv
    env = DesktopEnv(
        provider_name="docker", path_to_vm=image, os_type=instance.os_type,
        action_space=agent_config.action_space, require_a11y_tree=False,
        screen_size=(agent_config.screen_width, agent_config.screen_height), headless=True,
        client_password=agent_config.client_password or "", cache_dir=str(output / "cache"),
    )
    try:
        observation = env.reset(task_config=load_task_config(config, task))
        screenshot = observation.get("screenshot")
        if not screenshot:
            raise RuntimeError("Environment reset returned no screenshot")
        (output / "smoke.png").write_bytes(screenshot)
    finally:
        env.close()
    return {"task_id": task.task_id, "status": "environment_ready", "screenshot": str(output / "smoke.png")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True, help="Exact task directory ID")
    parser.add_argument("--task-root", type=Path, default=TASK_ROOT)
    parser.add_argument("--image", type=Path, help="Decompressed QCOW2 disk for the task's snapshot")
    parser.add_argument("--model", help="OpenAI-compatible API model name (or ARENA_MODEL_NAME)")
    parser.add_argument("--result-dir", type=Path, default=Path("results"))
    parser.add_argument("--task-timeout", type=float, default=18000,
                        help="Active task seconds, excluding registered framework pauses (default: 18000)")
    parser.add_argument("--client-password", default=os.getenv("ENGIWORLD_CLIENT_PASSWORD", os.getenv("OSWORLD_CLIENT_PASSWORD", "")))
    parser.add_argument("--record-video", action="store_true")
    parser.add_argument("--check", action="store_true", help="Validate task resources without starting a VM/API")
    parser.add_argument("--smoke-test", action="store_true", help="Start/reset the VM and save a screenshot without a model")
    args = parser.parse_args(argv)
    if args.task_timeout <= 0:
        parser.error("--task-timeout must be positive")
    try:
        task = preflight(args.task_root.resolve(), args.task)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    profile = get_agent_profile("openai-compatible")
    instance = InstanceRecord("local-docker", "", os_type=task.metadata["os_type"])
    agent_config = _agent_config_for_task(_agent_config_for_instance(
        replace(profile.agent_config, client_password=args.client_password, record_video=args.record_video),
        instance, task), task)
    if args.check:
        print(json.dumps({"task": task.task_id, "snapshot": task.metadata["snapshot"],
                          "mode": agent_config.eval_mode, "max_steps": agent_config.max_steps,
                          "task_timeout": args.task_timeout, "resources": "ok"}, indent=2))
        return 0
    if sys.platform != "linux":
        parser.error("Local QCOW2 evaluation requires a Linux host with Docker")
    if args.image is None or not args.image.is_file() or args.image.suffix != ".qcow2":
        parser.error("--image must point to an existing, decompressed .qcow2 disk")
    model = args.model or os.getenv("ARENA_MODEL_NAME")
    if not args.smoke_test and (not model or not os.getenv("OPENAI_API_KEY")):
        parser.error("Set --model (or ARENA_MODEL_NAME) and OPENAI_API_KEY")
    if model:
        os.environ["ARENA_MODEL_NAME"] = model
    # Apply common request defaults without overriding explicit local settings.
    for key, value in profile.env.items():
        if "HOTSWAP" not in key and "RUNTIME_CONFIG" not in key:
            os.environ.setdefault(key, value)
    os.environ["ARENA_OPENAI_COMPAT_HOTSWAP_ENABLED"] = "false"
    for option, default in {"RAM_SIZE": "16G", "CPU_CORES": "4", "DISK_SIZE": "200G"}.items():
        os.environ.setdefault("ENGIWORLD_DOCKER_" + option, os.getenv("OSWORLD_DOCKER_" + option, default))
    config = EvalConfig(
        run_id=datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8],
        task_root=str(args.task_root.resolve()), engine_path=str(RUNTIME_ROOT / "engine"),
        result_dir=str(args.result_dir.resolve()), s3_upload=False, keep_local_results=True,
    )
    output = Path(config.result_dir) / config.run_id
    output.mkdir(parents=True)
    logging.basicConfig(level=logging.INFO)
    budget = None
    try:
        with task_deadline(args.task_timeout) as budget:
            if args.smoke_test:
                summary = smoke_test(task, instance, config, agent_config, str(args.image.resolve()), output)
            else:
                result = run_single_task(task, instance, config, agent_config,
                                         provider_name="docker", path_to_vm=str(args.image.resolve()))
                summary = asdict(result)
    except LocalTaskTimeout as exc:
        if args.smoke_test:
            summary = {"task_id": task.task_id, "score": None, "error": str(exc),
                       "error_category": "environment_timeout"}
        else:
            summary = {"task_id": task.task_id, "status": "completed", **budget_outcome(),
                       "error": None, "error_category": None, "result_dir": str(output)}
    except Exception as exc:
        summary = {"task_id": task.task_id, "score": None, "error": str(exc),
                   "error_category": "environment_error"}
    if budget is not None:
        summary.update(budget.metrics())
    summary["active_time_limit_seconds"] = args.task_timeout
    if summary.get("scoring_basis") == "active_time_budget":
        (output / "result.txt").write_text("0.0", encoding="utf-8")
        (output / "evaluation.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Saved: {output / 'summary.json'}")
    return int(bool(summary.get("error")))


if __name__ == "__main__":
    raise SystemExit(main())
