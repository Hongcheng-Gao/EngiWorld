"""Run one EngiWorld task on a fresh Aliyun ECS instance."""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from datetime import datetime
import json
import logging
import math
import os
from pathlib import Path
import uuid

from engiworld.active_time import ActiveTimeBudgetExceeded, budget_outcome
from engiworld.agents.profiles import get_agent_profile
from engiworld.local_eval import RUNTIME_ROOT, preflight, task_deadline
from engiworld.prepare_tasks import TASK_ROOT
from engiworld.scheduler.runner import (
    _agent_config_for_instance, _agent_config_for_task, ensure_engine_importable,
    load_task_config, run_single_task,
)
from engiworld.scheduler.schemas import EvalConfig, InstanceRecord

CATALOG = RUNTIME_ROOT / "deploy" / "aliyun" / "images.json"


def find_cloud_image(image_name: str, region: str) -> str:
    from alibabacloud_ecs20140526.client import Client
    from alibabacloud_ecs20140526 import models
    from alibabacloud_tea_openapi.models import Config
    client = Client(Config(access_key_id=os.environ["ALIYUN_ACCESS_KEY_ID"],
                           access_key_secret=os.environ["ALIYUN_ACCESS_KEY_SECRET"],
                           region_id=region))
    matches = set()
    for owner in ("others", "self"):
        response = client.describe_images(models.DescribeImagesRequest(
            region_id=region, image_name=image_name, image_owner_alias=owner, status="Available"))
        matches.update(image.image_id for image in response.body.images.image
                       if image.image_name == image_name and image.status == "Available")
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True)
    parser.add_argument("--task-root", type=Path, default=TASK_ROOT)
    parser.add_argument("--image-id", default=os.getenv("ALIYUN_IMAGE_ID"))
    parser.add_argument("--image-catalog", type=Path, default=CATALOG)
    parser.add_argument("--model", default=os.getenv("ARENA_MODEL_NAME"))
    parser.add_argument("--result-dir", type=Path, default=Path("results"))
    parser.add_argument("--task-timeout", type=float, default=18000)
    parser.add_argument("--client-password", default=os.getenv("ENGIWORLD_CLIENT_PASSWORD", ""))
    parser.add_argument("--record-video", action="store_true")
    parser.add_argument("--check", action="store_true", help="Check local resources and configuration")
    parser.add_argument("--smoke-test", action="store_true", help="Reset the environment without a model")
    args = parser.parse_args(argv)
    if args.task_timeout <= 0:
        parser.error("--task-timeout must be positive")
    try:
        task = preflight(args.task_root.resolve(), args.task)
        check_cloud_config()
        image_id = resolve_image(task.metadata["snapshot"], args.image_id,
                                 args.image_catalog, os.environ["ALIYUN_REGION"])
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if args.check:
        print(json.dumps({"task": task.task_id, "snapshot": task.metadata["snapshot"],
                          "image_id": image_id, "region": os.environ["ALIYUN_REGION"],
                          "resources": "ok"}, indent=2))
        return 0
    if not args.smoke_test and (not args.model or not os.getenv("OPENAI_API_KEY")):
        parser.error("Set --model and OPENAI_API_KEY")
    os.environ["ALIYUN_IMAGE_ID"] = image_id
    # The cloud deadline covers boot, evaluation and a one-hour shutdown margin.
    os.environ["ENABLE_TTL"] = "true"
    os.environ["DEFAULT_TTL_MINUTES"] = str(max(120, math.ceil(args.task_timeout / 60) + 60))
    profile = get_agent_profile("openai-compatible")
    for key, value in profile.env.items():
        if "HOTSWAP" not in key and "RUNTIME_CONFIG" not in key:
            os.environ.setdefault(key, value)
    os.environ["ARENA_OPENAI_COMPAT_HOTSWAP_ENABLED"] = "false"
    if args.model:
        os.environ["ARENA_MODEL_NAME"] = args.model
    ensure_engine_importable(RUNTIME_ROOT / "engine")
    from desktop_env.providers.aliyun.manager import _allocate_vm
    from desktop_env.providers.aliyun.provider import AliyunProvider
    from alibabacloud_ecs20140526 import models as ecs_models

    config = EvalConfig(run_id=datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8],
                        task_root=str(args.task_root.resolve()), engine_path=str(RUNTIME_ROOT / "engine"),
                        result_dir=str(args.result_dir.resolve()), s3_upload=False, keep_local_results=True)
    output = Path(config.result_dir) / config.run_id
    output.mkdir(parents=True)
    logging.basicConfig(level=logging.INFO)
    provider = AliyunProvider()
    instance_id = None
    summary = {"task_id": task.task_id, "image_id": image_id, "provider": "aliyun"}
    budget = None
    try:
        instance_id = _allocate_vm()
        (output / "instance.json").write_text(json.dumps({"instance_id": instance_id,
                "image_id": image_id, "region": os.environ["ALIYUN_REGION"]}, indent=2))
        instance = InstanceRecord(instance_id, "", os_type=task.metadata["os_type"])
        agent = _agent_config_for_task(_agent_config_for_instance(replace(
            profile.agent_config, client_password=args.client_password,
            record_video=args.record_video), instance, task), task)
        with task_deadline(args.task_timeout) as budget:
            if args.smoke_test:
                from desktop_env.desktop_env import DesktopEnv
                env = None
                try:
                    env = DesktopEnv(provider_name="aliyun", path_to_vm=instance_id,
                                     os_type=instance.os_type, action_space=agent.action_space,
                                     require_a11y_tree=False, headless=True,
                                     client_password=args.client_password,
                                     cache_dir=str(output / "cache"))
                    observation = env.reset(task_config=load_task_config(config, task))
                    if not observation.get("screenshot"):
                        raise RuntimeError("Environment returned no screenshot")
                    (output / "smoke.png").write_bytes(observation["screenshot"])
                    summary.update(status="environment_ready", screenshot=str(output / "smoke.png"))
                finally:
                    if env is not None:
                        env.close()
            else:
                summary.update(asdict(run_single_task(task, instance, config, agent,
                                      provider_name="aliyun", path_to_vm=instance_id)))
    except ActiveTimeBudgetExceeded as exc:
        if args.smoke_test:
            summary.update(error=str(exc), error_category="environment_timeout")
        else:
            summary.update(status="completed", **budget_outcome(), error=None)
            (output / "result.txt").write_text("0.0")
            (output / "evaluation.json").write_text(json.dumps(summary, indent=2))
    except Exception as exc:
        summary.update(error=str(exc), error_category="environment_error")
    finally:
        if instance_id:
            try:
                request = ecs_models.DescribeInstancesRequest(
                    region_id=provider.region, instance_ids=json.dumps([instance_id]))
                if provider.client.describe_instances(request).body.instances.instance:
                    provider.stop_emulator(instance_id)
                summary["instance_released"] = True
            except Exception as exc:
                summary["instance_released"] = False
                summary["cleanup_error"] = str(exc)
        if budget is not None:
            summary.update(budget.metrics())
        (output / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print(f"Saved: {output / 'summary.json'}")
    return int(bool(summary.get("error") or summary.get("cleanup_error")))


if __name__ == "__main__":
    raise SystemExit(main())
