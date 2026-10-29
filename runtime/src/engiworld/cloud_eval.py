"""Run one EngiWorld task on a fresh Aliyun ECS instance."""
from __future__ import annotations

import argparse
import json
import math
import os
import uuid
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path

from engiworld.active_time import ActiveTimeBudgetExceeded, budget_outcome
from engiworld.agents.profiles import get_agent_profile
from engiworld.local_eval import RUNTIME_ROOT, preflight, task_deadline
from engiworld.prepare_tasks import TASK_ROOT
from engiworld.scheduler.runner import (
    _agent_config_for_instance,
    _agent_config_for_task,
    ensure_engine_importable,
    load_task_config,
    run_single_task,
)
from engiworld.scheduler.schemas import EvalConfig

CATALOG = RUNTIME_ROOT / "deploy" / "aliyun" / "images.json"


def find_cloud_image(image_name: str, region: str) -> str:
    from alibabacloud_ecs20140526 import models
    from alibabacloud_ecs20140526.client import Client
    from alibabacloud_tea_openapi.models import Config
    client = Client(Config(access_key_id=os.environ["ALIYUN_ACCESS_KEY_ID"],
                           access_key_secret=os.environ["ALIYUN_ACCESS_KEY_SECRET"],
                           region_id=region))
    matches = set()
    for owner in ("others", "self"):
        page = 1
        while True:
            response = client.describe_images(models.DescribeImagesRequest(
                region_id=region, image_name=image_name, image_owner_alias=owner,
                status="Available", page_number=page, page_size=100))
            items = response.body.images.image or []
            matches.update(image.image_id for image in items
                           if image.image_name == image_name and image.status == "Available")
            if page * 100 >= (response.body.total_count or len(items)):
                break
            page += 1
    if len(matches) != 1:
        raise ValueError(f"Expected one accessible image named {image_name} in {region}; found {len(matches)}. "
                         "Obtain image sharing access or set --image-id")
    return matches.pop()


def resolve_image(snapshot: str, image_id: str | None, catalog: Path, region: str) -> str:
    if image_id:
        return image_id
    data = json.loads(catalog.read_text())
    entry = data.get("regions", {}).get(region, {}).get(snapshot)
    if entry and entry.get("image_name") and not entry.get("image_id"):
        return find_cloud_image(entry["image_name"], region)
    if not entry or not entry.get("image_id"):
        raise ValueError(f"No image is configured for {snapshot} in {region}; set --image-id")
    return entry["image_id"]


def check_cloud_config() -> None:
    required = ("ALIYUN_ACCESS_KEY_ID", "ALIYUN_ACCESS_KEY_SECRET", "ALIYUN_REGION",
                "ALIYUN_VSWITCH_ID", "ALIYUN_SECURITY_GROUP_ID", "ALIYUN_INSTANCE_TYPE")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise ValueError("Set the cloud configuration: " + ", ".join(missing))
    private = os.getenv("ALIYUN_USE_PRIVATE_IP", "1").lower() in {"1", "true", "yes", "on"}
    if not private and int(os.getenv("ALIYUN_PUBLIC_BANDWIDTH", "0")) <= 0:
        raise ValueError("Public IP access requires ALIYUN_PUBLIC_BANDWIDTH > 0")


