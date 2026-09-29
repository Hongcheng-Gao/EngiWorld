"""Worker process entry point for distributed EngiWorld evaluation."""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import sys
import threading
import time
from dataclasses import fields, replace
from multiprocessing import Process

from engiworld.scheduler.error_policy import classify_task_error
from engiworld.scheduler.runner import run_single_task
from engiworld.scheduler.redis_store import RedisStore
from engiworld.scheduler.schemas import AgentConfig, EvalConfig, InstanceRecord, TaskResult, TaskSpec
from engiworld.scheduler.storage import upload_task_artifacts
from engiworld.scheduler.task_bundle import DEFAULT_TASK_BUCKET, ensure_task_bundle

_AGENT_CONFIG_FIELD_NAMES = {field.name for field in fields(AgentConfig)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="EngiWorld GUI/CLI evaluation worker")
    parser.add_argument(
        "--run-id",
        default=os.getenv("RUN_ID"),
        help=(
            "Optional run-scoped worker mode. Leave unset for the normal cluster mode, "
            "where the worker consumes the global Redis task queue and reads run_id "
            "from each claimed task."
        ),
    )
    parser.add_argument("--worker-id", default=None)
    parser.add_argument(
        "--redis-url",
        default=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
    )
    parser.add_argument("--engine-path", default=os.getenv("ENGIWORLD_ENGINE_PATH", os.getenv("OSWORLD_PATH", "engine")))
    parser.add_argument("--osworld-path", dest="engine_path", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    parser.add_argument(
        "--osworld-v2-path",
        default=os.getenv("OSWORLD_V2_PATH", "third_party/OSWorld-V2"),
    )
    parser.add_argument("--task-root", default="task")
    parser.add_argument(
        "--task-file-path",
        default=os.getenv("TASK_FILE_PATH"),
        help=(
            f"Optional fallback task bundle object key in {DEFAULT_TASK_BUCKET} "
            "for run-scoped workers."
        ),
    )
    parser.add_argument(
        "--task-download-wait-timeout-seconds",
        type=int,
        default=int(os.getenv("TASK_DOWNLOAD_WAIT_TIMEOUT_SECONDS", "3600")),
    )
    parser.add_argument(
        "--task-download-lock-stale-seconds",
        type=int,
        default=int(os.getenv("TASK_DOWNLOAD_LOCK_STALE_SECONDS", "3600")),
    )
    parser.add_argument("--local-concurrency", type=int, default=1)
    parser.add_argument("--model", default="example-rl-agent")
    parser.add_argument(
        "--agent-factory",
        default=os.getenv("ZMOS_AGENT_FACTORY"),
        help="Optional Python factory path, formatted as package.module:function.",
    )
    parser.add_argument("--checkpoint-path", default=None)
    parser.add_argument(
        "--platform",
        default=os.getenv("ARENA_AGENT_PLATFORM"),
        help=(
            "Optional agent platform override. Leave unset to infer it per task "
            "from the claimed instance os_type."
        ),
    )
    parser.add_argument("--action-space", default="computer_13")
    parser.add_argument(
        "--observation-type",
        default="screenshot",
        choices=["screenshot", "a11y_tree", "screenshot_a11y_tree", "som", "terminal"],
    )
    parser.add_argument(
        "--eval-mode",
        default="gui",
        choices=[
            "auto",
            "gui",
            "computer13",
            "gui-a11y",
            "gui-screenshot-a11y",
            "cli",
            "cli-text",
            "extreme",
        ],
    )
    parser.add_argument("--max-steps", type=int, default=15)
    parser.add_argument("--gui-max-steps", type=int, default=None)
    parser.add_argument("--cli-max-steps", type=int, default=None)
    parser.add_argument("--gui-multi-max-steps", type=int, default=None)
    parser.add_argument("--cli-multi-max-steps", type=int, default=None)
    parser.add_argument("--open-ended-max-steps", type=int, default=None)
    parser.add_argument("--top10-max-steps", dest="open_ended_max_steps", type=int, default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    parser.add_argument(
        "--gui-top10-max-steps",
        dest="legacy_gui_top10_max_steps",
        type=int,
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--cli-top10-max-steps",
        dest="legacy_cli_top10_max_steps",
        type=int,
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--history-turns", type=int, default=None)
    parser.add_argument("--bash-timeout", type=int, default=120)
    parser.add_argument(
        "--record-video",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    parser.add_argument("--sleep-after-execution", type=float, default=2.0)
    parser.add_argument("--screen-width", type=int, default=1920)
    parser.add_argument("--screen-height", type=int, default=1080)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument(
        "--client-password",
        default=os.getenv("VOLCENGINE_DEFAULT_PASSWORD"),
        help=(
            "Optional password passed to OSWorld setup steps that use {CLIENT_PASSWORD}; "
            "not required when the image auto-login/server setup does not need sudo."
        ),
    )
    parser.add_argument("--result-dir", default="results")
    parser.add_argument(
        "--s3-bucket",
        dest="s3_bucket",
        default=os.getenv("VOLCENGINE_S3_BUCKET", "agent-eval-results"),
    )
    parser.add_argument(
        "--s3-upload",
        dest="s3_upload",
        action="store_true",
        default=True,
    )
    parser.add_argument(
        "--no-s3-upload",
        dest="s3_upload",
        action="store_false",
    )
    parser.add_argument("--keep-local-results", action="store_true")
    parser.add_argument("--task-lease-ttl-seconds", type=int, default=1800)
    parser.add_argument("--instance-lease-ttl-seconds", type=int, default=2100)
    parser.add_argument("--poll-interval-seconds", type=float, default=5.0)
    parser.add_argument(
        "--reuse-instances",
        action="store_true",
        default=_bool_env("WORKER_REUSE_INSTANCES", False),
        help=(
            "Reuse an ECS VM after a task attempt. Default false recycles the VM "
            "after every task attempt and lets master launch a replacement."
        ),
    )
    parser.add_argument(
        "--idle-exit-rounds",
        type=int,
        default=int(os.getenv("WORKER_IDLE_EXIT_ROUNDS", "0")),
        help=(
            "Exit after this many consecutive empty claim attempts. "
            "Default 0 keeps polling forever in global queue mode."
        ),
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    base_worker_id = args.worker_id or socket.gethostname()
    eval_config = EvalConfig(
        run_id=args.run_id or "",
        redis_url=args.redis_url,
        engine_path=args.engine_path,
        osworld_v2_path=args.osworld_v2_path,
        task_root=args.task_root,
        result_dir=args.result_dir,
        s3_bucket=args.s3_bucket,
        s3_upload=args.s3_upload,
        keep_local_results=args.keep_local_results,
    )
    agent_config = AgentConfig(
        name=args.model,
        agent_factory=args.agent_factory,
        checkpoint_path=args.checkpoint_path,
        platform=args.platform,
        action_space=args.action_space,
        observation_type=args.observation_type,
        eval_mode=args.eval_mode,
        max_steps=args.max_steps,
        gui_max_steps=args.gui_max_steps,
        cli_max_steps=args.cli_max_steps,
        gui_multi_max_steps=args.gui_multi_max_steps,
        cli_multi_max_steps=args.cli_multi_max_steps,
        open_ended_max_steps=(
            args.open_ended_max_steps
            if args.open_ended_max_steps is not None
            else args.legacy_cli_top10_max_steps
        ),
        history_turns=args.history_turns,
        bash_timeout=args.bash_timeout,
        record_video=args.record_video,
        resume=args.resume,
        sleep_after_execution=args.sleep_after_execution,
        screen_width=args.screen_width,
        screen_height=args.screen_height,
        headless=args.headless,
        client_password=args.client_password,
    )

    if args.local_concurrency <= 1:
        _run_worker_loop(base_worker_id, eval_config, agent_config, args)
        return

    processes: list[Process] = []
    for idx in range(args.local_concurrency):
        worker_id = f"{base_worker_id}-{idx}"
        proc = Process(
            target=_run_worker_loop,
            args=(worker_id, eval_config, agent_config, args),
            name=f"arena-worker-{idx}",
        )
        proc.start()
        processes.append(proc)

    try:
        for proc in processes:
            proc.join()
    except KeyboardInterrupt:
        for proc in processes:
            if proc.is_alive():
                proc.terminate()
        for proc in processes:
            proc.join(timeout=5)
        raise


def _run_worker_loop(
    worker_id: str,
    eval_config: EvalConfig,
    agent_config: AgentConfig,
    args: argparse.Namespace,
) -> None:
    control_store = RedisStore(eval_config.redis_url, eval_config.run_id or "_global")
    _install_signal_handlers(worker_id, control_store)

    idle_rounds = 0
    prepared_eval_configs: dict[str, EvalConfig] = {}
    _emit(
        "worker_started",
        worker_id=worker_id,
        run_id=eval_config.run_id or None,
        queue_mode="run_scoped" if eval_config.run_id else "global",
    )
    while True:
        control_store.record_worker_heartbeat(worker_id, status="alive")
        store = control_store
        task_eval_config = eval_config
        next_ref = control_store.peek_ready_task_ref(
            run_id_filter=eval_config.run_id or None
        )
        if next_ref is not None and next_ref[0] not in prepared_eval_configs:
            next_run_id, _ = next_ref
            next_store = (
                control_store
                if eval_config.run_id
                else RedisStore(eval_config.redis_url, next_run_id, client=control_store.client)
            )
            try:
                prepared_eval_configs[next_run_id] = _ensure_task_data_for_run(
                    next_store,
                    worker_id,
                    replace(eval_config, run_id=next_run_id),
                    args,
                )
            except Exception as exc:
                _emit(
                    "task_bundle_download_failed",
                    worker_id=worker_id,
                    run_id=next_run_id,
                    error=str(exc),
                )
                time.sleep(args.poll_interval_seconds)
                continue

        if eval_config.run_id:
            task = store.claim_task(worker_id, lease_ttl_seconds=args.task_lease_ttl_seconds)
            task_eval_config = prepared_eval_configs.get(eval_config.run_id, eval_config)
        else:
            claimed = store.claim_any_task(
                worker_id,
                lease_ttl_seconds=args.task_lease_ttl_seconds,
            )
            if claimed is None:
                task = None
            else:
                run_id, task = claimed
                store = RedisStore(eval_config.redis_url, run_id, client=control_store.client)
                task_eval_config = prepared_eval_configs.get(
                    run_id,
                    replace(eval_config, run_id=run_id),
                )

        if task is None:
            completion_signal = (
                store.run_completion_signal() if eval_config.run_id else {}
            )
            if eval_config.run_id and completion_signal.get("status") == "completed":
                _emit(
                    "worker_run_completed_exit",
                    worker_id=worker_id,
                    run_id=eval_config.run_id,
                    completion_signal=completion_signal,
                )
                break
            idle_rounds += 1
            if args.idle_exit_rounds and idle_rounds >= args.idle_exit_rounds:
                _emit("worker_idle_exit", worker_id=worker_id, idle_rounds=idle_rounds)
                break
            time.sleep(args.poll_interval_seconds)
            continue
        idle_rounds = 0

        try:
            task_eval_config = _ensure_task_data_for_run(
                store,
                worker_id,
                task_eval_config,
                args,
            )
            prepared_eval_configs[task_eval_config.run_id] = task_eval_config
        except Exception as exc:
            reason = f"Task bundle download failed: {exc}"
            _emit(
                "task_bundle_download_failed",
                worker_id=worker_id,
                run_id=task_eval_config.run_id,
                task_id=task.task_id,
                error=str(exc),
            )
            store.requeue_claimed_task(task, worker_id, reason=reason)
            time.sleep(args.poll_interval_seconds)
            continue

        instance = store.claim_instance(
            worker_id,
            task.task_id,
            lease_ttl_seconds=args.instance_lease_ttl_seconds,
        )
        if instance is None:
            store.requeue_claimed_task(
                task,
                worker_id,
                reason=f"No available instance for snapshot={task.metadata.get('snapshot')}",
            )
            time.sleep(args.poll_interval_seconds)
            continue

        run_agent_config, run_agent_env, run_agent_profile = _agent_settings_for_run(
            store,
            agent_config,
        )
        _run_claimed_task(
            store,
            worker_id,
            task,
            instance,
            task_eval_config,
            run_agent_config,
            run_agent_env,
            run_agent_profile,
            args,
        )

    control_store.record_worker_heartbeat(worker_id, status="stopped")


def _ensure_task_data_for_run(
    store: RedisStore,
    worker_id: str,
    eval_config: EvalConfig,
    args: argparse.Namespace,
) -> EvalConfig:
    task_source = store.get_task_source()
    if (
        not task_source
        and args.run_id
        and eval_config.run_id == args.run_id
        and args.task_file_path
    ):
        task_source = {
            "bucket": DEFAULT_TASK_BUCKET,
            "file_path": args.task_file_path,
        }
    if not task_source:
        return eval_config

    task_root = ensure_task_bundle(
        task_root=args.task_root,
        run_id=eval_config.run_id,
        task_file_path=task_source["file_path"],
        task_bucket=task_source.get("bucket") or DEFAULT_TASK_BUCKET,
        wait_timeout_seconds=args.task_download_wait_timeout_seconds,
        lock_stale_seconds=args.task_download_lock_stale_seconds,
    )
    if str(task_root) == eval_config.task_root:
        return eval_config
    _emit(
        "task_bundle_ready",
        worker_id=worker_id,
        run_id=eval_config.run_id,
        task_root=str(task_root),
        task_source_key=store.task_source_key(),
        task_bucket=task_source["bucket"],
        task_file_path=task_source["file_path"],
    )
    return replace(eval_config, task_root=str(task_root))


def _run_claimed_task(
    store: RedisStore,
    worker_id: str,
    task: TaskSpec,
    instance: InstanceRecord,
    eval_config: EvalConfig,
    agent_config: AgentConfig,
    agent_env: dict[str, str],
    agent_profile: str,
    args: argparse.Namespace,
) -> None:
    store.record_worker_heartbeat(
        worker_id,
        status="running",
        task_id=task.task_id,
        instance_id=instance.instance_id,
    )
    _emit(
        "task_started",
        worker_id=worker_id,
        run_id=eval_config.run_id,
        task_id=task.task_id,
        instance_id=instance.instance_id,
        snapshot=task.metadata.get("snapshot"),
        agent_profile=agent_profile or None,
        model=agent_config.name,
        agent_factory=agent_config.agent_factory,
        action_space=agent_config.action_space,
        observation_type=agent_config.observation_type,
        eval_mode=agent_config.eval_mode,
    )

    stop_refresh = threading.Event()
    refresh_thread = threading.Thread(
        target=_refresh_leases_until_done,
        args=(store, worker_id, task, instance, args, stop_refresh),
        daemon=True,
    )
    refresh_thread.start()
    result: TaskResult | None = None
    artifact_uri = None
    error = None
    error_category = None
    runtime_agent_env = dict(agent_env)
    runtime_agent_env["ARENA_RUN_ID"] = eval_config.run_id
    previous_env = _apply_agent_env(runtime_agent_env)
    try:
        try:
            from engiworld.active_time import track_task_pauses

            def record_pause(reason, paused):
                store.set_task_pause(
                    task.task_id, instance.instance_id, worker_id,
                    int(task.metadata["attempt"]), reason, paused,
                )

            with track_task_pauses(record_pause):
                result = run_single_task(task, instance, eval_config, agent_config)
            error = result.error
            error_category = classify_task_error(error, result.error_category)
            try:
                artifact_uri = upload_task_artifacts(
                    eval_config,
                    task,
                    attempt=int(task.metadata.get("attempt", 1)),
                    local_result_dir=result.result_dir,
                )
            except Exception as upload_exc:
                upload_error = f"artifact upload failed: {upload_exc}"
                error = f"{error}; {upload_error}" if error else upload_error
        except Exception as exc:
            error = str(exc)
    finally:
        _restore_agent_env(previous_env)
        stop_refresh.set()
        refresh_thread.join(timeout=5)

    score = result.score if result is not None else 0.0
    result_dir = result.result_dir if result is not None else ""
    completion = store.complete_task_and_release_instance(
        task=task,
        instance=instance,
        worker_id=worker_id,
        score=score,
        artifact_uri=artifact_uri,
        error=error,
        error_category=error_category,
        quarantine_instance=False,
        recycle_instance=not args.reuse_instances,
    )
    reported_score = (
        None
        if completion.get("task_status") in {"api_incomplete", "infra_incomplete"}
        else score
    )
    store.record_worker_heartbeat(worker_id, status="alive")
    _emit(
        "task_finished",
        worker_id=worker_id,
        run_id=eval_config.run_id,
        task_id=task.task_id,
        instance_id=instance.instance_id,
        score=reported_score,
        artifact_uri=artifact_uri,
        result_dir=result_dir,
        error=error,
        error_category=error_category,
        completion=completion,
    )


def _agent_settings_for_run(
    store: RedisStore,
    default_agent_config: AgentConfig,
) -> tuple[AgentConfig, dict[str, str], str]:
    settings = store.agent_settings()
    raw_config = settings.get("agent_config") or {}
    overrides = {
        key: value
        for key, value in raw_config.items()
        if key in _AGENT_CONFIG_FIELD_NAMES and value is not None
    }
    agent_config = replace(default_agent_config, **overrides) if overrides else default_agent_config
    raw_env = settings.get("agent_env") or {}
    agent_env = {str(key): str(value) for key, value in raw_env.items()}
    return agent_config, agent_env, str(settings.get("agent_profile") or "")


def _apply_agent_env(agent_env: dict[str, str]) -> dict[str, str | None]:
    previous = {key: os.environ.get(key) for key in agent_env}
    for key, value in agent_env.items():
        os.environ[key] = value
    return previous


def _restore_agent_env(previous: dict[str, str | None]) -> None:
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def _refresh_leases_until_done(
    store: RedisStore,
    worker_id: str,
    task: TaskSpec,
    instance: InstanceRecord,
    args: argparse.Namespace,
    stop_event: threading.Event,
) -> None:
    interval = max(
        10.0,
        min(
            30.0,
            min(args.task_lease_ttl_seconds, args.instance_lease_ttl_seconds) / 3,
        ),
    )
    while not stop_event.wait(interval):
        ok = store.refresh_task_and_instance_leases(
            task_id=task.task_id,
            instance_id=instance.instance_id,
            worker_id=worker_id,
            task_lease_ttl_seconds=args.task_lease_ttl_seconds,
            instance_lease_ttl_seconds=args.instance_lease_ttl_seconds,
            runtime_phase=os.getenv("ARENA_TASK_RUNTIME_PHASE", ""),
        )
        if not ok:
            _emit(
                "lease_refresh_lost",
                worker_id=worker_id,
                run_id=store.run_id,
                task_id=task.task_id,
                instance_id=instance.instance_id,
            )
            return


def _install_signal_handlers(worker_id: str, store: RedisStore) -> None:
    def handle_signal(signum, frame):
        store.record_worker_heartbeat(worker_id, status=f"signal:{signum}")
        sys.exit(128 + signum)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)


def _emit(event: str, **payload) -> None:
    print(json.dumps({"event": event, **payload}, ensure_ascii=False), flush=True)


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


if __name__ == "__main__":
    main()
