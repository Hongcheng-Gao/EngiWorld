"""Select a cloud backend without changing the Redis scheduling protocol."""
from __future__ import annotations

from pathlib import Path


def make_cloud_client(provider, *, journal_dir=None):
    if provider == "aliyun":
        from engiworld.scheduler.aliyun_ecs import AliyunEcsClient, AliyunLaunchConfig
        return AliyunEcsClient(AliyunLaunchConfig.from_env(), journal_dir=journal_dir)
    if provider != "volcengine":
        raise ValueError(f"Unknown cloud provider: {provider}")
    from engiworld.scheduler.volcengine_ecs import VolcengineEcsClient, VolcengineLaunchConfig
    client = VolcengineEcsClient(VolcengineLaunchConfig.from_env())
    if journal_dir:
        client.journal_dir = Path(journal_dir)
    return client


def client_for_store(store):
    provider = store.client.hget(store.key("meta"), "cloud_provider") or "volcengine"
    path = store.client.hget(store.key("meta"), "cloud_journal_dir")
    return make_cloud_client(provider, journal_dir=path)
