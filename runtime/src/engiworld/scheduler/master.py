"""Master process entry point for distributed EngiWorld evaluation."""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path

from engiworld.agents.profiles import (
    ENGIWORLD_FORMAL_PROFILE_NAMES,
    ENGIWORLD_FORMAL_STEP_LIMITS,
    get_agent_profile,
    profile_names,
)
from engiworld.task_names import canonical_prefix
from engiworld.scheduler.redis_store import RedisStore
from engiworld.scheduler.schemas import (
    AgentConfig,
    EvalConfig,
    InstanceRecord,
    InstanceStatus,
    RunStatus,
    TaskSpec,
)
from engiworld.scheduler.task_bundle import DEFAULT_TASK_BUCKET, ensure_task_bundle
from engiworld.scheduler.task_loader import allocate_instances_by_snapshot, load_tasks
from engiworld.scheduler.volcengine_ecs import (
    EcsImage,
    InstanceLaunchGroup,
    VolcengineEcsClient,
    VolcengineLaunchConfig,
    match_images_by_snapshot,
)
from engiworld.scheduler.vm_osworld_update import (
    DEFAULT_VM_OSWORLD_BUNDLE_PATH,
    DEFAULT_VM_OSWORLD_BUCKET,
    VmOsworldBundleSpec,
    VmOsworldProvisionConfig,
    bundle_spec_dict,
    provision_config_dict,
    provision_vm_osworld,
    resolve_vm_osworld_bundle,
)

DEFAULT_V2_VM_OSWORLD_BUNDLE_PATH = "osworld-v2-vm-server-latest.tgz"


_EXPERIMENT_TASK_PREFIXES = {
    "gui_message_initial": "image-based-modeling/gui/",
    "cli_environment_initial": "image-based-modeling/cli/",
    "cli_message_initial": "image-based-modeling/cli/",
    "cli_message_no_readimg": "image-based-modeling/cli/",
}

