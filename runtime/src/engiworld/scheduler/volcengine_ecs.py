"""Volcengine ECS adapter used by the master process."""

from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from engiworld.scheduler.schemas import InstanceRecord


@dataclass(frozen=True)
class EcsImage:
    image_id: str
    image_name: str
    os_type: str
    status: str
    visibility: str
    raw: Any
    disk_size_gb: int | None = None


# Compatibility name used by image-copy and image-updater tooling.
SharedImage = EcsImage


@dataclass(frozen=True)
class EcsInstance:
    instance_id: str
    instance_name: str
    private_ip: str
    image_id: str
    os_type: str
    status: str
    tags: dict[str, str]
    raw: Any


@dataclass(frozen=True)
class InstanceLaunchGroup:
    image: EcsImage
    count: int
    snapshot: str
    os_type: str
    system_disk_size_gb: int | None = None


@dataclass(frozen=True)
class _PendingInstanceGroup:
    instance_ids: tuple[str, ...]
    image: EcsImage
    snapshot: str
    os_type: str
    system_disk_size_gb: int


@dataclass(frozen=True)
class CloudAssistantCommandResult:
    instance_id: str
    status: str
    exit_code: int | None
    output: str
    error_code: str
    error_message: str


@dataclass(frozen=True)
class VolcengineLaunchConfig:
    region: str
    access_key_id: str
    secret_access_key: str
    subnet_id: str
    security_group_id: str
    instance_type: str
    zone_id: str
    password: str | None = None
    project_name: str | None = None
    image_project_name: str | None = None
    system_disk_size_gb: int = 50
    system_disk_size_gb_by_image: dict[str, int] = field(default_factory=dict)
    system_disk_type: str = "ESSD_PL0"
    eip_bandwidth_mbps: int = 5
    allocate_public_ip: bool = True
    image_visibility: str = "private"
    keep_image_credential: bool = True
    install_run_command_agent: bool = False
    run_instances_max_count: int = 100
    describe_instances_batch_size: int = 100
    api_max_retries: int = 5
    api_retry_base_seconds: float = 2.0
    api_retry_max_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "VolcengineLaunchConfig":
        required = {
            "VOLCENGINE_ACCESS_KEY_ID": os.getenv("VOLCENGINE_ACCESS_KEY_ID"),
            "VOLCENGINE_SECRET_ACCESS_KEY": os.getenv("VOLCENGINE_SECRET_ACCESS_KEY"),
            "VOLCENGINE_REGION": os.getenv("VOLCENGINE_REGION"),
            "VOLCENGINE_SUBNET_ID": os.getenv("VOLCENGINE_SUBNET_ID"),
            "VOLCENGINE_SECURITY_GROUP_ID": os.getenv("VOLCENGINE_SECURITY_GROUP_ID"),
            "VOLCENGINE_INSTANCE_TYPE": os.getenv("VOLCENGINE_INSTANCE_TYPE"),
            "VOLCENGINE_ZONE_ID": os.getenv("VOLCENGINE_ZONE_ID"),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise EnvironmentError("Missing Volcengine configuration: " + ", ".join(missing))

        return cls(
            region=required["VOLCENGINE_REGION"] or "",
            access_key_id=required["VOLCENGINE_ACCESS_KEY_ID"] or "",
            secret_access_key=required["VOLCENGINE_SECRET_ACCESS_KEY"] or "",
            subnet_id=required["VOLCENGINE_SUBNET_ID"] or "",
            security_group_id=required["VOLCENGINE_SECURITY_GROUP_ID"] or "",
            instance_type=required["VOLCENGINE_INSTANCE_TYPE"] or "",
            zone_id=required["VOLCENGINE_ZONE_ID"] or "",
            password=os.getenv("VOLCENGINE_DEFAULT_PASSWORD") or None,
            project_name=os.getenv("VOLCENGINE_PROJECT_NAME", "agent-eval") or None,
            image_project_name=os.getenv("VOLCENGINE_IMAGE_PROJECT_NAME") or None,
            system_disk_size_gb=int(os.getenv("VOLCENGINE_SYSTEM_DISK_SIZE_GB", "50")),
            system_disk_size_gb_by_image=_parse_disk_size_map(
                os.getenv("VOLCENGINE_SYSTEM_DISK_SIZE_GB_BY_IMAGE", "")
            ),
            system_disk_type=os.getenv("VOLCENGINE_SYSTEM_DISK_TYPE", "ESSD_PL0"),
            eip_bandwidth_mbps=int(os.getenv("VOLCENGINE_EIP_BANDWIDTH_MBPS", "5")),
            allocate_public_ip=os.getenv("VOLCENGINE_ALLOCATE_PUBLIC_IP", "true").lower()
            not in {"0", "false", "no"},
            image_visibility=_parse_image_visibility(
                os.getenv("VOLCENGINE_IMAGE_VISIBILITY", "private")
            ),
            keep_image_credential=os.getenv("VOLCENGINE_KEEP_IMAGE_CREDENTIAL", "true").lower()
            not in {"0", "false", "no"},
            install_run_command_agent=os.getenv(
                "VOLCENGINE_INSTALL_RUN_COMMAND_AGENT",
                "false",
            ).lower()
            not in {"0", "false", "no"},
            run_instances_max_count=int(os.getenv("VOLCENGINE_RUN_INSTANCES_MAX_COUNT", "100")),
            describe_instances_batch_size=int(
                os.getenv("VOLCENGINE_DESCRIBE_INSTANCES_BATCH_SIZE", "100")
            ),
            api_max_retries=int(os.getenv("VOLCENGINE_API_MAX_RETRIES", "5")),
            api_retry_base_seconds=float(os.getenv("VOLCENGINE_API_RETRY_BASE_SECONDS", "2")),
            api_retry_max_seconds=float(os.getenv("VOLCENGINE_API_RETRY_MAX_SECONDS", "30")),
        )


class VolcengineEcsClient:
    def __init__(self, config: VolcengineLaunchConfig):
        self.config = config
        self._api = self._create_api()

    def _create_api(self):
        try:
            import volcenginesdkcore
            from volcenginesdkecs.api import ECSApi
        except ImportError as exc:
            raise ImportError(
                "Volcengine ECS SDK is required. Install volcengine-python-sdk[ark]."
            ) from exc

        configuration = volcenginesdkcore.Configuration()
        configuration.region = self.config.region
        configuration.ak = self.config.access_key_id
        configuration.sk = self.config.secret_access_key
        configuration.client_side_validation = True
        volcenginesdkcore.Configuration.set_default(configuration)
        return ECSApi()

    def list_images(self) -> list[EcsImage]:
        import volcenginesdkecs.models as ecs_models

        images: list[EcsImage] = []
        next_token = None
        while True:
            request = ecs_models.DescribeImagesRequest(
                visibility=self.config.image_visibility,
                max_results=100,
                next_token=next_token,
            )
            if self.config.image_project_name:
                request.project_name = self.config.image_project_name
            response = self._call_with_rate_limit_retry(
                "DescribeImages",
                lambda request=request: self._api.describe_images(request),
            )
            for image in response.images or []:
                images.append(
                    EcsImage(
                        image_id=image.image_id,
                        image_name=image.image_name,
                        os_type=image.os_type or "",
                        status=image.status or "",
                        visibility=image.visibility or "",
                        raw=image,
                        disk_size_gb=_image_system_disk_size_gb(image),
                    )
                )
            next_token = response.next_token
            if not next_token:
                break
        return images

    def list_shared_images(self) -> list[EcsImage]:
        """Compatibility wrapper; visibility is controlled by launch config."""
        return self.list_images()

    def list_instances(
        self,
        *,
        tags: dict[str, str] | None = None,
        project_name: str | None = None,
    ) -> list[EcsInstance]:
        """List ECS instances, optionally filtered by exact tag values."""
        import volcenginesdkecs.models as ecs_models

        expected_tags = {str(key): str(value) for key, value in (tags or {}).items()}
        tag_filters = [
            ecs_models.TagFilterForDescribeInstancesInput(key=key, values=[value])
            for key, value in sorted(expected_tags.items())
        ]
        instances: list[EcsInstance] = []
        next_token = None
        while True:
            request = ecs_models.DescribeInstancesRequest(
                max_results=100,
                next_token=next_token,
                project_name=project_name or self.config.project_name,
                tag_filters=tag_filters or None,
            )
            response = self._call_with_rate_limit_retry(
                "DescribeInstances",
                lambda request=request: self._api.describe_instances(request),
            )
            for instance in response.instances or []:
                instance_tags = _sdk_tags(instance)
                # Keep an exact-value check client-side in case provider-side
                # tag-filter semantics change.
                if any(instance_tags.get(key) != value for key, value in expected_tags.items()):
                    continue
                instances.append(
                    EcsInstance(
                        instance_id=str(instance.instance_id or ""),
                        instance_name=str(instance.instance_name or ""),
                        private_ip=_instance_private_ip(instance),
                        image_id=str(instance.image_id or ""),
                        os_type=str(instance.os_type or ""),
                        status=str(instance.status or ""),
                        tags=instance_tags,
                        raw=instance,
                    )
                )
            next_token = response.next_token
            if not next_token:
                break
        return instances

    def run_instances(
        self,
        image: EcsImage,
        count: int,
        run_id: str,
        snapshot: str,
        os_type: str,
        wait_timeout_seconds: int = 900,
    ) -> list[InstanceRecord]:
        return self.run_instance_groups(
            [
                InstanceLaunchGroup(
                    image=image,
                    count=count,
                    snapshot=snapshot,
                    os_type=os_type,
                )
            ],
            run_id=run_id,
            wait_timeout_seconds=wait_timeout_seconds,
        )

    def run_instance_groups(
        self,
        groups: list[InstanceLaunchGroup],
        run_id: str,
        wait_timeout_seconds: int = 900,
    ) -> list[InstanceRecord]:
        pending_groups: list[_PendingInstanceGroup] = []
        try:
            pending_groups = self.submit_instance_groups(groups, run_id=run_id)
            return self.wait_for_instance_groups(
                pending_groups,
                timeout_seconds=wait_timeout_seconds,
            )
        except (Exception, KeyboardInterrupt):
            instance_ids = _pending_instance_ids(pending_groups)
            if instance_ids:
                try:
                    self.terminate_instances(instance_ids)
                except Exception:
                    # Preserve the launch/wait failure. The caller still receives all
                    # submitted IDs in the original error for manual cleanup.
                    pass
            raise

    def submit_instance_groups(
        self,
        groups: list[InstanceLaunchGroup],
        run_id: str,
    ) -> list[_PendingInstanceGroup]:
        pending_groups: list[_PendingInstanceGroup] = []
        launched_instance_ids: list[str] = []
        try:
            for group in groups:
                if group.count <= 0:
                    continue
                system_disk_size_gb = self._resolve_system_disk_size_gb(
                    image=group.image,
                    snapshot=group.snapshot,
                    override=group.system_disk_size_gb,
                )
                for count in _split_count(group.count, self.config.run_instances_max_count):
                    instance_ids = self._run_instances_once(
                        image=group.image,
                        count=count,
                        run_id=run_id,
                        snapshot=group.snapshot,
                        system_disk_size_gb=system_disk_size_gb,
                    )
                    launched_instance_ids.extend(instance_ids)
                    if instance_ids:
                        pending_groups.append(
                            _PendingInstanceGroup(
                                instance_ids=tuple(instance_ids),
                                image=group.image,
                                snapshot=group.snapshot,
                                os_type=group.os_type,
                                system_disk_size_gb=system_disk_size_gb,
                            )
                        )
            return pending_groups
        except KeyboardInterrupt:
            if launched_instance_ids:
                self.terminate_instances(launched_instance_ids)
            raise

    def _run_instances_once(
        self,
        image: EcsImage,
        count: int,
        run_id: str,
        snapshot: str,
        system_disk_size_gb: int,
    ) -> list[str]:
        import volcenginesdkecs.models as ecs_models

        eip = None
        if self.config.allocate_public_ip:
            eip = ecs_models.EipAddressForRunInstancesInput(
                bandwidth_mbps=self.config.eip_bandwidth_mbps,
                charge_type="PayByTraffic",
            )

        request = ecs_models.RunInstancesRequest(
            image_id=image.image_id,
            instance_type=self.config.instance_type,
            count=count,
            min_count=count,
            network_interfaces=[
                ecs_models.NetworkInterfaceForRunInstancesInput(
                    subnet_id=self.config.subnet_id,
                    security_group_ids=[self.config.security_group_id],
                )
            ],
            eip_address=eip,
            instance_name=f"arena-{run_id}-{snapshot}".replace("_", "-")[:64],
            volumes=[
                ecs_models.VolumeForRunInstancesInput(
                    volume_type=self.config.system_disk_type,
                    size=system_disk_size_gb,
                )
            ],
            zone_id=self.config.zone_id,
            keep_image_credential=self.config.keep_image_credential,
            install_run_command_agent=self.config.install_run_command_agent,
            description=f"arena-osworld OSWorld evaluation run {run_id}, snapshot {snapshot}",
            tags=[
                ecs_models.TagForRunInstancesInput(key="run_id", value=run_id),
                ecs_models.TagForRunInstancesInput(key="snapshot", value=snapshot),
                ecs_models.TagForRunInstancesInput(key="managed_by", value="arena-osworld"),
            ],
        )
        if not self.config.keep_image_credential and self.config.password:
            request.password = self.config.password
        if self.config.project_name:
            request.project_name = self.config.project_name

        response = self._call_with_rate_limit_retry(
            "RunInstances",
            lambda request=request: self._api.run_instances(request),
        )
        return response.instance_ids or []

    def wait_for_instances(
        self,
        instance_ids: list[str],
        snapshot: str,
        image: EcsImage,
        os_type: str,
        timeout_seconds: int,
    ) -> list[InstanceRecord]:
        return self.wait_for_instance_groups(
            [
                _PendingInstanceGroup(
                    instance_ids=tuple(instance_ids),
                    snapshot=snapshot,
                    image=image,
                    os_type=os_type,
                    system_disk_size_gb=self._resolve_system_disk_size_gb(
                        image=image,
                        snapshot=snapshot,
                        override=None,
                    ),
                )
            ],
            timeout_seconds=timeout_seconds,
        )

    def wait_for_instance_groups(
        self,
        groups: list[_PendingInstanceGroup],
        timeout_seconds: int,
    ) -> list[InstanceRecord]:
        import volcenginesdkecs.models as ecs_models

        expected: dict[str, _PendingInstanceGroup] = {}
        ordered_ids: list[str] = []
        for group in groups:
            for instance_id in group.instance_ids:
                expected[instance_id] = group
                ordered_ids.append(instance_id)

        if not ordered_ids:
            return []

        deadline = time.time() + timeout_seconds
        last_instances: dict[str, Any] = {}
        while time.time() < deadline:
            for instance_id_batch in _chunks(
                ordered_ids,
                self.config.describe_instances_batch_size,
            ):
                response = self._call_with_rate_limit_retry(
                    "DescribeInstances",
                    lambda instance_id_batch=instance_id_batch: self._api.describe_instances(
                        ecs_models.DescribeInstancesRequest(
                            instance_ids=instance_id_batch,
                            max_results=len(instance_id_batch),
                        )
                    ),
                )
                for item in response.instances or []:
                    last_instances[item.instance_id] = item

            if all(
                str(getattr(last_instances.get(instance_id), "status", "")).upper()
                == "RUNNING"
                for instance_id in ordered_ids
            ):
                return [
                    _instance_record_from_sdk(
                        last_instances[instance_id],
                        snapshot=expected[instance_id].snapshot,
                        image=expected[instance_id].image,
                        os_type=expected[instance_id].os_type,
                        system_disk_size_gb=expected[instance_id].system_disk_size_gb,
                    )
                    for instance_id in ordered_ids
                ]
            time.sleep(5)

        observed = [
            (
                instance_id,
                getattr(last_instances.get(instance_id), "status", "MISSING"),
            )
            for instance_id in ordered_ids
        ]
        raise TimeoutError(
            f"Timed out waiting for instances to run: {ordered_ids}. "
            f"Last observed: {observed}"
        )

    def terminate_instances(self, instance_ids: list[str]) -> None:
        if not instance_ids:
            return

        import volcenginesdkecs.models as ecs_models

        self._call_with_rate_limit_retry(
            "DeleteInstances",
            lambda: self._api.delete_instances(
                ecs_models.DeleteInstancesRequest(instance_ids=instance_ids)
            ),
        )

    def stop_instances(self, instance_ids: list[str], *, force: bool = False) -> None:
        """Stop instances before capturing a reusable custom image."""
        if not instance_ids:
            return

        import volcenginesdkecs.models as ecs_models

        self._call_with_rate_limit_retry(
            "StopInstances",
            lambda: self._api.stop_instances(
                ecs_models.StopInstancesRequest(
                    instance_ids=instance_ids,
                    force_stop=force,
                )
            ),
        )

    def reboot_instances(self, instance_ids: list[str], *, force: bool = False) -> None:
        """Reboot instances, for example after Cloud Assistant installation."""
        if not instance_ids:
            return

        import volcenginesdkecs.models as ecs_models

        self._call_with_rate_limit_retry(
            "RebootInstances",
            lambda: self._api.reboot_instances(
                ecs_models.RebootInstancesRequest(
                    instance_ids=instance_ids,
                    force_stop=force,
                )
            ),
        )

    def wait_for_instance_status(
        self,
        instance_ids: list[str],
        *,
        expected_status: str,
        timeout_seconds: int = 600,
    ) -> None:
        """Wait for all requested instances to reach one ECS lifecycle state."""
        if not instance_ids:
            return

        import volcenginesdkecs.models as ecs_models

        expected = expected_status.upper()
        deadline = time.time() + timeout_seconds
        last_statuses: dict[str, str] = {}
        while time.time() < deadline:
            for instance_id_batch in _chunks(
                instance_ids,
                self.config.describe_instances_batch_size,
            ):
                response = self._call_with_rate_limit_retry(
                    "DescribeInstances",
                    lambda instance_id_batch=instance_id_batch: self._api.describe_instances(
                        ecs_models.DescribeInstancesRequest(
                            instance_ids=instance_id_batch,
                            max_results=len(instance_id_batch),
                        )
                    ),
                )
                for instance in response.instances or []:
                    last_statuses[str(instance.instance_id)] = str(instance.status or "")
            if all(
                last_statuses.get(instance_id, "").upper() == expected
                for instance_id in instance_ids
            ):
                return
            time.sleep(5)
        raise TimeoutError(
            f"Timed out waiting for instances to become {expected}: "
            + ", ".join(
                f"{instance_id}={last_statuses.get(instance_id, 'missing')}"
                for instance_id in instance_ids
            )
        )

    def create_image_from_instance(
        self,
        instance_id: str,
        *,
        image_name: str,
        description: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> str:
        """Create a full custom image from a stopped build instance."""
        import volcenginesdkecs.models as ecs_models

        request_tags = [
            ecs_models.TagForCreateImageInput(key=key, value=value)
            for key, value in sorted((tags or {}).items())
        ]
        request = ecs_models.CreateImageRequest(
            instance_id=instance_id,
            image_name=image_name,
            description=description,
            create_whole_image=True,
            tags=request_tags or None,
        )
        if self.config.project_name:
            request.project_name = self.config.project_name
        response = self._call_with_rate_limit_retry(
            "CreateImage",
            lambda: self._api.create_image(request),
        )
        image_id = str(response.image_id or "")
        if not image_id:
            raise RuntimeError("CreateImage returned an empty image id")
        return image_id

    def wait_for_image_available(
        self,
        image_id: str,
        *,
        timeout_seconds: int = 3600,
    ) -> SharedImage:
        """Wait for an image created by this account to become usable."""
        import volcenginesdkecs.models as ecs_models

        deadline = time.time() + timeout_seconds
        last_status = "missing"
        while time.time() < deadline:
            response = self._call_with_rate_limit_retry(
                "DescribeImages",
                lambda: self._api.describe_images(
                    ecs_models.DescribeImagesRequest(image_ids=[image_id], max_results=1)
                ),
            )
            images = response.images or []
            if images:
                image = images[0]
                last_status = str(image.status or "")
                normalized = last_status.lower()
                if normalized in {"available", "ok"}:
                    return SharedImage(
                        image_id=str(image.image_id),
                        image_name=str(image.image_name or ""),
                        os_type=str(image.os_type or ""),
                        status=last_status,
                        visibility=str(image.visibility or ""),
                        raw=image,
                        disk_size_gb=_image_system_disk_size_gb(image),
                    )
                if normalized in {"error", "failed"}:
                    raise RuntimeError(f"Image {image_id} entered status {last_status}")
            time.sleep(10)
        raise TimeoutError(
            f"Timed out waiting for image {image_id} to become available; last status={last_status}"
        )

    def modify_image_name(self, image_id: str, image_name: str) -> None:
        """Rename one custom image without changing its image ID."""
        import volcenginesdkecs.models as ecs_models

        self._call_with_rate_limit_retry(
            "ModifyImageAttribute",
            lambda: self._api.modify_image_attribute(
                ecs_models.ModifyImageAttributeRequest(
                    image_id=image_id,
                    image_name=image_name,
                )
            ),
        )

    def delete_images(
        self,
        image_ids: list[str],
        *,
        delete_binded_snapshots: bool = False,
    ) -> None:
        """Delete custom images and raise when ECS reports a per-image failure."""
        if not image_ids:
            return

        import volcenginesdkecs.models as ecs_models

        response = self._call_with_rate_limit_retry(
            "DeleteImages",
            lambda: self._api.delete_images(
                ecs_models.DeleteImagesRequest(
                    image_ids=image_ids,
                    delete_binded_snapshots=delete_binded_snapshots,
                )
            ),
        )
        failures = []
        for detail in response.operation_details or []:
            error = getattr(detail, "error", None)
            if error:
                failures.append(
                    f"{getattr(detail, 'image_id', '')}: "
                    f"{getattr(error, 'code', '')} {getattr(error, 'message', '')}".strip()
                )
        if failures:
            raise RuntimeError("DeleteImages failed: " + "; ".join(failures))

    def wait_for_images_deleted(
        self,
        image_ids: list[str],
        *,
        timeout_seconds: int = 900,
    ) -> None:
        """Wait until custom images no longer appear in DescribeImages."""
        if not image_ids:
            return

        import volcenginesdkecs.models as ecs_models

        deadline = time.time() + timeout_seconds
        remaining = set(image_ids)
        while time.time() < deadline:
            response = self._call_with_rate_limit_retry(
                "DescribeImages",
                lambda: self._api.describe_images(
                    ecs_models.DescribeImagesRequest(
                        image_ids=sorted(remaining),
                        max_results=max(1, len(remaining)),
                    )
                ),
            )
            remaining = {
                str(image.image_id)
                for image in response.images or []
                if str(image.image_id) in remaining
            }
            if not remaining:
                return
            time.sleep(5)
        raise TimeoutError(
            "Timed out waiting for custom images to be deleted: "
            + ", ".join(sorted(remaining))
        )

    def cloud_assistant_statuses(self, instance_ids: list[str]) -> dict[str, str]:
        """Return the current Cloud Assistant status for the requested instances."""
        if not instance_ids:
            return {}

        import volcenginesdkecs.models as ecs_models

        response = self._call_with_rate_limit_retry(
            "DescribeCloudAssistantStatus",
            lambda: self._api.describe_cloud_assistant_status(
                ecs_models.DescribeCloudAssistantStatusRequest(
                    instance_ids=instance_ids,
                    page_number=1,
                    page_size=max(1, len(instance_ids)),
                )
            ),
        )
        return {
            str(item.instance_id): str(item.status or "")
            for item in response.instances or []
        }

    def install_cloud_assistant(self, instance_ids: list[str]) -> list[str]:
        """Request Cloud Assistant installation and return accepted instance IDs."""
        if not instance_ids:
            return []

        import volcenginesdkecs.models as ecs_models

        response = self._call_with_rate_limit_retry(
            "InstallCloudAssistant",
            lambda: self._api.install_cloud_assistant(
                ecs_models.InstallCloudAssistantRequest(instance_ids=instance_ids)
            ),
        )
        failures = [
            f"{getattr(item, 'id', '')}: {getattr(item, 'error_message', '')}".strip()
            for item in response.failed_instances or []
        ]
        if failures:
            raise RuntimeError("InstallCloudAssistant failed: " + "; ".join(failures))
        return [str(instance_id) for instance_id in response.installing_instance_ids or []]

    def wait_for_cloud_assistant(
        self,
        instance_ids: list[str],
        timeout_seconds: int = 300,
    ) -> None:
        """Wait until the Cloud Assistant agent is online on every instance."""
        deadline = time.time() + timeout_seconds
        last_statuses: dict[str, str] = {}
        while time.time() < deadline:
            last_statuses = self.cloud_assistant_statuses(instance_ids)
            if all(
                last_statuses.get(instance_id, "").lower() in {"online", "running"}
                for instance_id in instance_ids
            ):
                return
            time.sleep(5)
        raise TimeoutError(
            "Timed out waiting for Cloud Assistant: "
            + ", ".join(
                f"{instance_id}={last_statuses.get(instance_id, 'missing')}"
                for instance_id in instance_ids
            )
        )

    def run_cloud_assistant_command(
        self,
        instance_ids: list[str],
        *,
        script: str,
        command_type: str,
        invocation_name: str,
        timeout_seconds: int,
    ) -> tuple[str, list[CloudAssistantCommandResult]]:
        """Run one Cloud Assistant command and wait for per-instance results."""
        import volcenginesdkecs.models as ecs_models

        encoded_script = base64.b64encode(script.encode("utf-8")).decode("ascii")
        request = ecs_models.RunCommandRequest(
            command_content=encoded_script,
            content_encoding="Base64",
            instance_ids=instance_ids,
            invocation_description="Provision OSWorld VM server code",
            invocation_name=invocation_name[:64],
            timeout=max(30, min(timeout_seconds, 86400)),
            type=command_type,
        )
        if self.config.project_name:
            request.project_name = self.config.project_name
        if command_type == "Shell":
            request.username = "root"
            request.working_dir = "/tmp"

        response = self._call_with_rate_limit_retry(
            "RunCommand",
            lambda: self._api.run_command(request),
        )
        invocation_id = str(response.invocation_id or "")
        if not invocation_id:
            raise RuntimeError("RunCommand returned an empty invocation id")
        results = self._wait_for_cloud_assistant_results(
            invocation_id,
            instance_ids,
            timeout_seconds=timeout_seconds,
        )
        return invocation_id, results

    def _wait_for_cloud_assistant_results(
        self,
        invocation_id: str,
        instance_ids: list[str],
        *,
        timeout_seconds: int,
    ) -> list[CloudAssistantCommandResult]:
        import volcenginesdkecs.models as ecs_models

        deadline = time.time() + timeout_seconds + 30
        last_results: dict[str, CloudAssistantCommandResult] = {}
        while time.time() < deadline:
            response = self._call_with_rate_limit_retry(
                "DescribeInvocationResults",
                lambda: self._api.describe_invocation_results(
                    ecs_models.DescribeInvocationResultsRequest(
                        invocation_id=invocation_id,
                        page_number=1,
                        page_size=max(1, len(instance_ids)),
                    )
                ),
            )
            for item in response.invocation_results or []:
                result = CloudAssistantCommandResult(
                    instance_id=str(item.instance_id or ""),
                    status=str(item.invocation_result_status or ""),
                    exit_code=item.exit_code,
                    output=_decode_cloud_assistant_output(str(item.output or "")),
                    error_code=str(item.error_code or ""),
                    error_message=str(item.error_message or ""),
                )
                if result.instance_id:
                    last_results[result.instance_id] = result

            if all(
                instance_id in last_results
                and _cloud_assistant_result_is_terminal(last_results[instance_id])
                for instance_id in instance_ids
            ):
                return [last_results[instance_id] for instance_id in instance_ids]
            time.sleep(3)

        states = ", ".join(
            f"{instance_id}={last_results.get(instance_id)}" for instance_id in instance_ids
        )
        raise TimeoutError(
            f"Timed out waiting for Cloud Assistant invocation {invocation_id}: {states}"
        )

    def _call_with_rate_limit_retry(self, operation_name: str, call: Callable[[], Any]) -> Any:
        delay = self.config.api_retry_base_seconds
        for attempt in range(self.config.api_max_retries + 1):
            try:
                return call()
            except Exception as exc:
                if attempt >= self.config.api_max_retries or not _is_rate_limit_error(exc):
                    raise
                time.sleep(delay)
                delay = min(delay * 2, self.config.api_retry_max_seconds)
        raise RuntimeError(f"{operation_name} retry loop exited unexpectedly")

    def _resolve_system_disk_size_gb(
        self,
        image: EcsImage,
        snapshot: str,
        override: int | None,
    ) -> int:
        image_min_size = image.disk_size_gb
        if override is not None:
            if override <= 0:
                raise ValueError("system_disk_size_gb override must be greater than 0.")
            return max(override, image_min_size or 0)

        configured_size = _configured_disk_size_gb(
            self.config.system_disk_size_gb_by_image,
            image=image,
            snapshot=snapshot,
        )
        if configured_size is not None:
            return max(configured_size, image_min_size or 0)

        if image_min_size is not None:
            return max(self.config.system_disk_size_gb, image_min_size)
        return self.config.system_disk_size_gb


def match_images_by_snapshot(
    snapshots: list[str],
    images: list[EcsImage],
    image_visibility: str | None = None,
) -> dict[str, EcsImage]:
    available = [image for image in images if image.status.lower() in {"available", "ok", ""}]
    by_exact = {image.image_name: image for image in available}
    matched: dict[str, EcsImage] = {}

    for snapshot in snapshots:
        image_id_matches = [image for image in available if image.image_id == snapshot]
        if len(image_id_matches) == 1:
            matched[snapshot] = image_id_matches[0]
            continue
        if snapshot in by_exact:
            matched[snapshot] = by_exact[snapshot]
            continue

        normalized_snapshot = _normalize_name(snapshot)
        candidates = [
            image
            for image in available
            if _normalize_name(image.image_name) == normalized_snapshot
            or normalized_snapshot in _normalize_name(image.image_name)
        ]
        if len(candidates) == 1:
            matched[snapshot] = candidates[0]
        elif len(candidates) > 1:
            candidates.sort(key=lambda image: (len(image.image_name), image.image_name))
            matched[snapshot] = candidates[0]

    missing = sorted(set(snapshots) - set(matched))
    if missing:
        names = ", ".join(sorted(image.image_name for image in available)[:30])
        visibility_label = image_visibility or "eligible"
        raise ValueError(
            f"No {visibility_label} image found for snapshots: "
            + ", ".join(missing)
            + f". Available image names include: {names}"
        )
    return matched


def _normalize_name(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _decode_cloud_assistant_output(value: str) -> str:
    stripped = value.strip()
    if not stripped or stripped.startswith(("{", "[")):
        return stripped
    try:
        decoded = base64.b64decode(stripped, validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return value
    return decoded


def _cloud_assistant_result_is_terminal(result: CloudAssistantCommandResult) -> bool:
    status = result.status.lower()
    if status in {"pending", "running", "starting", "scheduled", "stopping"}:
        return False
    if status in {
        "success",
        "succeeded",
        "finished",
        "failed",
        "error",
        "timeout",
        "cancelled",
        "canceled",
        "stopped",
    }:
        return True
    return result.exit_code is not None


def _parse_image_visibility(raw: str) -> str:
    visibility = raw.strip().lower()
    supported = {"private", "shared", "public", "marketplace"}
    if visibility not in supported:
        raise ValueError(
            "VOLCENGINE_IMAGE_VISIBILITY must be one of: "
            + ", ".join(sorted(supported))
        )
    return visibility


def _parse_disk_size_map(raw: str) -> dict[str, int]:
    if not raw.strip():
        return {}

    if raw.lstrip().startswith("{"):
        parsed = json.loads(raw)
    else:
        parsed = {}
        for item in raw.split(","):
            if not item.strip():
                continue
            if "=" not in item:
                raise ValueError(
                    "VOLCENGINE_SYSTEM_DISK_SIZE_GB_BY_IMAGE must be JSON or "
                    "comma-separated key=value pairs."
                )
            key, value = item.split("=", 1)
            parsed[key.strip()] = value.strip()

    if not isinstance(parsed, dict):
        raise ValueError("VOLCENGINE_SYSTEM_DISK_SIZE_GB_BY_IMAGE must be a mapping.")

    result: dict[str, int] = {}
    for key, value in parsed.items():
        size = int(value)
        if size <= 0:
            raise ValueError(f"Invalid disk size for {key!r}: {value!r}")
        key_str = str(key).strip()
        if not key_str:
            raise ValueError("Disk size mapping contains an empty key.")
        result[key_str] = size
    return result


def _configured_disk_size_gb(
    disk_size_by_image: dict[str, int],
    image: EcsImage,
    snapshot: str,
) -> int | None:
    candidates = [
        snapshot,
        image.image_name,
        image.image_id,
        _normalize_name(snapshot),
        _normalize_name(image.image_name),
        _normalize_name(image.image_id),
    ]
    for candidate in candidates:
        if candidate in disk_size_by_image:
            return disk_size_by_image[candidate]
    return None


def _image_system_disk_size_gb(image: Any) -> int | None:
    for attr in (
        "system_disk_size_gb",
        "system_disk_size",
        "min_disk_size_gb",
        "min_disk_size",
        "required_system_disk_size_gb",
        "required_system_disk_size",
        "image_size_gb",
        "image_size",
        "size",
    ):
        value = getattr(image, attr, None)
        if value in (None, ""):
            continue
        try:
            size = int(value)
        except (TypeError, ValueError):
            continue
        if 0 < size <= 2048:
            return size
    return None


def _split_count(count: int, max_count: int) -> Iterable[int]:
    if max_count <= 0:
        raise ValueError("run_instances_max_count must be greater than 0.")

    remaining = count
    while remaining > 0:
        current = min(remaining, max_count)
        yield current
        remaining -= current


def _chunks(items: list[str], size: int) -> Iterable[list[str]]:
    if size <= 0:
        raise ValueError("describe_instances_batch_size must be greater than 0.")

    for index in range(0, len(items), size):
        yield items[index : index + size]


def _pending_instance_ids(groups: list[_PendingInstanceGroup]) -> list[str]:
    return [
        instance_id
        for group in groups
        for instance_id in group.instance_ids
    ]


def _is_rate_limit_error(exc: Exception) -> bool:
    status_values = [
        getattr(exc, "status", None),
        getattr(exc, "status_code", None),
        getattr(getattr(exc, "response", None), "status", None),
        getattr(getattr(exc, "response", None), "status_code", None),
    ]
    if any(str(value) == "429" for value in status_values if value is not None):
        return True

    message_parts = [str(exc)]
    for attr in ("body", "code", "error_code", "message", "reason"):
        value = getattr(exc, attr, None)
        if value:
            message_parts.append(str(value))

    message = " ".join(message_parts).lower()
    return any(
        token in message
        for token in (
            "429",
            "limitexceeded",
            "qps",
            "rate limit",
            "requestlimit",
            "throttl",
            "too many request",
            "flow control",
        )
    )


def _instance_record_from_sdk(
    instance: Any,
    snapshot: str,
    image: EcsImage,
    os_type: str,
    system_disk_size_gb: int,
) -> InstanceRecord:
    private_ip = _instance_private_ip(instance)

    public_ip = None
    if instance.eip_address:
        public_ip = getattr(instance.eip_address, "ip_address", None)

    image_os_type = _os_type_from_image(image)

    return InstanceRecord(
        instance_id=instance.instance_id,
        private_ip=private_ip,
        public_ip=public_ip,
        os_type=image_os_type or os_type,
        metadata={
            "snapshot": snapshot,
            "image_id": image.image_id,
            "image_name": image.image_name,
            "image_os_type": image_os_type,
            "image_visibility": image.visibility,
            "task_os_type": os_type,
            "ecs_status": instance.status,
            "system_disk_size_gb": system_disk_size_gb,
        },
    )


def _instance_private_ip(instance: Any) -> str:
    for network_interface in getattr(instance, "network_interfaces", None) or []:
        private_ip = str(getattr(network_interface, "primary_ip_address", "") or "")
        if private_ip:
            return private_ip
    return ""


def _sdk_tags(resource: Any) -> dict[str, str]:
    return {
        str(getattr(tag, "key", "") or ""): str(getattr(tag, "value", "") or "")
        for tag in getattr(resource, "tags", None) or []
        if getattr(tag, "key", None)
    }


def _os_type_from_image(image: EcsImage) -> str:
    value = f"{image.os_type} {image.image_name}".lower()
    if "windows" in value:
        return "Windows"
    return "Ubuntu"
