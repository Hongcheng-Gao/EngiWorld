#!/usr/bin/env python3
"""Build an OSWorld base image from Volcengine Ubuntu 24.04 x86_64.

The builder launches one disposable ECS from an official public Ubuntu image,
uses Cloud Assistant to import a private TOS OSWorld server bundle and install
the guest runtime, captures a private custom image, and then releases the ECS.
The build VM receives only a time-limited presigned TOS URL, never AK/SK.
"""

from __future__ import annotations

import argparse
import base64
from dataclasses import replace
import json
import shlex
import time
from pathlib import Path
from typing import Any

from engiworld.scheduler.storage import create_s3_client
from engiworld.scheduler.vm_osworld_update import (
    DEFAULT_VM_OSWORLD_BUCKET,
    DEFAULT_VM_OSWORLD_BUNDLE_PATH,
    VmOsworldBundleSpec,
    resolve_vm_osworld_bundle,
)
from engiworld.scheduler.volcengine_ecs import (
    CloudAssistantCommandResult,
    SharedImage,
    VolcengineEcsClient,
    VolcengineLaunchConfig,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BOOTSTRAP = REPO_ROOT / "deploy" / "image-builder" / "bootstrap_ubuntu_osworld.sh"
DEFAULT_UPDATER = REPO_ROOT / "deploy" / "vm-updater" / "osworld_updater.py"
MANAGED_BY = "arena-osworld"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-image-id",
        help=(
            "Official public Ubuntu 24.04 x86_64 image ID. When omitted, the "
            "newest matching public image is selected automatically."
        ),
    )
    parser.add_argument(
        "--image-name",
        help="Target custom image name; defaults to a timestamped name.",
    )
    parser.add_argument(
        "--project-name",
        help="Target project; defaults to VOLCENGINE_PROJECT_NAME or agent-eval.",
    )
    parser.add_argument(
        "--osworld-server-path",
        "--bundle-path",
        dest="bundle_path",
        default=DEFAULT_VM_OSWORLD_BUNDLE_PATH,
        help="TOS object key in the osworld-server bucket.",
    )
    parser.add_argument(
        "--bundle-bucket",
        default=DEFAULT_VM_OSWORLD_BUCKET,
        help="TOS bucket containing the server bundle and manifest.",
    )
    parser.add_argument("--manifest-path", help="Optional explicit manifest object key.")
    parser.add_argument(
        "--install-profile",
        choices=("minimal", "desktop"),
        default="desktop",
        help=(
            "minimal installs Xvfb and the HTTP server; desktop additionally "
            "installs XFCE and noVNC on port 8006."
        ),
    )
    parser.add_argument("--osworld-user", default="user")
    parser.add_argument(
        "--server-dir",
        help="Guest server directory; defaults to /home/<osworld-user>/server.",
    )
    parser.add_argument("--system-disk-size-gb", type=int, default=80)
    parser.add_argument("--bootstrap-script", type=Path, default=DEFAULT_BOOTSTRAP)
    parser.add_argument("--updater-source", type=Path, default=DEFAULT_UPDATER)
    parser.add_argument("--presign-expires-seconds", type=int, default=3600)
    parser.add_argument("--instance-ready-timeout-seconds", type=int, default=900)
    parser.add_argument("--cloud-assistant-initial-wait-seconds", type=int, default=120)
    parser.add_argument("--cloud-assistant-timeout-seconds", type=int, default=1800)
    parser.add_argument("--bootstrap-timeout-seconds", type=int, default=3600)
    parser.add_argument("--instance-stop-timeout-seconds", type=int, default=900)
    parser.add_argument("--image-timeout-seconds", type=int, default=3600)
    parser.add_argument("--force-stop", action="store_true")
    parser.add_argument("--cleanup-on-error", action="store_true")
    parser.add_argument("--keep-build-instance", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def _emit(event: str, **payload: Any) -> None:
    print(json.dumps({"event": event, **payload}, ensure_ascii=True), flush=True)


def public_ubuntu_config(
    config: VolcengineLaunchConfig,
    *,
    project_name: str,
    system_disk_size_gb: int,
) -> VolcengineLaunchConfig:
    changes: dict[str, Any] = {
        "project_name": project_name,
        "image_project_name": None,
        "image_visibility": "public",
        "system_disk_size_gb": system_disk_size_gb,
        "keep_image_credential": False,
    }
    if hasattr(config, "install_run_command_agent"):
        changes["install_run_command_agent"] = True
    return replace(config, **changes)


def _image_field(image: SharedImage, name: str) -> str:
    return str(getattr(image.raw, name, "") or "").strip()


def image_summary(image: SharedImage) -> dict[str, Any]:
    return {
        "image_id": image.image_id,
        "image_name": image.image_name,
        "os_type": image.os_type,
        "platform": _image_field(image, "platform"),
        "platform_version": _image_field(image, "platform_version"),
        "os_name": _image_field(image, "os_name"),
        "architecture": _image_field(image, "architecture"),
        "status": image.status,
        "is_lts": getattr(image.raw, "is_lts", None),
        "is_support_cloud_init": getattr(image.raw, "is_support_cloud_init", None),
        "is_install_run_command_agent": getattr(
            image.raw,
            "is_install_run_command_agent",
            None,
        ),
    }


def is_ubuntu_2404_x86_64(image: SharedImage) -> bool:
    summary = image_summary(image)
    platform_text = " ".join(
        str(summary[name] or "")
        for name in ("image_name", "platform", "platform_version", "os_name")
    ).lower()
    architecture = "".join(
        character
        for character in str(summary["architecture"] or "").lower()
        if character.isalnum()
    )
    status = str(summary["status"] or "").lower()
    return (
        "ubuntu" in platform_text
        and "24.04" in platform_text
        and architecture in {"x8664", "amd64"}
        and status in {"available", "ok"}
    )


def select_public_base_image(
    images: list[SharedImage],
    requested_image_id: str | None,
) -> SharedImage:
    if requested_image_id:
        matches = [image for image in images if image.image_id == requested_image_id]
        if not matches:
            raise ValueError(
                f"Public base image {requested_image_id!r} was not returned by DescribeImages"
            )
        image = matches[0]
        if not is_ubuntu_2404_x86_64(image):
            raise ValueError(
                "Base image is not an available Ubuntu 24.04 x86_64 public image: "
                + json.dumps(image_summary(image), ensure_ascii=True)
            )
        return image

    candidates = [image for image in images if is_ubuntu_2404_x86_64(image)]
    if not candidates:
        ubuntu_images = [
            image_summary(image)
            for image in images
            if "ubuntu"
            in " ".join(
                [
                    image.image_name,
                    _image_field(image, "platform"),
                    _image_field(image, "os_name"),
                ]
            ).lower()
        ]
        raise ValueError(
            "DescribeImages returned no available Ubuntu 24.04 x86_64 public image. "
            "Visible Ubuntu images: "
            + json.dumps(ubuntu_images[:20], ensure_ascii=True)
        )

    def sort_key(image: SharedImage) -> tuple[int, int, str, str]:
        return (
            int(bool(getattr(image.raw, "is_lts", False))),
            int(bool(getattr(image.raw, "is_support_cloud_init", False))),
            _image_field(image, "updated_at") or _image_field(image, "created_at"),
            image.image_id,
        )

    return max(candidates, key=sort_key)


def create_presigned_bundle_url(
    bundle: VmOsworldBundleSpec,
    *,
    expires_seconds: int,
) -> str:
    client, settings = create_s3_client(bundle.bucket)
    return str(
        client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.bucket, "Key": bundle.object_key},
            ExpiresIn=expires_seconds,
            HttpMethod="GET",
        )
    )