_EXPERIMENT_PROFILE_ALIASES = {
    "gui-message": "gui_message_initial",
    "cli-environment": "cli_environment_initial",
    "cli-message": "cli_message_initial",
    "cli-message-no-readimg": "cli_message_no_readimg",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="EngiWorld GUI/CLI evaluation master")
    parser.add_argument(
        "command",
        choices=["plan", "start", "status", "reconcile", "run", "summary", "teardown"],
    )
    parser.add_argument(
        "--run-id",
        default=os.getenv("RUN_ID"),
        help=(
            "Evaluation run id. For start, omit it to let master generate one. "
            "For status/reconcile/run/summary/teardown, pass the target run id."
        ),
    )
    parser.add_argument(
        "--redis-url",
        default=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
    )
    parser.add_argument(
        "--benchmark",
        choices=["engiworld", "osworld-v1", "osworld-v2"],
        default=os.getenv("ENGIWORLD_BENCHMARK", os.getenv("ARENA_BENCHMARK", "engiworld")),
    )
    parser.add_argument("--engine-path", default="engine")
    parser.add_argument("--osworld-path", dest="engine_path", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    parser.add_argument(
        "--osworld-v2-path",
        default=os.getenv("OSWORLD_V2_PATH", "third_party/OSWorld-V2"),
    )
    parser.add_argument(
        "--v2-image-id",
        action="append",
        default=[],
        metavar="OS_TYPE=IMAGE_ID",
        help="OSWorld V2 image mapping, for example Ubuntu=image-xxx or Windows=image-yyy.",
    )
    parser.add_argument("--task-root", default="task")
    parser.add_argument(
        "--task-file-path",
        default=os.getenv("TASK_FILE_PATH"),
        help=(
            f"Optional object key/file path for the task bundle inside {DEFAULT_TASK_BUCKET}. "
            "Master and workers download it with the Volcengine S3 credentials."
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
    parser.add_argument(
        "--task-prefix",
        action="append",
        default=[],
        help=(
            "Task path prefix relative to --task-root. "
            "Examples: single-software/cli/calculix, single-software/gui/autocad. "
            "Can be specified multiple times. Initial-image CLI experiment profiles "
            "automatically select and stay within their paired task set."
        ),
    )
    parser.add_argument(
        "--task-id",
        action="append",
        default=[],
        metavar="ID",
        help=(
            "Run one exact task selected by stable base_task_id or by the task JSON id. "
            "Can be specified multiple times."
        ),
    )
    parser.add_argument(
        "--task-id-file",
        action="append",
        default=[],
        metavar="PATH",
        help=(
            "UTF-8 text file containing one stable base_task_id or task JSON id per line. "
            "Blank lines and lines beginning with # are ignored. Can be specified multiple times."
        ),
    )
    parser.add_argument("--task-limit", type=int, default=None)
    parser.add_argument(
        "--task-id-suffix",
        default=None,
        help=(
            "Suffix appended to each scheduler task_id. "
            "Default: local start time formatted as yyyymmdd-HHMMSS, "
            "generated once per master command."
        ),
    )
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument(
        "--retry-api-incomplete-from-run-id",
        default=None,
        help=(
            "For plan/start, create a new run containing only tasks marked "
            "api_incomplete in the specified prior run. The prior task bundle "
            "is reused when --task-file-path is omitted."
        ),
    )
    parser.add_argument(
        "--retry-infra-incomplete-from-run-id",
        default=None,
        help=(
            "For plan/start, create a new run containing only tasks marked "
            "infra_incomplete in the specified prior run. The prior task bundle, "
            "agent settings, and VM OSWorld settings are reused when not overridden."
        ),
    )
    parser.add_argument("--num-vms", type=int, default=128)
    parser.add_argument(
        "--instance-type",
        default=None,
        help=(
            "Volcengine ECS instance type for this master process. Overrides "
            "VOLCENGINE_INSTANCE_TYPE without changing the parent shell."
        ),
    )
    parser.add_argument(
        "--global-max-vms",
        type=int,
        default=int(os.getenv("MASTER_GLOBAL_MAX_VMS", "0")),
        help=(
            "Maximum ECS VM slots shared by all runs using this Redis database. "
            "Default MASTER_GLOBAL_MAX_VMS or 0 to disable global admission control."
        ),
    )
    parser.add_argument(
        "--global-vm-wait-interval-seconds",
        type=float,
        default=float(os.getenv("MASTER_GLOBAL_VM_WAIT_INTERVAL_SECONDS", "10")),
        help="Polling interval while this run waits for global VM slots.",
    )
    parser.add_argument("--wait-timeout-seconds", type=int, default=900)
    parser.add_argument(
        "--vm-osworld-bundle-path",
        default=os.getenv("VM_OSWORLD_BUNDLE_PATH"),
        help=(
            "TOS/S3 object key for the VM-side OSWorld server tgz. Defaults to "
            f"{DEFAULT_VM_OSWORLD_BUNDLE_PATH}. "
            "Its <key>.manifest.json companion is loaded before ECS provisioning."
        ),
    )
    parser.add_argument(
        "--vm-osworld-bundle-bucket",
        default=os.getenv("VM_OSWORLD_BUNDLE_BUCKET", DEFAULT_VM_OSWORLD_BUCKET),
    )
    parser.add_argument(
        "--vm-osworld-bundle-manifest-path",
        default=os.getenv("VM_OSWORLD_BUNDLE_MANIFEST_PATH"),
    )
    parser.add_argument(
        "--vm-osworld-presign-expires-seconds",
        type=int,
        default=int(os.getenv("VM_OSWORLD_PRESIGN_EXPIRES_SECONDS", "3600")),
    )
    parser.add_argument(
        "--vm-osworld-update-timeout-seconds",
        type=int,
        default=int(os.getenv("VM_OSWORLD_UPDATE_TIMEOUT_SECONDS", "600")),
    )
    parser.add_argument(
        "--vm-osworld-update-transport",
        choices=["auto", "execute", "cloud-assistant"],
        default=os.getenv("VM_OSWORLD_UPDATE_TRANSPORT", "auto"),
        help=(
            "How to invoke the updater in a newly launched VM. "
            "Default auto uses the OSWorld /execute endpoint first and falls back "
            "to Cloud Assistant for instances where /execute fails."
        ),
    )
    parser.add_argument(
        "--vm-osworld-execute-port",
        type=int,
        default=int(os.getenv("VM_OSWORLD_EXECUTE_PORT", "5000")),
    )
    parser.add_argument(
        "--vm-osworld-execute-wait-timeout-seconds",
        type=int,
        default=int(os.getenv("VM_OSWORLD_EXECUTE_WAIT_TIMEOUT_SECONDS", "300")),
    )
    parser.add_argument(
        "--vm-osworld-execute-request-timeout-seconds",
        type=int,
        default=int(os.getenv("VM_OSWORLD_EXECUTE_REQUEST_TIMEOUT_SECONDS", "30")),
    )
    parser.add_argument(
        "--vm-osworld-execute-max-workers",
        type=int,
        default=int(os.getenv("VM_OSWORLD_EXECUTE_MAX_WORKERS", "32")),
    )
    parser.add_argument(
        "--vm-osworld-cloud-assistant-wait-timeout-seconds",
        type=int,
        default=int(
            os.getenv("VM_OSWORLD_CLOUD_ASSISTANT_WAIT_TIMEOUT_SECONDS", "300")
        ),
    )
    parser.add_argument(
        "--vm-osworld-update-max-attempts",
        type=int,
        default=int(os.getenv("VM_OSWORLD_UPDATE_MAX_ATTEMPTS", "2")),
    )
    parser.add_argument(
        "--vm-osworld-max-failed-instances",
        type=int,
        default=int(os.getenv("VM_OSWORLD_MAX_FAILED_INSTANCES", "5")),
        help=(
            "Continue startup after terminating up to this many VMs whose OSWorld "
            "server provisioning failed (default: 5)."
        ),
    )
    parser.add_argument(
        "--vm-osworld-linux-updater-command",
        default=os.getenv(
            "VM_OSWORLD_LINUX_UPDATER_COMMAND",
            "/opt/arena-osworld-updater/update-osworld",
        ),
    )
    parser.add_argument(
        "--vm-osworld-windows-updater-command",
        default=os.getenv(
            "VM_OSWORLD_WINDOWS_UPDATER_COMMAND",
            "C:\\ProgramData\\ArenaOSWorldUpdater\\update-osworld.ps1",
        ),
    )
    parser.add_argument(
        "--task-run-timeout-seconds",
        type=int,
        default=int(os.getenv("TASK_RUN_TIMEOUT_SECONDS", str(5 * 60 * 60))),
        help="Active task seconds excluding registered pauses (default: 18000, 5 hours); exhaustion completes evaluation with score 0 and no task retry.",
    )
    parser.add_argument(
        "--reconcile-interval-seconds",
        type=float,
        default=float(os.getenv("MASTER_RECONCILE_INTERVAL_SECONDS", "10")),
    )
    parser.add_argument(
        "--reconcile-lock-ttl-seconds",
        type=int,
        default=int(os.getenv("MASTER_RECONCILE_LOCK_TTL_SECONDS", "60")),
    )
    parser.add_argument(
        "--no-auto-teardown",
        action="store_true",
        help="Do not terminate ECS instances automatically when all tasks are terminal.",
    )
    parser.add_argument("--retain-failed-instances", action="store_true",
                        help="Retain failed task VMs for debugging; they still consume VM capacity.")
    parser.add_argument(
        "--retain-api-incomplete-instances",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Retain a VM when its task ends with a model API interruption so the GUI "
            "state remains available for recovery. Enabled by default."
        ),
    )
    parser.add_argument("--delete-retained-instances", action="store_true",
                        help="Include retained debugging VMs in explicit teardown.")
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and print the task/instance plan without touching Redis or ECS.",
    )
    parser.add_argument(
        "--check-images",
        action="store_true",
        help="In plan/dry-run mode, also call Volcengine to verify configured images.",
    )
    parser.add_argument(
        "--follow",
        action="store_true",
        help=(
            "Only for start: after launching instances and enqueueing tasks, "
            "run the reconcile loop in the same process until the run is terminal."
        ),
    )
    parser.add_argument(
        "--agent",
        default=os.getenv("ARENA_AGENT"),
        choices=profile_names(),
        help=(
            "Named agent profile used for this run. Required for a new plan/start; "
            "retry runs may inherit the source run profile."
        ),
    )
    parser.add_argument(
        "--agent-env",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help=(
            "Non-secret environment override stored with the run. "
            "Use for values like OPENAI_BASE_URL, not API keys."
        ),
    )
    parser.add_argument("--action-space", default=None)
    parser.add_argument(
        "--observation-type",
        default=None,
        choices=["screenshot", "a11y_tree", "screenshot_a11y_tree", "som", "terminal"],
    )
    parser.add_argument(
        "--eval-mode",
        default=None,
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
        help="Interaction mode. 'auto' selects GUI/CLI from the EngiWorld task path.",
    )
    parser.add_argument(
        "--experiment-profile",
        default=None,
        help=(
            "EngiWorld prompt/observation profile, for example gui_main, gui_message_initial, "
            "gui_screenshot_a11y, cli_main, cli_message_initial, cli_message_no_readimg, "
            "cli_environment_initial, cli_text, or open_engineering."
        ),
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help=(
            "Uniform debugging limit. Formal EngiWorld profiles reject this option; "
            "use their validated GUI/CLI/Multi-software/Open-ended limits."
        ),
    )
    parser.add_argument(
        "--allow-nonstandard-step-limits",
        action="store_true",
        help=(
            "Permit nonstandard step budgets for a diagnostic run. "
            "Never use this flag for formal experiment results."
        ),
    )
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
    parser.add_argument(
        "--history-turns",
        type=int,
        default=None,
        help="Override the rolling interaction-history window for this run.",
    )
    parser.add_argument("--bash-timeout", type=int, default=None)
    parser.add_argument(
        "--record-video",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    parser.add_argument("--sleep-after-execution", type=float, default=None)
    parser.add_argument("--screen-width", type=int, default=None)
    parser.add_argument("--screen-height", type=int, default=None)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.global_max_vms < 0:
        parser.error("--global-max-vms must be zero or greater")
    if args.global_vm_wait_interval_seconds <= 0:
        parser.error("--global-vm-wait-interval-seconds must be greater than zero")
    if args.instance_type:
        os.environ["VOLCENGINE_INSTANCE_TYPE"] = args.instance_type
    if not args.vm_osworld_bundle_path:
        args.vm_osworld_bundle_path = (
            DEFAULT_V2_VM_OSWORLD_BUNDLE_PATH
            if args.benchmark == "osworld-v2"
            else DEFAULT_VM_OSWORLD_BUNDLE_PATH
        )
    _resolve_run_id(args, parser)
    if args.command in {"plan", "start"}:
        try:
            _prepare_incomplete_retry_from_args(args)
            (
                args.resolved_agent_profile,
                args.resolved_agent_config,
                args.resolved_agent_env,
            ) = _agent_settings_from_args(args)
            _bind_experiment_task_prefixes(args)
        except ValueError as exc:
            parser.error(str(exc))
    _prepare_task_root_from_args(args)
    eval_config = EvalConfig(
        run_id=args.run_id,
        redis_url=args.redis_url,
        benchmark=args.benchmark,
        engine_path=args.engine_path,
        osworld_v2_path=args.osworld_v2_path,
        task_root=args.task_root,
        result_dir=args.result_dir,
        s3_bucket=args.s3_bucket,
        s3_upload=args.s3_upload,
        keep_local_results=args.keep_local_results,
    )

    if args.command == "plan":
        task_id_suffix = _resolve_task_id_suffix(args)
        tasks = _load_tasks_from_args(args, task_id_suffix=task_id_suffix)
        plan = _build_plan(tasks, args.num_vms)
        plan["global_max_vms"] = args.global_max_vms
        plan["instance_type"] = os.getenv("VOLCENGINE_INSTANCE_TYPE")
        agent_profile, agent_config, agent_env = _resolved_agent_settings(args)
        plan["agent"] = _agent_summary(agent_profile, agent_config, agent_env)
        if _has_task_source(args):
            plan["task_bundle"] = _task_bundle_summary(args)
        if args.retry_api_incomplete_from_run_id:
            plan["retry_api_incomplete_from_run_id"] = (
                args.retry_api_incomplete_from_run_id
            )
        if args.retry_infra_incomplete_from_run_id:
            plan["retry_infra_incomplete_from_run_id"] = (
                args.retry_infra_incomplete_from_run_id
            )
        if args.vm_osworld_bundle_path:
            plan["vm_osworld_bundle"] = _requested_vm_osworld_bundle_summary(args)
        if args.check_images:
            plan["image_matches"] = _image_match_summary(plan["snapshots"])
        _print_json(plan)
        return

    if args.command == "start":
        _start(eval_config, args)
        return

    store = RedisStore(args.redis_url, args.run_id)
    if args.command == "status":
        _print_json(store.status())
    elif args.command == "reconcile":
        _print_json(_reconcile_once(store, args))
    elif args.command == "run":
        try:
            _run_reconcile_loop(store, args)
        except KeyboardInterrupt:
            _print_json(
                {
                    "event": "master_interrupted_cleanup",
                    **_abort_run(store, reason="master run interrupted"),
                }
            )
            raise SystemExit(130)
    elif args.command == "summary":
        _print_json(store.save_run_summary())
    elif args.command == "teardown":
        _print_json(_teardown(store, include_retained=args.delete_retained_instances))


def _start(eval_config: EvalConfig, args: argparse.Namespace) -> None:
    task_id_suffix = _resolve_task_id_suffix(args)
    tasks = _load_tasks_from_args(args, task_id_suffix=task_id_suffix)
    plan = _build_plan(tasks, args.num_vms)
    if args.global_max_vms > 0 and plan["instance_count"] > args.global_max_vms:
        raise ValueError(
            f"This run requires {plan['instance_count']} VMs, exceeding "
            f"--global-max-vms={args.global_max_vms}; reduce --num-vms"
        )
    plan["global_max_vms"] = args.global_max_vms
    plan["instance_type"] = os.getenv("VOLCENGINE_INSTANCE_TYPE")
    agent_profile, agent_config, agent_env = _resolved_agent_settings(args)
    plan["agent"] = _agent_summary(agent_profile, agent_config, agent_env)
    if args.dry_run:
        _print_json(plan)
        return

    vm_osworld_bundle, vm_osworld_provision_config = _vm_osworld_settings_from_args(args)
    if vm_osworld_bundle:
        plan["vm_osworld_bundle"] = bundle_spec_dict(vm_osworld_bundle)

    store = RedisStore(eval_config.redis_url, eval_config.run_id)
    store.register_run(
        eval_config,
        total_tasks=len(tasks),
        instance_count=plan["instance_count"],
        allocation=plan["allocation"],
        snapshot_os_type=plan["snapshot_os_type"],
        agent_profile=agent_profile,
        agent_config=asdict(agent_config),
        agent_env=agent_env,
        retry_source_run_id=(
            args.retry_api_incomplete_from_run_id
            or args.retry_infra_incomplete_from_run_id
        ),
        vm_osworld_bundle=bundle_spec_dict(vm_osworld_bundle),
        vm_osworld_provision_config=provision_config_dict(
            vm_osworld_provision_config
        ),
    )
    store.client.hset(store.key("meta"), mapping={
        "retain_failed_instances": str(getattr(args, "retain_failed_instances", False)).lower(),
        "retain_api_incomplete_instances": str(
            getattr(args, "retain_api_incomplete_instances", True)
        ).lower(),
    })
    if _has_task_source(args):
        store.set_task_source(args.task_file_path)

    ecs: VolcengineEcsClient | None = None
    instances: list[InstanceRecord] = []
    cleanup_instances: list[InstanceRecord] = []
    instances_registered = False
    slots_acquired = 0
    vm_osworld_report = None
    try:
        slots_acquired = _wait_for_global_vm_slots(
            store,
            plan["instance_count"],
            args,
            reason="initial_provisioning",
        )
        launch_config = VolcengineLaunchConfig.from_env()
        ecs = VolcengineEcsClient(launch_config)
        images = ecs.list_images()
        image_by_snapshot = match_images_by_snapshot(
            plan["snapshots"],
            images,
            image_visibility=launch_config.image_visibility,
        )
        store.client.hset(store.key("meta"), mapping={"launch_templates": json.dumps({
            snapshot: {
                "snapshot": snapshot, "image_id": image.image_id,
                "image_name": image.image_name, "os_type": plan["snapshot_os_type"][snapshot],
                "system_disk_size_gb": image.disk_size_gb,
                "image_visibility": launch_config.image_visibility,
            } for snapshot, image in image_by_snapshot.items()
        })})

        launch_groups = [
            InstanceLaunchGroup(
                image=image_by_snapshot[snapshot],
                count=count,
                snapshot=snapshot,
                os_type=plan["snapshot_os_type"][snapshot],
            )
            for snapshot, count in plan["allocation"].items()
        ]
        if slots_acquired:
            remaining_slots = slots_acquired
            limited_groups = []
            for group in launch_groups:
                count = min(group.count, remaining_slots)
                if count:
                    limited_groups.append(replace(group, count=count))
                remaining_slots -= count
            launch_groups = limited_groups
        instances = ecs.run_instance_groups(
            launch_groups,
            run_id=eval_config.run_id,
            wait_timeout_seconds=args.wait_timeout_seconds,
        )
        unused_slots = max(0, slots_acquired - len(instances))
        if unused_slots:
            store.release_global_vm_slots(count=unused_slots)
            slots_acquired -= unused_slots
        cleanup_instances = list(instances)

        if vm_osworld_bundle and vm_osworld_provision_config:
            instances, vm_osworld_report = provision_vm_osworld(
                ecs,
                instances,
                bundle=vm_osworld_bundle,
                config=vm_osworld_provision_config,
                run_id=eval_config.run_id,
            )
            failed_instance_ids = list(
                vm_osworld_report.get("terminated_failed_instance_ids", [])
            )
            if failed_instance_ids:
                store.release_global_vm_slots(instance_ids=failed_instance_ids)
                slots_acquired -= len(failed_instance_ids)

        store.register_instances(instances)
        instances_registered = True
        store.enqueue_tasks(tasks)
        store.mark_run_status(RunStatus.RUNNING)
        _print_json(
            {
                "run_id": eval_config.run_id,
                "benchmark": eval_config.benchmark,
                "task_id_suffix": task_id_suffix,
                "status": RunStatus.RUNNING.value,
                "task_count": len(tasks),
                "instance_count": len(instances),
                "launch_group_count": len(launch_groups),
                "launch_mode": "batch_submit_then_wait",
                "image_visibility": launch_config.image_visibility,
                "instance_type": launch_config.instance_type,
                "snapshots": plan["snapshots"],
                "allocation": plan["allocation"],
                "global_vm_capacity": store.global_vm_capacity(),
                "agent": _agent_summary(agent_profile, agent_config, agent_env),
                "task_bundle": _task_bundle_summary(args) if _has_task_source(args) else None,
                "task_source_key": store.task_source_key() if _has_task_source(args) else None,
                "retry_api_incomplete_from_run_id": (
                    args.retry_api_incomplete_from_run_id
                ),
                "retry_infra_incomplete_from_run_id": (
                    args.retry_infra_incomplete_from_run_id
                ),
                "vm_osworld": vm_osworld_report,
            }
        )
        if args.follow:
            _run_reconcile_loop(store, args)
    except KeyboardInterrupt:
        if ecs and cleanup_instances and not instances_registered:
            ecs.terminate_instances(
                [instance.instance_id for instance in cleanup_instances]
            )
            store.release_global_vm_slots(count=slots_acquired)
            slots_acquired = 0
        elif slots_acquired and not instances_registered:
            store.release_global_vm_slots(count=slots_acquired)
            slots_acquired = 0
        _print_json(
            {
                "event": "master_interrupted_cleanup",
                **_abort_run(store, reason="master start interrupted"),
            }
        )
        raise SystemExit(130)
    except Exception:
        cleanup_succeeded = not cleanup_instances
        if ecs and cleanup_instances and not instances_registered:
            try:
                ecs.terminate_instances(
                    [instance.instance_id for instance in cleanup_instances]
                )
                cleanup_succeeded = True
            except Exception:
                pass
        if slots_acquired and not instances_registered and cleanup_succeeded:
            store.release_global_vm_slots(count=slots_acquired)
        store.mark_run_status(RunStatus.FAILED)
        raise


def _run_reconcile_loop(store: RedisStore, args: argparse.Namespace) -> None:
    provisioning = {}
    with ThreadPoolExecutor(max_workers=1) as executor:
        while True:
            report = _reconcile_once(store, args, executor=executor, provisioning=provisioning)
            print(json.dumps(report, ensure_ascii=False), flush=True)
            if report.get("run_completed"):
                return
            time.sleep(args.reconcile_interval_seconds)


def _reconcile_once(store: RedisStore, args: argparse.Namespace, *, executor=None, provisioning=None) -> dict:
    report = store.requeue_expired_leases(
        task_run_timeout_seconds=args.task_run_timeout_seconds,
        lock_ttl_seconds=args.reconcile_lock_ttl_seconds,
    )
    if not report.get("lock_acquired", True):
        return {"run_id": store.run_id, **report}

    terminated = []
    released_capacity = None
    replacements: list[InstanceRecord] = []
    vm_osworld_report = None
    ecs: VolcengineEcsClient | None = None
    future = provisioning.get("future") if provisioning is not None else None
    if future is not None and future.done():
        replacements, vm_osworld_report = future.result()
        provisioning.pop("future")
        future = None
    instances_to_terminate = _dedupe_instance_infos(
        [
            *report.get("instances_to_terminate", []),
            *store.pending_terminating_instances(),
        ]
    )
    report["instances_to_terminate"] = instances_to_terminate
    run_completed_before_replacement = store.is_run_terminal()
    if instances_to_terminate:
        launch_config = VolcengineLaunchConfig.from_env()
        ecs = VolcengineEcsClient(launch_config)
        instance_ids = [item["instance_id"] for item in instances_to_terminate]
        ecs.terminate_instances(instance_ids)
        store.mark_instances_terminated(instance_ids, reason="terminated by master reconcile")
        released_capacity = store.release_global_vm_slots(instance_ids=instance_ids)
        terminated = instance_ids

    replacement_demand = {}
    replacement_sources = []
    if not run_completed_before_replacement and future is None:
        replacement_demand = store.replacement_demand_by_snapshot()
        replacement_sources = store.replacement_sources_for_demand(
            replacement_demand
        )
        if replacement_sources:
            if ecs is None:
                launch_config = VolcengineLaunchConfig.from_env()
                ecs = VolcengineEcsClient(launch_config)
            if executor is not None:
                future = executor.submit(_provision_replacement_instances, store, args, ecs, replacement_sources)
                provisioning["future"] = future
            else:
                replacements, vm_osworld_report = _provision_replacement_instances(
                    store, args, ecs, replacement_sources,
                )

    summary = None
    teardown_report = None
    run_completed = store.is_run_terminal() and future is None
    if run_completed:
        summary = store.save_run_summary()
        store.mark_run_completion_signal(summary)
        if not args.no_auto_teardown:
            teardown_report = _teardown(store)

    return {
        "run_id": store.run_id,
        **report,
        "terminated_instances": terminated,
        "released_global_vm_capacity": released_capacity,
        "replacement_instances": [instance.instance_id for instance in replacements],
        "replacement_demand": replacement_demand,
        "replacement_missing_templates": sorted(
            set(replacement_demand)
            - {str(item.get("snapshot", "default")) for item in replacement_sources}
        ),
        "vm_osworld": vm_osworld_report,
        "replacement_skipped_run_completed": bool(
            instances_to_terminate and run_completed_before_replacement
        ),
        "run_completed": run_completed,
        "summary": _compact_summary(summary) if summary else None,
        "teardown": teardown_report,
    }


def _dedupe_instance_infos(items: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    for item in items:
        instance_id = item.get("instance_id")
        if instance_id and instance_id not in by_id:
            by_id[instance_id] = item
    return list(by_id.values())


def _wait_for_global_vm_slots(
    store: RedisStore,
    count: int,
    args: argparse.Namespace,
    *,
    reason: str,
) -> int:
    if count <= 0:
        return 0
    limit = args.global_max_vms
    if limit <= 0:
        limit = int(store.global_vm_capacity().get("limit") or 0)
    if limit <= 0:
        return 0
    if count > limit:
        raise ValueError(
            f"VM slot request {count} exceeds the active global limit {limit}"
        )
    while True:
        capacity = store.try_reserve_global_vm_slots(count, limit, allow_partial=True)
        status = capacity.get("status")
        if status == "acquired":
            _print_json(
                {
                    "event": "global_vm_slots_acquired",
                    "run_id": store.run_id,
                    "reason": reason,
                    **capacity,
                }
            )
            return int(capacity.get("acquired", count))
        if status == "limit_mismatch":
            raise ValueError(
                "MASTER_GLOBAL_MAX_VMS differs from the active global capacity "
                f"limit: requested={limit}, active={capacity.get('limit')}"
            )
        _print_json(
            {
                "event": "global_vm_slots_waiting",
                "run_id": store.run_id,
                "reason": reason,
                **capacity,
            }
        )
        if reason == "replacement_provisioning":
            return -1
        time.sleep(args.global_vm_wait_interval_seconds)


def _provision_replacement_instances(
    store: RedisStore,
    args: argparse.Namespace,
    ecs: VolcengineEcsClient,
    replacement_sources: list[dict],
) -> tuple[list[InstanceRecord], dict | None]:
    replacement_count = len(replacement_sources)
    acquired_slots = _wait_for_global_vm_slots(
        store,
        replacement_count,
        args,
        reason="replacement_provisioning",
    )
    if acquired_slots == -1:
        return [], {"status": "waiting_for_capacity"}
    if acquired_slots:
        replacement_sources = replacement_sources[:acquired_slots]
    try:
        replacements = _launch_replacement_instances(
            ecs,
            replacement_sources,
            run_id=store.run_id,
            wait_timeout_seconds=args.wait_timeout_seconds,
        )
        unused_slots = max(0, acquired_slots - len(replacements))
        if unused_slots:
            store.release_global_vm_slots(count=unused_slots)
            acquired_slots -= unused_slots
    except Exception:
        if acquired_slots:
            store.release_global_vm_slots(count=acquired_slots)
        raise

    vm_osworld_report = None
    vm_settings = store.vm_osworld_settings()
    if not vm_settings.get("bundle"):
        store.register_instances(replacements)
        return replacements, vm_osworld_report

    store.register_instances(
        replacements,
        status=InstanceStatus.PROVISIONING.value,
    )
    bundle = VmOsworldBundleSpec.from_dict(vm_settings["bundle"])
    provision_config = VmOsworldProvisionConfig.from_dict(
        vm_settings.get("provision_config")
    )
    try:
        replacements, vm_osworld_report = provision_vm_osworld(
            ecs,
            replacements,
            bundle=bundle,
            config=provision_config,
            run_id=store.run_id,
        )
        failed_replacement_ids = list(
            vm_osworld_report.get("terminated_failed_instance_ids", [])
        )
        if failed_replacement_ids:
            store.mark_instances_terminated(
                failed_replacement_ids,
                reason="VM OSWorld provisioning failed within tolerance",
            )
            store.release_global_vm_slots(instance_ids=failed_replacement_ids)
    except Exception as exc:
        error = f"VM OSWorld provisioning failed: {type(exc).__name__}: {exc}"
        for instance in replacements:
            store.mark_instance_terminating(instance.instance_id, reason=error)
        return [], {
            "status": "failed",
            "error": error,
            "instances": [instance.instance_id for instance in replacements],
        }

    store.mark_instances_available(replacements)
    return replacements, vm_osworld_report


def _launch_replacement_instances(
    ecs: VolcengineEcsClient,
    terminated_instances: list[dict],
    run_id: str,
    wait_timeout_seconds: int,
) -> list[InstanceRecord]:
    grouped: dict[tuple[str, str, str, str, str, int | None], dict] = {}
    for item in terminated_instances:
        image_id = item.get("image_id")
        if not image_id:
            continue
        key = (
            item["snapshot"],
            image_id,
            item.get("image_name", item["snapshot"]),
            item.get("image_visibility", ecs.config.image_visibility),
            item.get("os_type", "Ubuntu"),
            _optional_int(item.get("system_disk_size_gb")),
        )
        grouped.setdefault(key, {"count": 0, "item": item})
        grouped[key]["count"] += 1

    launch_groups = []
    for (
        snapshot,
        image_id,
        image_name,
        image_visibility,
        os_type,
        system_disk_size_gb,
    ), data in grouped.items():
        launch_groups.append(
            InstanceLaunchGroup(
                image=EcsImage(
                    image_id=image_id,
                    image_name=image_name,
                    os_type=data["item"].get("image_os_type", os_type),
                    status="available",
                    visibility=image_visibility,
                    raw=None,
                    disk_size_gb=system_disk_size_gb,
                ),
                count=data["count"],
                snapshot=snapshot,
                os_type=os_type,
                system_disk_size_gb=system_disk_size_gb,
            )
        )

    if not launch_groups:
        return []
    return ecs.run_instance_groups(
        launch_groups,
        run_id=run_id,
        wait_timeout_seconds=wait_timeout_seconds,
    )


def _teardown(store: RedisStore, include_retained: bool = False) -> dict:
    instance_ids = store.active_instance_ids() if include_retained else store.cleanup_instance_ids()
    store.mark_run_status(RunStatus.TEARING_DOWN)
    if instance_ids:
        launch_config = VolcengineLaunchConfig.from_env()
        ecs = VolcengineEcsClient(launch_config)
        ecs.terminate_instances(instance_ids)
        store.mark_instances_terminated(instance_ids, reason="run teardown")
        store.release_global_vm_slots(instance_ids=instance_ids)
    elif not store.retained_instances():
        store.release_global_vm_slots()
    store.mark_run_status(RunStatus.COMPLETED)
    summary = store.save_run_summary()
    store.mark_run_completion_signal(summary)
    return {
        "run_id": store.run_id,
        "terminated_instances": len(instance_ids),
        "instance_ids": instance_ids,
        "retained_instances": store.retained_instances(),
        "summary": _compact_summary(summary),
    }


def _abort_run(store: RedisStore, reason: str) -> dict:
    instance_ids = store.cleanup_instance_ids()
    terminated_instances: list[str] = []
    if instance_ids:
        try:
            launch_config = VolcengineLaunchConfig.from_env()
            ecs = VolcengineEcsClient(launch_config)
            ecs.terminate_instances(instance_ids)
            terminated_instances = instance_ids
            store.release_global_vm_slots(instance_ids=instance_ids)
        except Exception as exc:
            try:
                store.mark_run_status(RunStatus.FAILED)
            except Exception:
                pass
            return {
                "run_id": store.run_id,
                "status": "cleanup_failed",
                "reason": reason,
                "redis_cleared": False,
                "instances_to_terminate": instance_ids,
                "terminated_instances": terminated_instances,
                "error": f"{type(exc).__name__}: {exc}",
            }
    elif not store.retained_instances():
        store.release_global_vm_slots()

    if store.retained_instances():
        # Keep Redis evidence and prevent further claims after interruption.
        store.mark_run_status(RunStatus.FAILED)
        return {"run_id": store.run_id, "status": "aborted", "reason": reason,
                "redis_cleared": False, "terminated_instances": terminated_instances,
                "retained_instances": store.retained_instances()}
    clear_report = store.clear_run_state()
    return {
        "run_id": store.run_id,
        "status": "aborted",
        "reason": reason,
        "redis_cleared": True,
        "terminated_instances": terminated_instances,
        **clear_report,
    }


def _resolve_task_id_suffix(args: argparse.Namespace) -> str:
    return args.task_id_suffix or datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def _resolve_run_id(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if args.run_id:
        return
    if args.command == "start":
        args.run_id = "eval-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        return
    if args.command == "plan":
        args.run_id = "plan"
        return
    parser.error(f"--run-id is required for {args.command}")


def _load_tasks_from_args(args: argparse.Namespace, task_id_suffix: str) -> list[TaskSpec]:
    if args.benchmark == "osworld-v2" and sys.version_info < (3, 12):
        raise ValueError("OSWorld V2 scheduling requires Python 3.12 or newer.")
    retry_base_task_ids = set(
        getattr(args, "retry_api_incomplete_base_task_ids", [])
    ) | set(getattr(args, "retry_infra_incomplete_base_task_ids", []))
    requested_task_ids = _requested_task_ids(args)
    if requested_task_ids and args.task_limit is not None:
        raise ValueError("--task-limit cannot be combined with --task-id/--task-id-file")
    if requested_task_ids and retry_base_task_ids:
        raise ValueError(
            "--task-id/--task-id-file cannot be combined with "
            "an incomplete-task retry run"
        )
    tasks = load_tasks(
        task_root=args.task_root,
        path_prefixes=args.task_prefix,
        limit=None if retry_base_task_ids or requested_task_ids else args.task_limit,
        max_attempts=args.max_attempts,
        task_id_suffix=task_id_suffix,
        benchmark=args.benchmark,
        osworld_v2_path=args.osworld_v2_path,
        v2_image_ids=_parse_v2_image_ids(args.v2_image_id),
    )
    if requested_task_ids:
        tasks = _select_tasks_by_ids(tasks, requested_task_ids)
    if retry_base_task_ids:
        tasks = [
            task
            for task in tasks
            if str(task.metadata.get("base_task_id") or "") in retry_base_task_ids
        ]
        if args.task_limit is not None:
            tasks = tasks[: args.task_limit]
    if not tasks:
        if retry_base_task_ids:
            raise ValueError(
                "No task files in the current task bundle match the incomplete "
                "tasks from the prior run."
            )
        raise ValueError("No tasks found for the requested task root/prefix/limit.")
    return tasks


def _requested_task_ids(args: argparse.Namespace) -> list[str]:
    values = list(getattr(args, "task_id", None) or [])
    for raw_path in getattr(args, "task_id_file", None) or []:
        path = Path(raw_path).expanduser()
        if not path.is_file():
            raise ValueError(f"Task ID file does not exist or is not a file: {path}")
        file_values = [
            line.strip()
            for line in path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if not file_values:
            raise ValueError(f"Task ID file contains no task IDs: {path}")
        values.extend(file_values)

    selected: list[str] = []
    seen: set[str] = set()
    for value in values:
        task_id = str(value).strip().strip("/\\").replace("\\", "/")
        if not task_id or task_id in seen:
            continue
        selected.append(task_id)
        seen.add(task_id)
    return selected


def _select_tasks_by_ids(tasks: list[TaskSpec], requested_ids: list[str]) -> list[TaskSpec]:
    matches: dict[str, list[TaskSpec]] = defaultdict(list)
    for task in tasks:
        stable_ids = {
            str(task.metadata.get("base_task_id") or "").strip(),
            str(task.metadata.get("source_task_id") or "").strip(),
        }
        for stable_id in stable_ids - {""}:
            matches[stable_id].append(task)

    missing = [task_id for task_id in requested_ids if not matches.get(task_id)]
    ambiguous = {
        task_id: candidates
        for task_id in requested_ids
        if len(candidates := matches.get(task_id, [])) > 1
    }
    if missing or ambiguous:
        problems = []
        if missing:
            problems.append("missing task IDs: " + ", ".join(missing))
        if ambiguous:
            details = "; ".join(
                f"{task_id} -> "
                + ", ".join(
                    str(task.metadata.get("base_task_id") or task.task_id)
                    for task in candidates
                )
                for task_id, candidates in ambiguous.items()
            )
            problems.append("ambiguous task IDs: " + details)
        raise ValueError("; ".join(problems))

    selected: list[TaskSpec] = []
    seen_task_ids: set[str] = set()
    for requested_id in requested_ids:
        task = matches[requested_id][0]
        stable_id = str(task.metadata.get("base_task_id") or task.task_id)
        if stable_id in seen_task_ids:
            continue
        selected.append(task)
        seen_task_ids.add(stable_id)
    return selected


def _bind_experiment_task_prefixes(args: argparse.Namespace) -> None:
    """Keep initial-image experiment profiles within their paired CLI task set."""
    config = getattr(args, "resolved_agent_config", None)
    raw_profile = getattr(config, "experiment_profile", None) or getattr(
        args, "experiment_profile", None
    )
    profile = str(raw_profile or "").strip().lower()
    profile = _EXPERIMENT_PROFILE_ALIASES.get(profile, profile)
    expected_prefix = _EXPERIMENT_TASK_PREFIXES.get(profile)
    if not expected_prefix:
        return

    requested_prefixes = [canonical_prefix(p) for p in (getattr(args, "task_prefix", None) or [])]
    if not requested_prefixes:
        args.task_prefix = [expected_prefix]
        return

    invalid_prefixes = [
        prefix
        for prefix in requested_prefixes
        if not str(prefix).strip("/\\").replace("\\", "/").lower().startswith(
            expected_prefix
        )
    ]
    if invalid_prefixes:
        formatted = ", ".join(repr(prefix) for prefix in invalid_prefixes)
        raise ValueError(
            f"Experiment profile {profile!r} is bound to tasks under "
            f"{expected_prefix!r}; incompatible --task-prefix: {formatted}"
        )


def _prepare_incomplete_retry_from_args(args: argparse.Namespace) -> None:
    api_source_run_id = args.retry_api_incomplete_from_run_id
    infra_source_run_id = args.retry_infra_incomplete_from_run_id
    if api_source_run_id and infra_source_run_id:
        raise ValueError(
            "--retry-api-incomplete-from-run-id and "
            "--retry-infra-incomplete-from-run-id cannot be combined"
        )
    source_run_id = api_source_run_id or infra_source_run_id
    if not source_run_id:
        args.retry_api_incomplete_base_task_ids = []
        args.retry_infra_incomplete_base_task_ids = []
        return
    if args.command not in {"plan", "start"}:
        raise ValueError("Incomplete-task retry options are only valid for plan/start")
    if source_run_id == args.run_id:
        raise ValueError("The incomplete-task retry must use a new --run-id")

    source_store = RedisStore(args.redis_url, source_run_id)
    if api_source_run_id:
        category = "api_incomplete"
        base_task_ids = source_store.api_incomplete_base_task_ids()
    else:
        category = "infra_incomplete"
        base_task_ids = source_store.infra_incomplete_base_task_ids()
    if not base_task_ids:
        raise ValueError(f"Run {source_run_id!r} has no {category} tasks")
    args.retry_api_incomplete_base_task_ids = base_task_ids if api_source_run_id else []
    args.retry_infra_incomplete_base_task_ids = (
        base_task_ids if infra_source_run_id else []
    )
    source_agent_settings = source_store.agent_settings()
    args.retry_source_agent_profile = source_agent_settings.get("agent_profile") or None
    args.retry_source_agent_config = source_agent_settings.get("agent_config") or {}
    args.retry_source_agent_env = source_agent_settings.get("agent_env") or {}
    args.retry_source_vm_osworld_settings = source_store.vm_osworld_settings()

    if not args.task_file_path:
        source = source_store.get_task_source()
        if source:
            args.task_file_path = source["file_path"]


def _prepare_task_root_from_args(args: argparse.Namespace) -> None:
    if args.command not in {"plan", "start"} or not _has_task_source(args):
        return
    args.task_root = str(
        ensure_task_bundle(
            task_root=args.task_root,
            run_id=args.run_id,
            task_file_path=args.task_file_path,
            wait_timeout_seconds=args.task_download_wait_timeout_seconds,
            lock_stale_seconds=args.task_download_lock_stale_seconds,
        )
    )


def _task_bundle_summary(args: argparse.Namespace) -> dict:
    return {
        "downloaded_task_root": args.task_root,
        "task_source_key": f"task_source_{args.run_id}",
        "task_bucket": DEFAULT_TASK_BUCKET,
        "task_file_path": args.task_file_path,
    }


def _requested_vm_osworld_bundle_summary(args: argparse.Namespace) -> dict:
    return {
        "bucket": args.vm_osworld_bundle_bucket,
        "object_key": args.vm_osworld_bundle_path,
        "manifest_key": args.vm_osworld_bundle_manifest_path
        or f"{args.vm_osworld_bundle_path}.manifest.json",
    }


def _vm_osworld_settings_from_args(
    args: argparse.Namespace,
) -> tuple[VmOsworldBundleSpec | None, VmOsworldProvisionConfig | None]:
    if args.vm_osworld_bundle_path:
        bundle = resolve_vm_osworld_bundle(
            bucket=args.vm_osworld_bundle_bucket,
            object_key=args.vm_osworld_bundle_path,
            manifest_key=args.vm_osworld_bundle_manifest_path,
        )
        config = VmOsworldProvisionConfig(
            presign_expires_seconds=args.vm_osworld_presign_expires_seconds,
            update_timeout_seconds=args.vm_osworld_update_timeout_seconds,
            transport=args.vm_osworld_update_transport,
            execute_port=args.vm_osworld_execute_port,
            execute_wait_timeout_seconds=(
                args.vm_osworld_execute_wait_timeout_seconds
            ),
            execute_request_timeout_seconds=(
                args.vm_osworld_execute_request_timeout_seconds
            ),
            execute_max_workers=args.vm_osworld_execute_max_workers,
            cloud_assistant_wait_timeout_seconds=(
                args.vm_osworld_cloud_assistant_wait_timeout_seconds
            ),
            max_attempts=args.vm_osworld_update_max_attempts,
            max_failed_instances=args.vm_osworld_max_failed_instances,
            linux_updater_command=args.vm_osworld_linux_updater_command,
            windows_updater_command=args.vm_osworld_windows_updater_command,
        )
        return bundle, config

    inherited = getattr(args, "retry_source_vm_osworld_settings", {}) or {}
    if inherited.get("bundle"):
        return (
            VmOsworldBundleSpec.from_dict(inherited["bundle"]),
            VmOsworldProvisionConfig.from_dict(inherited.get("provision_config")),
        )
    return None, None


def _has_task_source(args: argparse.Namespace) -> bool:
    return bool(args.task_file_path)


def _build_plan(tasks: list[TaskSpec], num_vms: int) -> dict:
    allocation = allocate_instances_by_snapshot(tasks, num_vms)
    counts = Counter(str(task.metadata["snapshot"]) for task in tasks)
    os_type_by_snapshot = _snapshot_os_types(tasks)
    instance_count = sum(allocation.values())

    return {
        "task_id_suffix": tasks[0].metadata.get("task_id_suffix", "") if tasks else "",
        "benchmark": tasks[0].metadata.get("benchmark", "engiworld") if tasks else "engiworld",
        "task_count": len(tasks),
        "snapshot_count": len(counts),
        "requested_instance_count": num_vms,
        "instance_count": instance_count,
        "snapshots": sorted(counts),
        "tasks_by_snapshot": dict(sorted(counts.items())),
        "snapshot_os_type": os_type_by_snapshot,
        "allocation": dict(sorted(allocation.items())),
        "sample_tasks": [_task_summary(task) for task in tasks[:5]],
        "queue": {
            "type": "redis_sorted_set",
            "key": "osworld:tasks:ready",
            "member": "{\"run_id\":\"...\",\"task_id\":\"...\"}",
            "payload_key": "osworld:{run_id}:tasks:payload",
        },
    }


def _agent_settings_from_args(args: argparse.Namespace) -> tuple[str, AgentConfig, dict[str, str]]:
    use_retry_source_agent = bool(
        not args.agent and getattr(args, "retry_source_agent_profile", None)
    )
    profile_name = args.agent or getattr(args, "retry_source_agent_profile", None)
    if not profile_name:
        raise ValueError(
            "--agent is required for a new plan/start so the model profile is explicit"
        )
    profile = get_agent_profile(profile_name)
    config = profile.agent_config
    if use_retry_source_agent:
        source_config = dict(getattr(args, "retry_source_agent_config", {}))
        legacy_limit = source_config.pop("top10_max_steps", None)
        if legacy_limit is not None and source_config.get("open_ended_max_steps") is None:
            source_config["open_ended_max_steps"] = legacy_limit
        source_overrides = {
            name: value
            for name, value in source_config.items()
            if name in AgentConfig.__dataclass_fields__ and value is not None
        }
        if source_overrides:
            config = replace(config, **source_overrides)
    overrides = {}
    for field_name in (
        "action_space",
        "observation_type",
        "eval_mode",
        "experiment_profile",
        "max_steps",
        "gui_max_steps",
        "cli_max_steps",
        "gui_multi_max_steps",
        "cli_multi_max_steps",
        "open_ended_max_steps",
        "history_turns",
        "bash_timeout",
        "record_video",
        "resume",
        "sleep_after_execution",
        "screen_width",
        "screen_height",
    ):
        value = getattr(args, field_name, None)
        if value is not None:
            overrides[field_name] = value
    legacy_cli_top10 = getattr(args, "legacy_cli_top10_max_steps", None)
    if overrides.get("open_ended_max_steps") is None and legacy_cli_top10 is not None:
        overrides["open_ended_max_steps"] = legacy_cli_top10
    if overrides:
        config = replace(config, **overrides)
    _validate_formal_step_limits(profile_name, config, args)
    if getattr(args, "max_steps", None) is not None:
        mode_step_fields = (
            "gui_max_steps",
            "cli_max_steps",
            "gui_multi_max_steps",
            "cli_multi_max_steps",
            "open_ended_max_steps",
        )
        implicit_mode_resets = {
            field_name: None
            for field_name in mode_step_fields
            if getattr(args, field_name, None) is None
        }
        config = replace(
            config,
            **implicit_mode_resets,
            open_max_steps=None,
            multi_max_steps=None,
        )

    env = dict(profile.env)
    if use_retry_source_agent:
        env.update(getattr(args, "retry_source_agent_env", {}))
    env.update(_parse_agent_env(args.agent_env))
    return profile.name, config, env


def _validate_formal_step_limits(
    profile_name: str,
    config: AgentConfig,
    args: argparse.Namespace,
) -> None:
    if profile_name not in ENGIWORLD_FORMAL_PROFILE_NAMES:
        return
    if getattr(args, "allow_nonstandard_step_limits", False):
        return
    if getattr(args, "max_steps", None) is not None:
        raise ValueError(
            "Formal EngiWorld profiles do not accept --max-steps because it collapses "
            "the GUI/CLI/Multi-software/Open-ended step budgets. Omit it and use the profile defaults."
        )

    mismatches = {
        field_name: (getattr(config, field_name), expected)
        for field_name, expected in ENGIWORLD_FORMAL_STEP_LIMITS.items()
        if getattr(config, field_name) != expected
    }
    for legacy_field in ("open_max_steps", "multi_max_steps"):
        value = getattr(config, legacy_field)
        if value is not None:
            mismatches[legacy_field] = (value, None)
    if mismatches:
        detail = ", ".join(
            f"{name}={actual!r} (expected {expected!r})"
            for name, (actual, expected) in sorted(mismatches.items())
        )
        raise ValueError(
            "Formal EngiWorld step limits do not match the locked protocol: " + detail
        )


def _resolved_agent_settings(args: argparse.Namespace) -> tuple[str, AgentConfig, dict[str, str]]:
    return args.resolved_agent_profile, args.resolved_agent_config, args.resolved_agent_env


def _parse_agent_env(items: list[str]) -> dict[str, str]:
    env = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"--agent-env must be formatted as KEY=VALUE, got {item!r}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"--agent-env key cannot be empty: {item!r}")
        if _looks_sensitive_env_name(key):
            raise ValueError(
                f"Refusing to store sensitive-looking --agent-env {key!r} in Redis. "
                "Inject secrets through worker environment variables instead."
            )
        env[key] = value
    return env


def _looks_sensitive_env_name(name: str) -> bool:
    normalized = name.upper()
    if normalized in {"ARENA_MODEL_MAX_TOKENS", "ARENA_MODEL_TOKEN_LIMIT_FIELD"}:
        return False
    return any(token in normalized for token in ("KEY", "SECRET", "TOKEN", "PASSWORD"))


def _agent_summary(profile: str, config: AgentConfig, env: dict[str, str]) -> dict:
    return {
        "profile": profile,
        "model": config.name,
        "agent_factory": config.agent_factory,
        "action_space": config.action_space,
        "observation_type": config.observation_type,
        "eval_mode": config.eval_mode,
        "experiment_profile": config.experiment_profile,
        "max_steps": config.max_steps,
        "gui_max_steps": config.gui_max_steps,
        "cli_max_steps": config.cli_max_steps,
        "gui_multi_max_steps": config.gui_multi_max_steps,
        "cli_multi_max_steps": config.cli_multi_max_steps,
        "open_ended_max_steps": config.open_ended_max_steps,
        "open_max_steps": config.open_max_steps,
        "multi_max_steps": config.multi_max_steps,
        "history_turns": config.history_turns,
        "bash_timeout": config.bash_timeout,
        "record_video": config.record_video,
        "resume": config.resume,
        "sleep_after_execution": config.sleep_after_execution,
        "screen_width": config.screen_width,
        "screen_height": config.screen_height,
        "headless": config.headless,
        "env": env,
    }


def _snapshot_os_types(tasks: list[TaskSpec]) -> dict[str, str]:
    os_types: dict[str, Counter[str]] = defaultdict(Counter)
    for task in tasks:
        snapshot = str(task.metadata["snapshot"])
        os_types[snapshot][str(task.metadata.get("os_type", "Ubuntu"))] += 1
    return {
        snapshot: counts.most_common(1)[0][0]
        for snapshot, counts in sorted(os_types.items())
    }


def _task_summary(task: TaskSpec) -> dict:
    return {
        "task_id": task.task_id,
        "base_task_id": task.metadata["base_task_id"],
        "source_task_id": task.metadata["source_task_id"],
        "domain": task.domain,
        "example_id": task.example_id,
        "snapshot": task.metadata["snapshot"],
        "os_type": task.metadata["os_type"],
        "task_path": task.metadata["task_path"],
    }


def _image_match_summary(snapshots: list[str]) -> dict[str, dict[str, str]]:
    launch_config = VolcengineLaunchConfig.from_env()
    ecs = VolcengineEcsClient(launch_config)
    image_by_snapshot = match_images_by_snapshot(
        snapshots,
        ecs.list_images(),
        image_visibility=launch_config.image_visibility,
    )
    return {
        snapshot: {
            "image_id": image.image_id,
            "image_name": image.image_name,
            "os_type": image.os_type,
            "status": image.status,
            "visibility": image.visibility,
        }
        for snapshot, image in sorted(image_by_snapshot.items())
    }


def _parse_v2_image_ids(values: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError("--v2-image-id must be formatted as OS_TYPE=IMAGE_ID")
        os_type, image_id = (part.strip() for part in raw.split("=", 1))
        normalized = "Windows" if os_type.lower().startswith("win") else "Ubuntu"
        if not image_id:
            raise ValueError("--v2-image-id image ID must not be empty")
        mapping[normalized] = image_id
    return mapping


def _compact_summary(summary: dict | None) -> dict | None:
    if not summary:
        return None
    return {
        "run_id": summary.get("run_id"),
        "status": summary.get("status"),
        "total_tasks": summary.get("total_tasks"),
        "status_counts": summary.get("status_counts"),
        "completed_tasks": summary.get("completed_tasks"),
        "failed_tasks": summary.get("failed_tasks"),
        "api_incomplete_tasks": summary.get("api_incomplete_tasks"),
        "infra_incomplete_tasks": summary.get("infra_incomplete_tasks"),
        "run_terminal": summary.get("run_terminal"),
    }


def _optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
