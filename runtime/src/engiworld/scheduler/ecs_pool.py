"""ECS instance pool adapter.

The environment engine provides the low-level Volcengine operations.
"""

from __future__ import annotations

from pathlib import Path

from engiworld.scheduler.runner import ensure_engine_importable, resolve_engine_path
from engiworld.scheduler.schemas import InstanceRecord


def provision_instances(
    ubuntu_count: int,
    windows_count: int = 0,
    max_workers: int = 8,
    osworld_path: str | None = None,
) -> list[InstanceRecord]:
    ensure_engine_importable(resolve_engine_path(osworld_path))
    from lib_volcengine_pool import provision_vm_pool

    records = provision_vm_pool(
        ubuntu_count=ubuntu_count,
        windows_count=windows_count,
        max_workers=max_workers,
    )
    return [
        InstanceRecord(
            instance_id=item["instance_id"],
            private_ip=item["private_ip"],
            os_type=item.get("os_type", "Ubuntu"),
            public_ip=item.get("public_ip"),
        )
        for item in records
    ]


def terminate_instances(instance_ids: list[str], osworld_path: str | None = None) -> None:
    ensure_engine_importable(resolve_engine_path(osworld_path))
    from lib_volcengine_pool import terminate_instances as osworld_terminate_instances

    osworld_terminate_instances(instance_ids)


def expected_submodule_path(repo_root: str | Path = ".") -> Path:
    return Path(repo_root).resolve() / "engine"