def build_cloud_assistant_bootstrap(
    *,
    bootstrap_path: Path,
    updater_path: Path,
    bundle: VmOsworldBundleSpec,
    bundle_url: str,
    install_profile: str,
    osworld_user: str,
    server_dir: str,
) -> str:
    if not bootstrap_path.is_file():
        raise FileNotFoundError(f"Ubuntu bootstrap script not found: {bootstrap_path}")
    if not updater_path.is_file():
        raise FileNotFoundError(f"OSWorld updater source not found: {updater_path}")
    if not server_dir.startswith("/"):
        raise ValueError(f"--server-dir must be an absolute Linux path: {server_dir!r}")
    if not osworld_user or any(character.isspace() for character in osworld_user):
        raise ValueError(f"Invalid --osworld-user: {osworld_user!r}")

    variables = {
        "OSWORLD_BUNDLE_URL": bundle_url,
        "OSWORLD_ARCHIVE_SHA256": bundle.archive_sha256,
        "OSWORLD_CONTENT_SHA256": bundle.content_sha256,
        "OSWORLD_BUNDLE_VERSION": bundle.version,
        "OSWORLD_BUNDLE_ROOT_DIR": bundle.root_dir,
        "OSWORLD_UPDATER_B64": base64.b64encode(updater_path.read_bytes()).decode("ascii"),
        "OSWORLD_INSTALL_PROFILE": install_profile,
        "OSWORLD_USER": osworld_user,
        "OSWORLD_SERVER_DIR": server_dir,
    }
    exports = "\n".join(
        f"export {name}={shlex.quote(value)}" for name, value in variables.items()
    )
    bootstrap = bootstrap_path.read_text(encoding="utf-8")
    if bootstrap.startswith("#!"):
        shebang, remainder = bootstrap.split("\n", 1)
        return shebang + "\n" + exports + "\n" + remainder
    return "#!/usr/bin/env bash\n" + exports + "\n" + bootstrap


