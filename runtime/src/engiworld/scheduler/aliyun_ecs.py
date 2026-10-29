"""Alibaba ECS adapter for the existing Redis master/worker scheduler."""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from engiworld.cloud_journal import CloudJournal
from engiworld.scheduler.schemas import InstanceRecord
from engiworld.scheduler.volcengine_ecs import EcsImage, EcsInstance


@dataclass
class AliyunLaunchConfig:
    region: str
    instance_type: str
    image_visibility: str = "shared"
    ttl_minutes: int = 1800  # Includes the default 24-hour API recovery window.

    @classmethod
    def from_env(cls):
        required = ("ALIYUN_REGION", "ALIYUN_INSTANCE_TYPE", "ALIYUN_ACCESS_KEY_ID",
                    "ALIYUN_ACCESS_KEY_SECRET", "ALIYUN_VSWITCH_ID", "ALIYUN_SECURITY_GROUP_ID")
        if any(not os.getenv(key) for key in required):
            raise ValueError("Set " + ", ".join(key for key in required if not os.getenv(key)))
        return cls(os.environ["ALIYUN_REGION"], os.environ["ALIYUN_INSTANCE_TYPE"],
                   ttl_minutes=int(os.getenv("DEFAULT_TTL_MINUTES", "1800")))


class AliyunEcsClient:
    provider_name = "aliyun"
    def __init__(self, config, *, journal_dir=None, client=None):
        from alibabacloud_ecs20140526.client import Client
        from alibabacloud_tea_openapi.models import Config
        self.config = config
        self.client = client or Client(Config(region_id=config.region,
            access_key_id=os.environ["ALIYUN_ACCESS_KEY_ID"],
            access_key_secret=os.environ["ALIYUN_ACCESS_KEY_SECRET"]))
        self.journal_dir = Path(journal_dir or os.getenv("ENGIWORLD_CLOUD_JOURNAL_DIR", "results/cloud-instances/aliyun"))

    def list_images(self):
        from engiworld.cloud_eval import CATALOG, find_cloud_image
        catalog = json.loads(Path(os.getenv("ALIYUN_IMAGE_CATALOG", str(CATALOG))).read_text())
        result = []
        for snapshot, entry in catalog.get("regions", {}).get(self.config.region, {}).items():
            if getattr(self, "snapshots", None) and snapshot not in self.snapshots:
                continue
            image_id = entry.get("image_id") or find_cloud_image(entry["image_name"], self.config.region)
            image = self.get_image(image_id, snapshot)
            result.append(image)
        return result

    def get_image(self, image_id, snapshot):
        from alibabacloud_ecs20140526 import models
        images = self.client.describe_images(models.DescribeImagesRequest(
            region_id=self.config.region, image_id=image_id)).body.images.image
        if len(images) != 1 or images[0].status != "Available":
            raise ValueError(f"Image {image_id} is unavailable")
        image = images[0]
        return EcsImage(image_id, snapshot, image.os_type, "available", "shared", image, int(image.size))

    def list_instances(self, *, instance_ids=None, instance_name=None, **kwargs):
        from alibabacloud_ecs20140526 import models
        page = 1
        result = []
        while True:
            response = self.client.describe_instances(models.DescribeInstancesRequest(
                region_id=self.config.region, instance_ids=json.dumps(instance_ids) if instance_ids else None,
                instance_name=instance_name, page_number=page, page_size=100)).body
            items = response.instances.instance or []
            for item in items:
                if instance_ids is not None and item.instance_id not in instance_ids:
                    continue
                if instance_name is not None and item.instance_name != instance_name:
                    continue
                private = item.vpc_attributes.private_ip_address.ip_address if item.vpc_attributes else []
                result.append(EcsInstance(item.instance_id, item.instance_name,
                    private[0] if private else "", item.image_id, item.os_type, item.status, {}, item))
            if page * 100 >= (response.total_count or len(items)):
                return result
            page += 1

    def run_instance_groups(self, groups, run_id, wait_timeout_seconds=900):
        from alibabacloud_ecs20140526 import models
        records = []
        transaction = self.journal_dir / uuid.uuid4().hex
        try:
            for group in groups:
                image = self.get_image(group.image.image_id, group.snapshot)
                for _ in range(group.count):
                    journal = CloudJournal(transaction, "aliyun", run_id=run_id,
                                           region=self.config.region, image_id=image.image_id)
                    name = "EngiWorld-" + journal.data["client_token"][:24]
                    journal.update(instance_name=name)
                    disks = []
                    mappings = image.raw.disk_device_mappings
                    size = max(20, image.disk_size_gb or 20)
                    for disk in (mappings.disk_device_mapping or []) if mappings else []:
                        if disk.type == "system":
                            size = max(size, int(disk.size))
                        elif disk.type == "data":
                            if not disk.snapshot_id:
                                raise ValueError("Image data disk has no snapshot ID")
                            disks.append(models.RunInstancesRequestDataDisk(snapshot_id=disk.snapshot_id,
                                size=int(disk.size), category="cloud_essd", delete_with_instance=True))
                    release = datetime.now(timezone.utc) + timedelta(minutes=max(30, self.config.ttl_minutes))
                    release = (release + timedelta(seconds=59)).replace(second=0, microsecond=0)
                    request = models.RunInstancesRequest(region_id=self.config.region,
                        image_id=image.image_id, instance_type=self.config.instance_type,
                        v_switch_id=os.environ["ALIYUN_VSWITCH_ID"],
                        security_group_id=os.environ["ALIYUN_SECURITY_GROUP_ID"],
                        instance_name=name, client_token=journal.data["client_token"], amount=1,
                        password_inherit=True, deletion_protection=False, instance_charge_type="PostPaid",
                        internet_charge_type="PayByTraffic",
                        internet_max_bandwidth_out=int(os.getenv("ALIYUN_PUBLIC_BANDWIDTH", "0")),
                        system_disk=models.RunInstancesRequestSystemDisk(size=str(size), category="cloud_essd"),
                        data_disk=disks or None, auto_release_time=release.strftime('%Y-%m-%dT%H:%M:%SZ'))
                    journal.update(state="submitting", auto_release_time=request.auto_release_time)
                    ids = self.client.run_instances(request).body.instance_id_sets.instance_id_set
                    if not ids:
                        raise RuntimeError("RunInstances returned no instance IDs; outcome unknown")
                    journal.update(state="created", instance_ids=ids)
                    deadline = time.monotonic() + wait_timeout_seconds
                    while True:
                        instances = self.list_instances(instance_ids=ids)
                        if len(instances) == len(ids) and all(i.status.lower() == "running" for i in instances):
                            break
                        if time.monotonic() >= deadline:
                            raise TimeoutError(f"Instances did not reach Running: {ids}")
                        time.sleep(5)
                    for instance in instances:
                        records.append(InstanceRecord(instance.instance_id, instance.private_ip,
                            os_type=group.os_type, metadata={"provider": "aliyun", "snapshot": group.snapshot,
                            "image_id": image.image_id, "image_name": group.snapshot,
                            "image_visibility": "shared", "system_disk_size_gb": size}))
            return records
        except BaseException:
            from engiworld.cloud_journal import cleanup_journals
            cleanup_journals(self, transaction)
            raise

    def terminate_instances(self, instance_ids, timeout_seconds=300):
        """Send at most one delete per instance and poll until absence is confirmed."""
        from alibabacloud_ecs20140526 import models
        for instance_id in dict.fromkeys(instance_ids):
            current = self.list_instances(instance_ids=[instance_id])
            if not current:
                continue
            if current[0].status.lower() not in {"deleting", "deleted", "terminating"}:
                try:
                    self.client.delete_instances(models.DeleteInstancesRequest(region_id=self.config.region,
                        instance_id=[instance_id], force=True))
                except Exception:
                    # A concurrent deletion or lost delete response is only success after confirmation.
                    remaining = self.list_instances(instance_ids=[instance_id])
                    if remaining and remaining[0].status.lower() not in {"deleting", "terminating", "deleted"}:
                        raise
            deadline = time.monotonic() + timeout_seconds
            while self.list_instances(instance_ids=[instance_id]):
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Deletion not confirmed for {instance_id}")
                time.sleep(2)