def main(argv: list[str] | None = None) -> int:
    from engiworld.cloud_journal import cleanup_journals
    from engiworld.cloud_models import add_model_arguments, model_record, resolve_model
    from engiworld.scheduler.cloud_factory import make_cloud_client
    from engiworld.scheduler.error_policy import outcome_fields
    from engiworld.scheduler.volcengine_ecs import InstanceLaunchGroup, match_images_by_snapshot

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=["aliyun", "volcengine"], default="aliyun")
    parser.add_argument("--task", required=True)
    parser.add_argument("--task-root", type=Path, default=TASK_ROOT)
    parser.add_argument("--image-id")
    parser.add_argument("--image-catalog", type=Path, default=CATALOG)
    add_model_arguments(parser)
    parser.add_argument("--result-dir", type=Path, default=Path("results"))
    parser.add_argument("--task-timeout", type=float, default=18000)
    parser.add_argument("--client-password", default=os.getenv("ENGIWORLD_CLIENT_PASSWORD", ""))
    parser.add_argument("--record-video", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--retain-api-incomplete-instances", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args(argv)
    if not math.isfinite(args.task_timeout) or args.task_timeout <= 0:
        parser.error("--task-timeout must be finite and positive")
    try:
        task = preflight(args.task_root.resolve(), args.task)
        if not args.smoke_test and not args.check and not args.agent:
            raise ValueError("Select --agent; custom models also need --model, --reasoning-effort and --max-tokens")
        if args.agent:
            profile, agent_env = resolve_model(args.agent, model=args.model,
                reasoning_effort=args.reasoning_effort, max_tokens=args.max_tokens,
                token_limit_field=args.token_limit_field)
        else:
            profile, agent_env = get_agent_profile("openai-compatible"), {}
        if not args.smoke_test and not args.check and not os.getenv("OPENAI_API_KEY"):
            raise ValueError("Set OPENAI_API_KEY")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    # Install the resolved protocol, including defaults; ambient model settings
    # must not silently alter a named preset. Endpoint credentials stay private.
    previous = {key: os.environ.get(key) for key in agent_env}
    previous["ARENA_RUN_ID"] = os.environ.get("ARENA_RUN_ID")
    os.environ.update(agent_env)
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
    os.environ["ARENA_RUN_ID"] = run_id
    output = args.result_dir.resolve() / run_id
    journal_dir = output / "instances"
    summary = {"task_id": task.task_id, "provider": args.provider, "run_id": run_id,
               "score": None, "result_dir": str(output), "status": "initializing"}
    if args.agent:
        summary["model_config"] = model_record(args.agent, agent_env)
    ecs = None
    budget = None
    retained = False
    output.mkdir(parents=True)
    try:
        ecs = make_cloud_client(args.provider, journal_dir=journal_dir)
        snapshot = task.metadata["snapshot"]
        if args.provider == "aliyun":
            check_cloud_config()
            image_id = resolve_image(snapshot, args.image_id, args.image_catalog, os.environ["ALIYUN_REGION"])
            image = ecs.get_image(image_id, snapshot)
            # Registered API waits are excluded from task time. Allow their full
            # configured window before the provider's wall-clock safety release.
            wait = float(agent_env.get("ARENA_OPENAI_COMPAT_HOTSWAP_WAIT_SECONDS", "0"))
            ecs.config.ttl_minutes = max(120, math.ceil((args.task_timeout + wait) / 60) + 60)
        else:
            images = ecs.list_images()
            if args.image_id:
                matches = [i for i in images if i.image_id == args.image_id]
                if len(matches) != 1:
                    raise ValueError("The selected Volcengine image is unavailable")
                image = matches[0]
            else:
                image = match_images_by_snapshot([snapshot], images,
                    image_visibility=ecs.config.image_visibility)[snapshot]
        summary["image_id"] = image.image_id
        if args.check:
            summary.update(status="checked", resources="ok")
        else:
            instance = ecs.run_instance_groups([InstanceLaunchGroup(image, 1, snapshot,
                task.metadata["os_type"])], run_id=run_id)[0]
            summary["instance_id"] = instance.instance_id
            config = EvalConfig(run_id=run_id, task_root=str(args.task_root.resolve()),
                engine_path=str(RUNTIME_ROOT / "engine"), result_dir=str(args.result_dir.resolve()),
                s3_upload=False, keep_local_results=True)
            agent = _agent_config_for_task(_agent_config_for_instance(replace(profile.agent_config,
                client_password=args.client_password, record_video=args.record_video), instance, task), task)
            ensure_engine_importable(RUNTIME_ROOT / "engine")
            with task_deadline(args.task_timeout) as budget:
                if args.smoke_test:
                    from desktop_env.desktop_env import DesktopEnv
                    env = DesktopEnv(provider_name=args.provider, path_to_vm=instance.instance_id,
                        os_type=instance.os_type, action_space=agent.action_space,
                        require_a11y_tree=False, headless=True, manage_lifecycle=False,
                        client_password=args.client_password, cache_dir=str(output / "cache"))
                    observation = env.reset(task_config=load_task_config(config, task))
                    if not observation.get("screenshot"):
                        raise RuntimeError("Environment returned no screenshot")
                    (output / "smoke.png").write_bytes(observation["screenshot"])
                    summary.update(status="environment_ready")
                else:
                    summary.update(asdict(run_single_task(task, instance, config, agent,
                        provider_name=args.provider, path_to_vm=instance.instance_id,
                        manage_lifecycle=False)))
                    summary.update(outcome_fields(summary.get("error"), summary.get("error_category"),
                                                  summary.get("score")))
    except ActiveTimeBudgetExceeded as exc:
        if args.smoke_test:
            summary.update(status="infra_incomplete", score=None, error=str(exc), error_category="infra")
        else:
            summary.update(status="completed", **budget_outcome(), error=None)
            (output / "result.txt").write_text("0.0", encoding="utf-8")
            (output / "evaluation.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    except Exception as exc:
        summary.update(status="infra_incomplete", score=None, error=str(exc), error_category="infra")
    finally:
        # Task timing is stopped before cloud deletion starts. One owner releases
        # instances and waits for confirmed absence, even after allocation fails.
        if budget is not None:
            summary.update(budget.metrics())
        summary["active_time_limit_seconds"] = args.task_timeout
        retained = summary.get("status") == "api_incomplete" and args.retain_api_incomplete_instances
        if retained:
            summary.update(instance_retained=True, instance_released=False)
        elif ecs is not None:
            failures = cleanup_journals(ecs, journal_dir)
            summary["instance_released"] = not failures
            if failures:
                summary.update(cleanup_error="Cloud release is unconfirmed", unreleased_requests=failures)
        summary["instance_records"] = [str(p) for p in journal_dir.rglob("*.json")]
        (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    print(json.dumps(summary, indent=2))
    print(f"Saved: {output / 'summary.json'}")
    return int(bool(summary.get("error") or summary.get("cleanup_error")))


if __name__ == "__main__":
    raise SystemExit(main())