def _normalized_cloud_assistant_status(value: str) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def ensure_cloud_assistant(
    ecs: VolcengineEcsClient,
    instance_id: str,
    *,
    initial_wait_seconds: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    try:
        ecs.wait_for_cloud_assistant(
            [instance_id],
            timeout_seconds=max(1, initial_wait_seconds),
        )
        return {"installed": False, "rebooted": False, "status": "online"}
    except TimeoutError:
        statuses = ecs.cloud_assistant_statuses([instance_id])
        current_status = statuses.get(instance_id, "missing")

    installed = False
    accepted: list[str] = []
    if _normalized_cloud_assistant_status(current_status) != "readyreboot":
        _emit(
            "ubuntu_osworld_cloud_assistant_installing",
            instance_id=instance_id,
            previous_status=current_status,
        )
        accepted = ecs.install_cloud_assistant([instance_id])
        installed = True

    deadline = time.monotonic() + timeout_seconds
    last_status = current_status
    rebooted = False
    while time.monotonic() < deadline:
        status = ecs.cloud_assistant_statuses([instance_id]).get(instance_id, "missing")
        normalized = _normalized_cloud_assistant_status(status)
        if status != last_status:
            _emit(
                "ubuntu_osworld_cloud_assistant_status",
                instance_id=instance_id,
                previous_status=last_status,
                status=status,
            )
            last_status = status
        if normalized in {"online", "running"}:
            return {
                "installed": installed,
                "rebooted": rebooted,
                "status": status,
                "accepted_instance_ids": accepted,
            }
        if normalized == "readyreboot" and not rebooted:
            _emit("ubuntu_osworld_cloud_assistant_rebooting", instance_id=instance_id)
            ecs.reboot_instances([instance_id])
            rebooted = True
        elif normalized in {"failed", "error", "installfailed"}:
            raise RuntimeError(
                f"Cloud Assistant installation failed on {instance_id}: {status}"
            )
        time.sleep(5)
    raise TimeoutError(
        "Timed out waiting for Cloud Assistant: "
        f"{instance_id}={last_status}, rebooted={rebooted}"
    )


def validate_bootstrap_result(result: CloudAssistantCommandResult) -> dict[str, Any]:
    if result.status.lower() not in {"success", "succeeded", "finished"} or result.exit_code not in {
        0,
        None,
    }:
        raise RuntimeError(
            f"Ubuntu OSWorld bootstrap failed on {result.instance_id}: "
            f"status={result.status}, exit_code={result.exit_code}, "
            f"error={result.error_code} {result.error_message}, output={result.output[-8000:]}"
        )
    for line in reversed(result.output.splitlines()):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("event") == "ubuntu_osworld_bootstrap_ready":
            return payload
    raise RuntimeError(
        "Ubuntu bootstrap completed without its ready report: " + result.output[-8000:]
    )


def run(args: argparse.Namespace) -> int:
    if args.keep_build_instance and args.cleanup_on_error:
        raise ValueError("--keep-build-instance and --cleanup-on-error cannot be combined")
    if args.system_disk_size_gb < 20:
        raise ValueError("--system-disk-size-gb must be at least 20")
    if args.presign_expires_seconds < 300:
        raise ValueError("--presign-expires-seconds must be at least 300")

    base_config = VolcengineLaunchConfig.from_env()
    project_name = args.project_name or base_config.project_name or "agent-eval"
    server_dir = args.server_dir or f"/home/{args.osworld_user}/server"
    config = public_ubuntu_config(
        base_config,
        project_name=project_name,
        system_disk_size_gb=args.system_disk_size_gb,
    )
    ecs = VolcengineEcsClient(config)
    bundle = resolve_vm_osworld_bundle(
        bucket=args.bundle_bucket,
        object_key=args.bundle_path,
        manifest_key=args.manifest_path,
    )
    base_image = select_public_base_image(ecs.list_shared_images(), args.base_image_id)
    build_id = time.strftime("ubuntu-osworld-%Y%m%d-%H%M%S")
    image_name = args.image_name or build_id
    if len(image_name) > 128:
        raise ValueError("--image-name must be at most 128 characters")

    plan = {
        "project_name": project_name,
        "base_image": image_summary(base_image),
        "target_image_name": image_name,
        "system_disk_size_gb": args.system_disk_size_gb,
        "install_profile": args.install_profile,
        "server_dir": server_dir,
        "bundle": {
            "bucket": bundle.bucket,
            "object_key": bundle.object_key,
            "manifest_key": bundle.manifest_key,
            "version": bundle.version,
            "archive_sha256": bundle.archive_sha256,
            "content_sha256": bundle.content_sha256,
        },
        "allocate_public_ip": config.allocate_public_ip,
        "dry_run": args.dry_run,
    }
    _emit("ubuntu_osworld_image_build_plan", **plan)
    if args.dry_run:
        return 0
    if not config.password:
        raise EnvironmentError(
            "VOLCENGINE_DEFAULT_PASSWORD must be set when launching an official public image. "
            "It is sent to RunInstances but is never written to the custom image build log."
        )

    bundle_url = create_presigned_bundle_url(
        bundle,
        expires_seconds=args.presign_expires_seconds,
    )
    bootstrap = build_cloud_assistant_bootstrap(
        bootstrap_path=args.bootstrap_script,
        updater_path=args.updater_source,
        bundle=bundle,
        bundle_url=bundle_url,
        install_profile=args.install_profile,
        osworld_user=args.osworld_user,
        server_dir=server_dir,
    )

    instance_id: str | None = None
    image_id: str | None = None
    success = False
    try:
        instances = ecs.run_instances(
            base_image,
            count=1,
            run_id=build_id,
            snapshot="ubuntu-24-04-osworld-base-build",
            os_type="Ubuntu",
            wait_timeout_seconds=args.instance_ready_timeout_seconds,
        )
        if len(instances) != 1:
            raise RuntimeError(f"Expected one build instance, got {len(instances)}")
        instance_id = instances[0].instance_id
        _emit(
            "ubuntu_osworld_build_instance_ready",
            instance_id=instance_id,
            private_ip=instances[0].private_ip,
        )

        assistant = ensure_cloud_assistant(
            ecs,
            instance_id,
            initial_wait_seconds=args.cloud_assistant_initial_wait_seconds,
            timeout_seconds=args.cloud_assistant_timeout_seconds,
        )
        _emit(
            "ubuntu_osworld_cloud_assistant_ready",
            instance_id=instance_id,
            **assistant,
        )
        invocation_id, results = ecs.run_cloud_assistant_command(
            [instance_id],
            script=bootstrap,
            command_type="Shell",
            invocation_name=f"arena-ubuntu-osworld-{build_id}",
            timeout_seconds=args.bootstrap_timeout_seconds,
        )
        if len(results) != 1:
            raise RuntimeError(f"Expected one Cloud Assistant result, got {len(results)}")
        bootstrap_report = validate_bootstrap_result(results[0])
        if bootstrap_report.get("content_sha256") != bundle.content_sha256:
            raise RuntimeError(
                "Bootstrap content SHA256 mismatch: "
                f"expected={bundle.content_sha256}, report={bootstrap_report}"
            )
        _emit(
            "ubuntu_osworld_guest_ready",
            instance_id=instance_id,
            invocation_id=invocation_id,
            bootstrap=bootstrap_report,
        )

        ecs.stop_instances([instance_id], force=args.force_stop)
        ecs.wait_for_instance_status(
            [instance_id],
            expected_status="STOPPED",
            timeout_seconds=args.instance_stop_timeout_seconds,
        )
        image_id = ecs.create_image_from_instance(
            instance_id,
            image_name=image_name,
            description="Arena OSWorld Ubuntu 24.04 x86_64 base image",
            tags={
                "managed_by": MANAGED_BY,
                "source": "ubuntu-24.04-public-image",
                "benchmark": "osworld",
                "architecture": "x86_64",
                "base_image_id": base_image.image_id,
                "server_version": bundle.version[:256],
                "server_sha256": bundle.content_sha256,
                "install_profile": args.install_profile,
            },
        )
        image = ecs.wait_for_image_available(
            image_id,
            timeout_seconds=args.image_timeout_seconds,
        )
        success = True
        result = {
            "image_id": image.image_id,
            "image_name": image.image_name,
            "build_instance_id": instance_id,
            "project_name": project_name,
            "base_image": image_summary(base_image),
            "bundle": plan["bundle"],
            "bootstrap": bootstrap_report,
        }
        _emit("ubuntu_osworld_image_ready", **result)
        return 0
    finally:
        should_delete = bool(instance_id) and (
            (success and not args.keep_build_instance)
            or (not success and args.cleanup_on_error)
        )
        if should_delete:
            ecs.terminate_instances([instance_id])
            _emit("ubuntu_osworld_build_instance_deleted", instance_id=instance_id)
        elif instance_id and not success:
            _emit(
                "ubuntu_osworld_build_instance_retained",
                instance_id=instance_id,
                image_id=image_id,
                reason="build_failed",
            )


def main() -> int:
    try:
        return run(parse_args())
    except KeyboardInterrupt:
        _emit("ubuntu_osworld_image_build_aborted", error="KeyboardInterrupt")
        return 130
    except Exception as exc:
        _emit(
            "ubuntu_osworld_image_build_aborted",
            error=f"{type(exc).__name__}: {exc}",
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
