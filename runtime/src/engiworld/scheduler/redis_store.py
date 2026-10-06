"""Redis-backed scheduler state store.

The MVP uses coarse Redis locks via ``SET key value NX EX ttl``. This keeps the
coordination model easy to inspect while master remains a single control point.
"""

from __future__ import annotations

import json
import time
import uuid
from collections import defaultdict
from dataclasses import asdict
from typing import Any

from engiworld.active_time import (
    LEDGER_FIELD, PauseTrackingError, active_time_metrics, budget_outcome, pause_mapping,
)
from engiworld.scheduler.error_policy import MODEL_ENVIRONMENT_ERROR_CATEGORY
from engiworld.scheduler.schemas import (
    EvalConfig,
    InstanceRecord,
    InstanceStatus,
    RunStatus,
    TaskSpec,
)
from engiworld.scheduler.task_bundle import DEFAULT_TASK_BUCKET

RUN_STATE_TTL_SECONDS = 3 * 24 * 60 * 60
RUN_COMPLETION_SIGNAL_TTL_SECONDS = RUN_STATE_TTL_SECONDS
CLAIM_LOCK_TTL_SECONDS = 3
TASK_MUTATION_LOCK_TTL_SECONDS = 30
WORKER_HEARTBEAT_TTL_SECONDS = 10 * 60
GLOBAL_READY_TASKS_KEY = "osworld:tasks:ready"
GLOBAL_LOCK_PREFIX = "osworld:lock"
GLOBAL_VM_CAPACITY_LIMIT_KEY = "osworld:global:vm_capacity:limit"
GLOBAL_VM_CAPACITY_USED_KEY = "osworld:global:vm_capacity:used"
GLOBAL_VM_CAPACITY_BY_RUN_KEY = "osworld:global:vm_capacity:by_run"
GLOBAL_VM_CAPACITY_RELEASED_IDS_KEY = "osworld:global:vm_capacity:released_ids"


def connect(redis_url: str):
    try:
        import redis
    except ImportError as exc:
        raise ImportError("Install redis to use RedisStore: pip install redis") from exc

    client = redis.Redis.from_url(redis_url, decode_responses=True)
    client.ping()
    return client


class RedisStore:
    def __init__(self, redis_url: str, run_id: str, client: Any | None = None):
        self.redis_url = redis_url
        self.client = client or connect(redis_url)
        self.run_id = run_id

    def key(self, suffix: str) -> str:
        return f"osworld:{self.run_id}:{suffix}"

    def lock_key(self, name: str) -> str:
        return self.key(f"lock:{name}")

    def global_lock_key(self, name: str) -> str:
        return f"{GLOBAL_LOCK_PREFIX}:{name}"

    def task_source_key(self) -> str:
        return f"task_source_{self.run_id}"

    def try_reserve_global_vm_slots(
        self,
        count: int,
        limit: int,
        allow_partial: bool = False,
    ) -> dict[str, Any]:
        """Atomically reserve VM capacity shared by every run in this Redis DB."""

        if count <= 0:
            raise ValueError("global VM slot reservation count must be greater than zero")
        if limit <= 0:
            return {"status": "disabled", "requested": count}

        token = self.acquire_global_lock("vm_capacity", ttl_seconds=10)
        if token is None:
            return {"status": "lock_busy", "requested": count, **self.global_vm_capacity()}
        try:
            configured_limit = _int(self.client.get(GLOBAL_VM_CAPACITY_LIMIT_KEY), 0)
            used = _int(self.client.get(GLOBAL_VM_CAPACITY_USED_KEY), 0)
            if configured_limit and configured_limit != limit:
                if used:
                    return {
                        "status": "limit_mismatch",
                        "requested": count,
                        "requested_limit": limit,
                        **self.global_vm_capacity(),
                    }
                self.client.set(GLOBAL_VM_CAPACITY_LIMIT_KEY, limit)
                configured_limit = limit
            elif not configured_limit:
                self.client.set(GLOBAL_VM_CAPACITY_LIMIT_KEY, limit)
                configured_limit = limit

            requested = count
            if allow_partial:
                count = min(count, max(0, configured_limit - used))
            if count == 0 or used + count > configured_limit:
                return {
                    "status": "waiting",
                    "requested": requested,
                    **self.global_vm_capacity(),
                }

            used = self.client.incrby(GLOBAL_VM_CAPACITY_USED_KEY, count)
            run_reserved = self.client.hincrby(
                GLOBAL_VM_CAPACITY_BY_RUN_KEY,
                self.run_id,
                count,
            )
            return {
                "status": "acquired",
                "requested": requested,
                "acquired": count,
                "limit": configured_limit,
                "used": used,
                "available": max(0, configured_limit - used),
                "run_reserved": run_reserved,
            }
        finally:
            self.release_global_lock("vm_capacity", token)

    def release_global_vm_slots(
        self,
        count: int | None = None,
        *,
        instance_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Release this run's slots after ECS deletion; instance releases are idempotent."""

        token = None
        deadline = time.time() + 30
        while token is None and time.time() < deadline:
            token = self.acquire_global_lock("vm_capacity", ttl_seconds=10)
            if token is None:
                time.sleep(0.1)
        if token is None:
            raise RuntimeError("Timed out acquiring global VM capacity lock for release")

        try:
            held = _int(
                self.client.hget(GLOBAL_VM_CAPACITY_BY_RUN_KEY, self.run_id),
                0,
            )
            requested_release = held if count is None and instance_ids is None else count or 0
            newly_released_ids: list[str] = []
            if instance_ids is not None:
                for instance_id in dict.fromkeys(instance_ids):
                    if not self.client.sismember(
                        GLOBAL_VM_CAPACITY_RELEASED_IDS_KEY,
                        instance_id,
                    ):
                        newly_released_ids.append(instance_id)
                requested_release += len(newly_released_ids)

            released = min(held, max(0, requested_release))
            remaining = held - released
            if remaining:
                self.client.hset(
                    GLOBAL_VM_CAPACITY_BY_RUN_KEY,
                    mapping={self.run_id: remaining},
                )
            else:
                self.client.hdel(GLOBAL_VM_CAPACITY_BY_RUN_KEY, self.run_id)

            used = max(
                0,
                _int(self.client.get(GLOBAL_VM_CAPACITY_USED_KEY), 0) - released,
            )
            if used:
                self.client.set(GLOBAL_VM_CAPACITY_USED_KEY, used)
                if newly_released_ids:
                    self.client.sadd(
                        GLOBAL_VM_CAPACITY_RELEASED_IDS_KEY,
                        *newly_released_ids,
                    )
            else:
                self.client.delete(
                    GLOBAL_VM_CAPACITY_USED_KEY,
                    GLOBAL_VM_CAPACITY_LIMIT_KEY,
                    GLOBAL_VM_CAPACITY_BY_RUN_KEY,
                    GLOBAL_VM_CAPACITY_RELEASED_IDS_KEY,
                )
            capacity = self.global_vm_capacity()
            return {
                "released": released,
                "requested_release": requested_release,
                "newly_released_instance_ids": newly_released_ids,
                **capacity,
            }
        finally:
            self.release_global_lock("vm_capacity", token)

    def global_vm_capacity(self) -> dict[str, Any]:
        limit = _int(self.client.get(GLOBAL_VM_CAPACITY_LIMIT_KEY), 0)
        used = _int(self.client.get(GLOBAL_VM_CAPACITY_USED_KEY), 0)
        run_reserved = _int(
            self.client.hget(GLOBAL_VM_CAPACITY_BY_RUN_KEY, self.run_id),
            0,
        )
        return {
            "limit": limit,
            "used": used,
            "available": max(0, limit - used) if limit else None,
            "run_reserved": run_reserved,
        }

    def set_task_source(self, file_path: str) -> None:
        payload = {
            "bucket": DEFAULT_TASK_BUCKET,
            "file_path": file_path.lstrip("/"),
        }
        self.client.set(
            self.task_source_key(),
            json.dumps(payload, ensure_ascii=False),
        )
        self.client.hset(
            self.key("meta"),
            mapping={
                "task_source_key": self.task_source_key(),
                "task_source_set": "true",
                "updated_at": int(time.time()),
            },
        )

    def get_task_source(self) -> dict[str, str] | None:
        raw = self.client.get(self.task_source_key())
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid task source payload in {self.task_source_key()}") from exc
        bucket = str(payload.get("bucket") or "")
        file_path = str(payload.get("file_path") or "")
        if not bucket or not file_path:
            raise ValueError(f"Invalid task source payload in {self.task_source_key()}")
        return {"bucket": bucket, "file_path": file_path}

    def acquire_lock(
        self,
        name: str,
        ttl_seconds: int = 30,
        owner: str | None = None,
    ) -> str | None:
        token = owner or uuid.uuid4().hex
        acquired = self.client.set(self.lock_key(name), token, nx=True, ex=ttl_seconds)
        return token if acquired else None

    def acquire_global_lock(
        self,
        name: str,
        ttl_seconds: int = 30,
        owner: str | None = None,
    ) -> str | None:
        token = owner or uuid.uuid4().hex
        acquired = self.client.set(self.global_lock_key(name), token, nx=True, ex=ttl_seconds)
        return token if acquired else None

    def release_lock(self, name: str, token: str) -> bool:
        return self._release_lock_key(self.lock_key(name), token)

    def release_global_lock(self, name: str, token: str) -> bool:
        return self._release_lock_key(self.global_lock_key(name), token)

    def _release_lock_key(self, key: str, token: str) -> bool:
        with self.client.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(key)
                    if pipe.get(key) != token:
                        pipe.unwatch()
                        return False
                    pipe.multi()
                    pipe.delete(key)
                    pipe.execute()
                    return True
                except Exception as exc:
                    if exc.__class__.__name__ == "WatchError":
                        continue
                    raise

    def refresh_lock(self, name: str, token: str, ttl_seconds: int = 30) -> bool:
        key = self.lock_key(name)
        with self.client.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(key)
                    if pipe.get(key) != token:
                        pipe.unwatch()
                        return False
                    pipe.multi()
                    pipe.expire(key, ttl_seconds)
                    pipe.execute()
                    return True
                except Exception as exc:
                    if exc.__class__.__name__ == "WatchError":
                        continue
                    raise

    def register_run(
        self,
        eval_config: EvalConfig,
        total_tasks: int,
        instance_count: int,
        allocation: dict[str, int] | None = None,
        snapshot_os_type: dict[str, str] | None = None,
        agent_profile: str | None = None,
        agent_config: dict[str, Any] | None = None,
        agent_env: dict[str, str] | None = None,
        retry_source_run_id: str | None = None,
        vm_osworld_bundle: dict[str, Any] | None = None,
        vm_osworld_provision_config: dict[str, Any] | None = None,
    ) -> None:
        now = int(time.time())
        self.client.delete(self.key("control:completion"))
        self.client.hset(
            self.key("meta"),
            mapping={
                "status": RunStatus.INITIALIZING.value,
                "run_id": self.run_id,
                "created_at": now,
                "updated_at": now,
                "total_tasks": total_tasks,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "api_incomplete_tasks": 0,
                "infra_incomplete_tasks": 0,
                "running_tasks": 0,
                "pending_tasks": 0,
                "available_instance_count": 0,
                "provisioned_instance_count": 0,
                "terminated_instance_count": 0,
                "target_instance_count": instance_count,
                "allocation": json.dumps(allocation or {}),
                "snapshot_os_type": json.dumps(snapshot_os_type or {}),
                "eval_config": json.dumps(asdict(eval_config)),
                "agent_profile": agent_profile or "",
                "agent_config": json.dumps(agent_config or {}, ensure_ascii=False),
                "agent_env": json.dumps(agent_env or {}, ensure_ascii=False),
                "retry_source_run_id": retry_source_run_id or "",
                "vm_osworld_bundle": json.dumps(
                    vm_osworld_bundle or {}, ensure_ascii=False
                ),
                "vm_osworld_provision_config": json.dumps(
                    vm_osworld_provision_config or {}, ensure_ascii=False
                ),
            },
        )
        self.client.hdel(self.key("meta"), "completion_signal", "completion_signal_at")

    def agent_settings(self) -> dict[str, Any]:
        meta = self.client.hgetall(self.key("meta"))
        return {
            "agent_profile": meta.get("agent_profile", ""),
            "agent_config": _json_object(meta.get("agent_config")),
            "agent_env": _json_object(meta.get("agent_env")),
        }

    def vm_osworld_settings(self) -> dict[str, Any]:
        meta = self.client.hgetall(self.key("meta"))
        return {
            "bundle": _json_object(meta.get("vm_osworld_bundle")),
            "provision_config": _json_object(
                meta.get("vm_osworld_provision_config")
            ),
        }

    def mark_run_status(self, status: RunStatus) -> None:
        self.client.hset(
            self.key("meta"),
            mapping={"status": status.value, "updated_at": int(time.time())},
        )
        if status in {RunStatus.COMPLETED, RunStatus.FAILED}:
            self.expire_run_state()

    def mark_run_completion_signal(self, summary: dict[str, Any] | None = None) -> dict[str, Any]:
        now = int(time.time())
        payload = {
            "run_id": self.run_id,
            "status": RunStatus.COMPLETED.value,
            "completed_at": now,
            "total_tasks": _int((summary or {}).get("total_tasks"), 0),
            "completed_tasks": _int((summary or {}).get("completed_tasks"), 0),
            "failed_tasks": _int((summary or {}).get("failed_tasks"), 0),
            "api_incomplete_tasks": _int(
                (summary or {}).get("api_incomplete_tasks"), 0
            ),
            "infra_incomplete_tasks": _int(
                (summary or {}).get("infra_incomplete_tasks"), 0
            ),
        }
        self.client.set(
            self.key("control:completion"),
            json.dumps(payload, ensure_ascii=False),
            ex=RUN_COMPLETION_SIGNAL_TTL_SECONDS,
        )
        self.client.hset(
            self.key("meta"),
            mapping={
                "completion_signal": RunStatus.COMPLETED.value,
                "completion_signal_at": now,
                "updated_at": now,
            },
        )
        self.expire_run_state()
        return payload

    def run_completion_signal(self) -> dict[str, Any]:
        raw = self.client.get(self.key("control:completion"))
        if not raw:
            return {}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {"status": raw}
        return payload if isinstance(payload, dict) else {"status": str(payload)}

    def is_run_completion_signaled(self) -> bool:
        return self.run_completion_signal().get("status") == RunStatus.COMPLETED.value

    def record_worker_heartbeat(
        self,
        worker_id: str,
        status: str = "alive",
        task_id: str | None = None,
        instance_id: str | None = None,
    ) -> None:
        mapping = {
            "worker_id": worker_id,
            "status": status,
            "hostname": "",
            "heartbeat_at": int(time.time()),
            "current_task_id": task_id or "",
            "current_instance_id": instance_id or "",
        }
        worker_key = self.key(f"worker:{worker_id}")
        self.client.hset(worker_key, mapping=mapping)
        self.client.expire(worker_key, WORKER_HEARTBEAT_TTL_SECONDS)

    def expire_run_state(self, ttl_seconds: int = RUN_STATE_TTL_SECONDS) -> None:
        keys = self._run_state_keys()
        if not keys:
            return
        pipe = self.client.pipeline()
        for key in keys:
            pipe.expire(key, ttl_seconds)
        pipe.execute()

    def clear_run_state(self) -> dict[str, Any]:
        ready_removed = self.remove_global_ready_tasks()
        keys = self._run_state_keys()
        if keys:
            self.client.delete(*keys)
        return {
            "ready_tasks_removed": ready_removed,
            "redis_keys_deleted": len(keys),
        }

    def remove_global_ready_tasks(self) -> int:
        removed = 0
        pipe = self.client.pipeline()
        for member in self.client.zrange(GLOBAL_READY_TASKS_KEY, 0, -1):
            ref = _global_task_ref(member)
            if ref is None:
                continue
            run_id, _ = ref
            if run_id != self.run_id:
                continue
            pipe.zrem(GLOBAL_READY_TASKS_KEY, member)
            removed += 1
        if removed:
            pipe.execute()
        return removed

    def _run_state_keys(self) -> set[str]:
        keys = {
            self.task_source_key(),
            self.key("meta"),
            self.key("summary"),
            self.key("control:completion"),
            self.key("tasks:payload"),
            self.key("tasks:processing"),
            self.key("tasks:completed"),
            self.key("tasks:failed"),
            self.key("tasks:api_incomplete"),
            self.key("tasks:infra_incomplete"),
            self.key("instances:all"),
            self.key("instances:available"),
            self.key("instances:leased"),
            self.key("instances:quarantine"),
            self.key("instances:terminating"),
            self.key("instances:terminated"),
        }
        for task_id in self.client.hkeys(self.key("tasks:payload")):
            keys.add(self.key(f"task:{task_id}"))

        snapshots = set()
        for instance_id in self.all_instance_ids():
            keys.add(self.key(f"instance:{instance_id}"))
            raw = self.client.hgetall(self.key(f"instance:{instance_id}"))
            metadata = json.loads(raw.get("metadata") or "{}") if raw else {}
            snapshots.add(str(metadata.get("snapshot", "default")))

        for snapshot in snapshots:
            keys.add(self.key(f"instances:by_snapshot:{snapshot}"))
            keys.add(self.key(f"instances:available:{snapshot}"))
        return keys

    def set_task_pause(
        self, task_id: str, instance_id: str, worker_id: str, attempt: int,
        reason: str, paused: bool, now: float | None = None,
    ) -> None:
        """Record before pausing the process, and close before resuming it.

        Leases/heartbeats remain required during a pause. This records time; it
        does not send OS signals or restart the task, VM, or original start.
        """
        lock_name = f"complete_task:{task_id}"
        lock = self.acquire_lock(lock_name, ttl_seconds=TASK_MUTATION_LOCK_TTL_SECONDS,
                                 owner=worker_id)
        if lock is None:
            raise PauseTrackingError(f"Could not lock pause ledger for {task_id}")
        try:
            task_key = self.key(f"task:{task_id}")
            raw = self.client.hgetall(task_key)
            if (raw.get("status") not in {"running", "leased"}
                    or raw.get("worker_id") != worker_id
                    or raw.get("instance_id") != instance_id
                    or _int(raw.get("attempt"), 0) != attempt):
                raise PauseTrackingError(f"Pause owner/attempt changed for {task_id}")
            self.client.hset(task_key, mapping=pause_mapping(
                raw, reason, paused, time.time() if now is None else now))
        finally:
            self.release_lock(lock_name, lock)

    def refresh_task_and_instance_leases(
        self,
        task_id: str,
        instance_id: str,
        worker_id: str,
        task_lease_ttl_seconds: int,
        instance_lease_ttl_seconds: int,
        runtime_phase: str = "",
    ) -> bool:
        task_worker = self.client.hget(self.key(f"task:{task_id}"), "worker_id")
        instance_worker = self.client.hget(self.key(f"instance:{instance_id}"), "worker_id")
        if task_worker != worker_id or instance_worker != worker_id:
            return False

        now = int(time.time())
        task_deadline = now + task_lease_ttl_seconds
        instance_deadline = now + instance_lease_ttl_seconds
        pipe = self.client.pipeline()
        pipe.hset(
            self.key(f"task:{task_id}"),
            mapping={
                "lease_deadline_ts": task_deadline,
                "updated_at": now,
                "runtime_phase": runtime_phase,
            },
        )
        pipe.hset(
            self.key(f"instance:{instance_id}"),
            mapping={"lease_deadline_ts": instance_deadline, "updated_at": now},
        )
        pipe.zadd(self.key("tasks:processing"), {task_id: task_deadline})
        pipe.zadd(self.key("instances:leased"), {instance_id: instance_deadline})
        pipe.hset(
            self.key(f"worker:{worker_id}"),
            mapping={
                "status": "running",
                "current_task_id": task_id,
                "current_instance_id": instance_id,
                "heartbeat_at": now,
            },
        )
        pipe.execute()
        return True

    def register_instances(
        self,
        instances: list[InstanceRecord],
        status: str = InstanceStatus.AVAILABLE.value,
    ) -> None:
        if status not in {
            InstanceStatus.PROVISIONING.value,
            InstanceStatus.AVAILABLE.value,
        }:
            raise ValueError(f"Unsupported initial instance status: {status}")
        pipe = self.client.pipeline()
        for instance in instances:
            snapshot = str(instance.metadata.get("snapshot", "default"))
            instance_payload = asdict(instance)
            instance_mapping = {
                key: value
                for key, value in instance_payload.items()
                if key != "metadata" and value is not None
            }
            pipe.sadd(self.key("instances:all"), instance.instance_id)
            pipe.hset(
                self.key(f"instance:{instance.instance_id}"),
                mapping={
                    **instance_mapping,
                    "status": status,
                    "boot_at": int(time.time()),
                    "metadata": json.dumps(instance.metadata),
                },
            )
            pipe.sadd(self.key(f"instances:by_snapshot:{snapshot}"), instance.instance_id)
            if status == InstanceStatus.AVAILABLE.value:
                pipe.lpush(self.key("instances:available"), instance.instance_id)
                pipe.lpush(
                    self.key(f"instances:available:{snapshot}"), instance.instance_id
                )
        if instances:
            if status == InstanceStatus.AVAILABLE.value:
                pipe.hincrby(
                    self.key("meta"), "available_instance_count", len(instances)
                )
            pipe.hincrby(self.key("meta"), "provisioned_instance_count", len(instances))
        pipe.execute()

    def mark_instances_available(self, instances: list[InstanceRecord]) -> None:
        pipe = self.client.pipeline()
        promoted = 0
        for instance in instances:
            instance_key = self.key(f"instance:{instance.instance_id}")
            current_status = self.client.hget(instance_key, "status")
            if current_status != InstanceStatus.PROVISIONING.value:
                continue
            snapshot = str(instance.metadata.get("snapshot", "default"))
            pipe.hset(
                instance_key,
                mapping={
                    "status": InstanceStatus.AVAILABLE.value,
                    "metadata": json.dumps(instance.metadata),
                    "updated_at": int(time.time()),
                },
            )
            pipe.lpush(self.key("instances:available"), instance.instance_id)
            pipe.lpush(self.key(f"instances:available:{snapshot}"), instance.instance_id)
            promoted += 1
        if promoted:
            pipe.hincrby(self.key("meta"), "available_instance_count", promoted)
        pipe.execute()

    def enqueue_tasks(self, tasks: list[TaskSpec], score_start: int | None = None) -> None:
        score = score_start if score_start is not None else int(time.time() * 1000)
        pipe = self.client.pipeline()
        for offset, task in enumerate(tasks):
            task_payload = _task_payload_for_run(self.run_id, task)
            task_score = score + offset
            pipe.hset(
                self.key(f"task:{task.task_id}"),
                mapping={
                    **task_payload,
                    "status": "pending",
                    "attempt": 0,
                    "metadata": json.dumps(task_payload["metadata"], ensure_ascii=False),
                    "payload": json.dumps(task_payload),
                },
            )
            pipe.hset(self.key("tasks:payload"), task.task_id, json.dumps(task_payload))
            pipe.zadd(
                GLOBAL_READY_TASKS_KEY,
                {_global_task_member(self.run_id, task.task_id): task_score},
            )
        pipe.hset(
            self.key("meta"),
            mapping={
                "total_tasks": len(tasks),
                "pending_tasks": len(tasks),
                "task_queue_type": "sorted_set",
                "updated_at": int(time.time()),
            },
        )
        pipe.execute()

    def status(self) -> dict[str, Any]:
        meta = self.client.hgetall(self.key("meta"))
        return {
            "run_id": self.run_id,
            "meta": meta,
            "pending_tasks": _int(meta.get("pending_tasks"), 0),
            "processing_tasks": _int(meta.get("running_tasks"), 0),
            "completed_tasks": self.client.scard(self.key("tasks:completed")),
            "failed_tasks": self.client.scard(self.key("tasks:failed")),
            "api_incomplete_tasks": self.client.scard(
                self.key("tasks:api_incomplete")
            ),
            "infra_incomplete_tasks": self.client.scard(
                self.key("tasks:infra_incomplete")
            ),
            "available_instances": self.client.llen(self.key("instances:available")),
            "retained_instances": self.retained_instances(),
            "leased_instances": self.client.zcard(self.key("instances:leased")),
            "quarantined_instances": self.client.scard(self.key("instances:quarantine")),
            "terminating_instances": self.client.scard(self.key("instances:terminating")),
            "terminated_instances": self.client.scard(self.key("instances:terminated")),
            "run_terminal": self.is_run_terminal(),
            "completion_signal": self.run_completion_signal(),
            "task_source_key": self.task_source_key(),
            "task_source_present": bool(self.client.exists(self.task_source_key())),
            "vm_osworld": self.vm_osworld_settings(),
            "global_vm_capacity": self.global_vm_capacity(),
        }

    def replacement_demand_by_snapshot(self) -> dict[str, int]:
        """Return missing VM counts without replacing capacity for finished tasks."""

        meta = self.client.hgetall(self.key("meta"))
        allocation = _json_object(meta.get("allocation"))
        remaining: dict[str, int] = defaultdict(int)
        for task_id in self.client.hkeys(self.key("tasks:payload")):
            status = self.client.hget(self.key(f"task:{task_id}"), "status")
            if status not in {"pending", "leased", "running"}:
                continue
            payload = self.client.hget(self.key("tasks:payload"), task_id)
            if not payload:
                continue
            task = _task_from_json(payload)
            remaining[str(task.metadata.get("snapshot", "default"))] += 1

        active: dict[str, int] = defaultdict(int)
        for instance_id in self.active_instance_ids():
            raw = self.client.hgetall(self.key(f"instance:{instance_id}"))
            if raw.get("status") in {"terminating", "terminated", "retained"}:
                continue
            metadata = json.loads(raw.get("metadata") or "{}")
            active[str(metadata.get("snapshot", "default"))] += 1

        demand = {}
        for snapshot, target in allocation.items():
            desired = min(_int(target, 0), remaining.get(snapshot, 0))
            missing = max(0, desired - active.get(snapshot, 0))
            if missing:
                demand[snapshot] = missing
        return demand

    def replacement_sources_for_demand(
        self,
        demand_by_snapshot: dict[str, int],
    ) -> list[dict[str, Any]]:
        """Build launch requests from the most recent known instance per snapshot."""

        templates: dict[str, dict[str, Any]] = {}
        for instance_id in reversed(self.all_instance_ids()):
            raw = self.client.hgetall(self.key(f"instance:{instance_id}"))
            if not raw:
                continue
            metadata = json.loads(raw.get("metadata") or "{}")
            snapshot = str(metadata.get("snapshot", "default"))
            if snapshot in templates or not metadata.get("image_id"):
                continue
            templates[snapshot] = self._terminating_instance_info(
                instance_id,
                raw,
                reason="replacement required for pending task",
            )

        initial_templates = _json_object(self.client.hget(self.key("meta"), "launch_templates"))
        for snapshot, template in initial_templates.items():
            templates.setdefault(snapshot, template)
        sources = []
        for snapshot, count in demand_by_snapshot.items():
            template = templates.get(snapshot)
            if template:
                sources.extend(dict(template) for _ in range(count))
        return sources

    def api_incomplete_base_task_ids(self) -> list[str]:
        """Return stable task ids that can be selected into a new retry run."""
        return self._incomplete_base_task_ids("api_incomplete")

    def infra_incomplete_base_task_ids(self) -> list[str]:
        """Return infrastructure-incomplete task ids for a clean retry run."""
        return self._incomplete_base_task_ids("infra_incomplete")

    def _incomplete_base_task_ids(self, category: str) -> list[str]:
        base_task_ids = []
        for task_id in sorted(self.client.smembers(self.key(f"tasks:{category}"))):
            raw_payload = self.client.hget(self.key("tasks:payload"), task_id)
            if not raw_payload:
                continue
            try:
                payload = json.loads(raw_payload)
            except json.JSONDecodeError:
                continue
            metadata = payload.get("metadata") or {}
            base_task_id = metadata.get("base_task_id") or task_id.rsplit("@", 1)[0]
            base_task_ids.append(str(base_task_id))
        return sorted(set(base_task_ids))

    def all_instance_ids(self) -> list[str]:
        return sorted(self.client.smembers(self.key("instances:all")))

    def active_instance_ids(self) -> list[str]:
        ids = []
        for instance_id in self.all_instance_ids():
            status = self.client.hget(self.key(f"instance:{instance_id}"), "status")
            if status != "terminated":
                ids.append(instance_id)
        return ids

    def retained_instances(self) -> list[dict[str, str]]:
        return [raw for instance_id in self.all_instance_ids()
                if (raw := self.client.hgetall(self.key(f"instance:{instance_id}"))).get("status") == "retained"]

    def cleanup_instance_ids(self) -> list[str]:
        return [instance_id for instance_id in self.active_instance_ids()
                if self.client.hget(self.key(f"instance:{instance_id}"), "status") != "retained"]

    def retain_failed_instances_enabled(self) -> bool:
        return self.client.hget(self.key("meta"), "retain_failed_instances") == "true"

    def retain_api_incomplete_instances_enabled(self) -> bool:
        return (
            self.client.hget(
                self.key("meta"), "retain_api_incomplete_instances"
            )
            == "true"
        )

    def retain_instance(self, instance_id: str, reason: str) -> None:
        key = self.key(f"instance:{instance_id}")
        raw = self.client.hgetall(key)
        snapshot = json.loads(raw.get("metadata") or "{}").get("snapshot", "default")
        self.client.zrem(self.key("instances:leased"), instance_id)
        self.client.srem(self.key("instances:terminating"), instance_id)
        self.client.lrem(self.key("instances:available"), 0, instance_id)
        self.client.lrem(self.key(f"instances:available:{snapshot}"), 0, instance_id)
        if raw.get("status") == "available":
            self.client.hincrby(self.key("meta"), "available_instance_count", -1)
        self.client.hset(key, mapping={"status": "retained", "instance_id": instance_id, "last_error": reason,
                                     "lease_deadline_ts": "", "retained_at": int(time.time())})

    def claim_task(self, worker_id: str, lease_ttl_seconds: int) -> TaskSpec | None:
        claimed = self._claim_from_global_ready(
            worker_id=worker_id,
            lease_ttl_seconds=lease_ttl_seconds,
            run_id_filter=self.run_id,
        )
        return claimed[1] if claimed else None

    def claim_any_task(
        self,
        worker_id: str,
        lease_ttl_seconds: int,
    ) -> tuple[str, TaskSpec] | None:
        return self._claim_from_global_ready(
            worker_id=worker_id,
            lease_ttl_seconds=lease_ttl_seconds,
            run_id_filter=None,
        )

    def peek_ready_task_ref(self, run_id_filter: str | None = None) -> tuple[str, str] | None:
        refs = self.client.zrange(GLOBAL_READY_TASKS_KEY, 0, 99)
        for member in refs:
            ref = _global_task_ref(member)
            if ref is None:
                continue
            run_id, task_id = ref
            if run_id_filter and run_id != run_id_filter:
                continue
            return run_id, task_id
        return None

    def _claim_from_global_ready(
        self,
        worker_id: str,
        lease_ttl_seconds: int,
        run_id_filter: str | None = None,
    ) -> tuple[str, TaskSpec] | None:
        lock = self.acquire_global_lock(
            "claim_task",
            ttl_seconds=CLAIM_LOCK_TTL_SECONDS,
            owner=worker_id,
        )
        if lock is None:
            return None
        try:
            refs = self.client.zrange(GLOBAL_READY_TASKS_KEY, 0, 99)
            for member in refs:
                ref = _global_task_ref(member)
                if ref is None:
                    self.client.zrem(GLOBAL_READY_TASKS_KEY, member)
                    continue

                run_id, task_id = ref
                if run_id_filter and run_id != run_id_filter:
                    continue

                run_store = RedisStore(self.redis_url, run_id, client=self.client)
                if not run_store.is_claimable_run():
                    self.client.zrem(GLOBAL_READY_TASKS_KEY, member)
                    continue

                task = run_store.claim_task_by_id(
                    task_id,
                    worker_id=worker_id,
                    lease_ttl_seconds=lease_ttl_seconds,
                    ready_member=member,
                )
                if task is not None:
                    return run_id, task
                if self.client.zscore(GLOBAL_READY_TASKS_KEY, member) is not None:
                    return None
            return None
        finally:
            self.release_global_lock("claim_task", lock)

    def is_claimable_run(self) -> bool:
        meta = self.client.hgetall(self.key("meta"))
        if not meta:
            return False
        if meta.get("status") in {RunStatus.COMPLETED.value, RunStatus.FAILED.value}:
            return False
        if meta.get("completion_signal") == RunStatus.COMPLETED.value:
            return False
        return True

    def claim_task_by_id(
        self,
        task_id: str,
        worker_id: str,
        lease_ttl_seconds: int,
        ready_member: str | None = None,
    ) -> TaskSpec | None:
        ready_member = ready_member or _global_task_member(self.run_id, task_id)
        lock = self.acquire_lock(
            "claim_task",
            ttl_seconds=CLAIM_LOCK_TTL_SECONDS,
            owner=worker_id,
        )
        if lock is None:
            return None
        try:
            payload = self.client.hget(self.key("tasks:payload"), task_id)
            raw_task = self.client.hgetall(self.key(f"task:{task_id}"))
            if payload is None or not raw_task:
                self.client.zrem(GLOBAL_READY_TASKS_KEY, ready_member)
                return None

            if raw_task.get("status") != "pending":
                self.client.zrem(GLOBAL_READY_TASKS_KEY, ready_member)
                return None

            preferred_worker_host = (
                raw_task.get("preferred_worker_host")
                or raw_task.get("retained_worker_host")
                or ""
            )
            if preferred_worker_host and preferred_worker_host not in worker_id:
                return None

            now = int(time.time())
            deadline = now + lease_ttl_seconds
            pipe = self.client.pipeline()
            pipe.zrem(GLOBAL_READY_TASKS_KEY, ready_member)
            pipe.hincrby(self.key(f"task:{task_id}"), "attempt", 1)
            pipe.hset(
                self.key(f"task:{task_id}"),
                mapping={
                    "status": "leased",
                    "worker_id": worker_id,
                    "lease_deadline_ts": deadline,
                    "started_at": now,
                    "updated_at": now,
                },
            )
            pipe.hdel(
                self.key(f"task:{task_id}"), LEDGER_FIELD, "user_active_time_ledger",
                "user_paused", "user_paused_at", "runtime_phase", "evaluation_status",
                "failure_reason_code", "scoring_basis", "native_evaluator_executed",
            )
            pipe.zadd(self.key("tasks:processing"), {task_id: deadline})
            pipe.hincrby(self.key("meta"), "pending_tasks", -1)
            pipe.hincrby(self.key("meta"), "running_tasks", 1)
            result = pipe.execute()
            attempt = int(result[1])

            task = _task_from_json(payload)
            task.metadata["attempt"] = attempt
            task.metadata["run_id"] = self.run_id
            return task
        finally:
            self.release_lock("claim_task", lock)

    def claim_instance(
        self,
        worker_id: str,
        task_id: str,
        lease_ttl_seconds: int,
    ) -> InstanceRecord | None:
        task_payload = self.client.hget(self.key("tasks:payload"), task_id)
        if task_payload is None:
            raise KeyError(f"Task payload missing for task_id={task_id}")
        task = _task_from_json(task_payload)
        snapshot = str(task.metadata["snapshot"])

        lock = self.acquire_lock(
            f"claim_instance:{snapshot}",
            ttl_seconds=CLAIM_LOCK_TTL_SECONDS,
            owner=worker_id,
        )
        if lock is None:
            return None
        try:
            task_key = self.key(f"task:{task_id}")
            preferred_instance_id = (
                self.client.hget(task_key, "preferred_instance_id")
                or self.client.hget(task_key, "retained_instance_id")
            )
            if preferred_instance_id:
                raw_instance = self.client.hgetall(
                    self.key(f"instance:{preferred_instance_id}")
                )
                if not raw_instance or raw_instance.get("status") != "available":
                    return None
                instance = self._load_instance(preferred_instance_id)
                if instance is None:
                    raise KeyError(
                        "Preferred instance metadata missing for "
                        f"instance_id={preferred_instance_id}"
                    )
                instance_snapshot = str(
                    raw_instance.get("snapshot")
                    or instance.metadata.get("snapshot")
                    or ""
                )
                if instance_snapshot != snapshot:
                    raise ValueError(
                        f"Preferred instance {preferred_instance_id} uses snapshot "
                        f"{instance_snapshot!r}, expected {snapshot!r}"
                    )
                removed = self.client.lrem(
                    self.key(f"instances:available:{snapshot}"),
                    0,
                    preferred_instance_id,
                )
                if not removed:
                    return None
                instance_id = preferred_instance_id
            else:
                instance_id = self.client.lpop(
                    self.key(f"instances:available:{snapshot}")
                )
                if instance_id is None:
                    return None

            self.client.lrem(self.key("instances:available"), 0, instance_id)
            now = int(time.time())
            deadline = now + lease_ttl_seconds
            self.client.hset(
                self.key(f"instance:{instance_id}"),
                mapping={
                    "status": "leased",
                    "worker_id": worker_id,
                    "task_id": task_id,
                    "lease_deadline_ts": deadline,
                    "updated_at": now,
                },
            )
            self.client.hset(
                task_key,
                mapping={
                    "status": "running",
                    "instance_id": instance_id,
                    "preferred_instance_id": "",
                    "preferred_worker_host": "",
                    "updated_at": now,
                },
            )
            self.client.zadd(self.key("instances:leased"), {instance_id: deadline})
            self.client.hincrby(self.key("meta"), "available_instance_count", -1)
            instance = self._load_instance(instance_id)
            if instance is None:
                raise KeyError(f"Instance metadata missing for instance_id={instance_id}")
            return instance
        finally:
            self.release_lock(f"claim_instance:{snapshot}", lock)

    def complete_task_and_release_instance(
        self,
        task: TaskSpec,
        instance: InstanceRecord,
        worker_id: str,
        score: float | None,
        artifact_uri: str | None = None,
        error: str | None = None,
        error_category: str | None = None,
        quarantine_instance: bool = False,
        recycle_instance: bool = False,
    ) -> dict[str, Any]:
        lock_name = f"complete_task:{task.task_id}"
        lock = self.acquire_lock(
            lock_name,
            ttl_seconds=TASK_MUTATION_LOCK_TTL_SECONDS,
            owner=worker_id,
        )
        if lock is None:
            raise RuntimeError(f"Could not acquire completion lock for {task.task_id}")
        try:
            now = int(time.time())
            task_key = self.key(f"task:{task.task_id}")
            instance_key = self.key(f"instance:{instance.instance_id}")
            raw_task = self.client.hgetall(task_key)
            if raw_task.get("worker_id") != worker_id or raw_task.get("instance_id") not in {
                "",
                instance.instance_id,
            }:
                return {
                    "accepted": False,
                    "reason": "task ownership lost",
                    "task_id": task.task_id,
                }

            raw_instance = self.client.hgetall(instance_key)
            if raw_instance.get("worker_id") != worker_id:
                return {
                    "accepted": False,
                    "reason": "instance ownership lost",
                    "task_id": task.task_id,
                    "instance_id": instance.instance_id,
                }

            attempt = _int(raw_task.get("attempt"), int(task.metadata.get("attempt", 0) or 0))
            max_attempts = _int(raw_task.get("max_attempts"), task.max_attempts)
            from engiworld.scheduler.error_policy import classify_task_error
            from engiworld.scheduler.model_action_outcome import ALT_F4_CATEGORY, ALT_F4_REASON
            error_category = classify_task_error(error, error_category)
            if error and error_category == ALT_F4_CATEGORY:
                score = 0.0
            is_api_incomplete = bool(error) and error_category == "model_api"
            is_infra_incomplete = bool(error) and error_category == "infra"
            is_model_environment_failure = (
                bool(error) and error_category == ALT_F4_CATEGORY
            )
            will_retry = (
                bool(error)
                and not is_api_incomplete
                and not is_infra_incomplete
                and not is_model_environment_failure
                and attempt < max_attempts
            )

            task_mapping = {
                "worker_id": worker_id,
                "instance_id": instance.instance_id,
                "updated_at": now,
            }
            if not is_api_incomplete and not is_infra_incomplete:
                task_mapping["score"] = score
            else:
                self.client.hdel(task_key, "score")
            if artifact_uri:
                task_mapping["artifact_uri"] = artifact_uri
            if is_model_environment_failure:
                task_mapping.update({"evaluation_status": "completed", "failure_reason": ALT_F4_REASON, "failure_reason_code": ALT_F4_CATEGORY, "scoring_basis": "model_action_causal_evidence", "native_evaluator_executed": "false", "reviewed_no_retry": "1", "reviewed_attempt": str(attempt)})

            self.client.zrem(self.key("tasks:processing"), task.task_id)
            self.client.hincrby(self.key("meta"), "running_tasks", -1)
            if error:
                task_mapping["error_message"] = error
                task_mapping["last_error"] = error
                task_mapping["error_category"] = error_category or "task"

            if not error or is_model_environment_failure:
                task_mapping.update({"status": "completed", "finished_at": now})
                self.client.hset(task_key, mapping=task_mapping)
                if not error:
                    self.client.hdel(
                        task_key,
                        "error_message",
                        "last_error",
                        "last_requeue_reason",
                        "error_category",
                    )
                self.client.sadd(self.key("tasks:completed"), task.task_id)
                self.client.hincrby(self.key("meta"), "completed_tasks", 1)
                task_status = "completed"
            elif is_api_incomplete:
                task_mapping.update({"status": "api_incomplete", "finished_at": now})
                self.client.hset(task_key, mapping=task_mapping)
                self.client.sadd(self.key("tasks:api_incomplete"), task.task_id)
                self.client.hincrby(self.key("meta"), "api_incomplete_tasks", 1)
                task_status = "api_incomplete"
            elif is_infra_incomplete:
                task_mapping.update({"status": "infra_incomplete", "finished_at": now})
                self.client.hset(task_key, mapping=task_mapping)
                self.client.sadd(self.key("tasks:infra_incomplete"), task.task_id)
                self.client.hincrby(self.key("meta"), "infra_incomplete_tasks", 1)
                task_status = "infra_incomplete"
            elif will_retry:
                retry_score = int(time.time() * 1000)
                task_mapping.update(
                    {
                        "status": "pending",
                        "worker_id": "",
                        "instance_id": "",
                        "lease_deadline_ts": "",
                        "started_at": "",
                        "last_requeue_reason": error,
                    }
                )
                self.client.hset(task_key, mapping=task_mapping)
                self.client.hdel(task_key, "finished_at")
                self.client.zadd(
                    GLOBAL_READY_TASKS_KEY,
                    {_global_task_member(self.run_id, task.task_id): retry_score},
                )
                self.client.hincrby(self.key("meta"), "pending_tasks", 1)
                task_status = "pending"
            else:
                task_mapping.update({"status": "failed", "finished_at": now})
                self.client.hset(task_key, mapping=task_mapping)
                self.client.sadd(self.key("tasks:failed"), task.task_id)
                self.client.hincrby(self.key("meta"), "failed_tasks", 1)
                task_status = "failed"

            self.client.zrem(self.key("instances:leased"), instance.instance_id)
            snapshot = str(instance.metadata.get("snapshot", task.metadata.get("snapshot", "default")))
            retain_instance = (
                error
                and not is_model_environment_failure
                and (
                    self.retain_failed_instances_enabled()
                    or (
                        is_api_incomplete
                        and self.retain_api_incomplete_instances_enabled()
                    )
                )
            )
            if retain_instance:
                self.retain_instance(instance.instance_id, error)
                instance_status = "retained"
                recycle_instance = False
            elif quarantine_instance:
                instance_status = "quarantined"
                self.client.sadd(self.key("instances:quarantine"), instance.instance_id)
                self.client.hset(
                    self.key(f"instance:{instance.instance_id}"),
                    mapping={
                        "status": "quarantined",
                        "worker_id": worker_id,
                        "task_id": task.task_id,
                        "updated_at": now,
                        "last_error": error or "quarantined by worker",
                    },
                )
            elif recycle_instance:
                instance_status = "terminating"
                self.client.lrem(self.key("instances:available"), 0, instance.instance_id)
                self.client.lrem(self.key(f"instances:available:{snapshot}"), 0, instance.instance_id)
                self.client.sadd(self.key("instances:terminating"), instance.instance_id)
                self.client.hset(
                    self.key(f"instance:{instance.instance_id}"),
                    mapping={
                        "status": "terminating",
                        "worker_id": "",
                        "task_id": "",
                        "lease_deadline_ts": "",
                        "updated_at": now,
                        "last_error": error
                        or f"task finished; recycling instance; task_id={task.task_id}",
                    },
                )
            else:
                instance_status = "available"
                self.client.hset(
                    self.key(f"instance:{instance.instance_id}"),
                    mapping={
                        "status": "available",
                        "worker_id": "",
                        "task_id": "",
                        "lease_deadline_ts": "",
                        "updated_at": now,
                    },
                )
                self.client.lpush(self.key("instances:available"), instance.instance_id)
                self.client.lpush(self.key(f"instances:available:{snapshot}"), instance.instance_id)
                self.client.hincrby(self.key("meta"), "available_instance_count", 1)
            return {
                "accepted": True,
                "task_id": task.task_id,
                "task_status": task_status,
                "will_retry": will_retry,
                "attempt": attempt,
                "max_attempts": max_attempts,
                "error_category": error_category,
                "instance_id": instance.instance_id,
                "instance_status": instance_status,
                "recycle_instance": recycle_instance,
            }
        finally:
            self.release_lock(lock_name, lock)

    def requeue_claimed_task(self, task: TaskSpec, worker_id: str, reason: str) -> None:
        lock_name = f"requeue_task:{task.task_id}"
        lock = self.acquire_lock(
            lock_name,
            ttl_seconds=TASK_MUTATION_LOCK_TTL_SECONDS,
            owner=worker_id,
        )
        if lock is None:
            raise RuntimeError(f"Could not acquire requeue lock for {task.task_id}")
        try:
            now = int(time.time())
            retry_score = int(time.time() * 1000)
            task_key = self.key(f"task:{task.task_id}")
            if self.client.hget(task_key, "retained_instance_id"):
                first = self.client.zrange(
                    GLOBAL_READY_TASKS_KEY, 0, 0, withscores=True
                )
                if first:
                    retry_score = int(first[0][1]) - 1
            self.client.zrem(self.key("tasks:processing"), task.task_id)
            self.client.zadd(
                GLOBAL_READY_TASKS_KEY,
                {_global_task_member(self.run_id, task.task_id): retry_score},
            )
            self.client.hset(
                task_key,
                mapping={
                    "status": "pending",
                    "worker_id": "",
                    "lease_deadline_ts": "",
                    "updated_at": now,
                    "last_requeue_reason": reason,
                },
            )
            current_attempt = int(self.client.hget(self.key(f"task:{task.task_id}"), "attempt") or 0)
            if current_attempt > 0:
                self.client.hincrby(self.key(f"task:{task.task_id}"), "attempt", -1)
            self.client.hincrby(self.key("meta"), "running_tasks", -1)
            self.client.hincrby(self.key("meta"), "pending_tasks", 1)
        finally:
            self.release_lock(lock_name, lock)

    def requeue_expired_leases(
        self,
        now: int | None = None,
        task_run_timeout_seconds: int = 5 * 60 * 60,
        lock_ttl_seconds: int = 60,
    ) -> dict[str, Any]:
        now = now or int(time.time())
        lock = self.acquire_lock("reconcile", ttl_seconds=lock_ttl_seconds)
        if lock is None:
            return {"lock_acquired": False, "message": "another reconcile is running"}

        report: dict[str, Any] = {
            "lock_acquired": True,
            "checked_processing_tasks": 0,
            "requeued_tasks": 0,
            "failed_tasks": 0,
            "completed_tasks": 0,
            "instances_to_terminate": [],
            "timed_out_tasks": [],
            "lease_expired_tasks": [],
        }
        try:
            task_ids = self.client.zrange(self.key("tasks:processing"), 0, -1)
            report["checked_processing_tasks"] = len(task_ids)
            for task_id in task_ids:
                task_lock_name = f"complete_task:{task_id}"
                task_lock = self.acquire_lock(task_lock_name, ttl_seconds=TASK_MUTATION_LOCK_TTL_SECONDS)
                if task_lock is None:
                    continue
                try:
                    raw = self.client.hgetall(self.key(f"task:{task_id}"))
                    if raw.get("status") not in {"leased", "running"}:
                        continue
                    lease_deadline = _int(raw.get("lease_deadline_ts"), 0)
                    lease_expired = bool(lease_deadline and lease_deadline <= now)
                    timing = active_time_metrics(raw, now)
                    run_timed_out = bool(
                        task_run_timeout_seconds > 0 and raw.get("started_at")
                        and timing["active_duration_seconds"] >= task_run_timeout_seconds
                    )
                    if not lease_expired and not run_timed_out:
                        continue
                    # A lost worker lease is infrastructure loss, not proof that
                    # a model actually used its whole active-time budget.
                    if lease_expired:
                        reason = "task lease expired"
                        task_result = self._retry_or_fail_processing_task(task_id, raw, reason, now)
                        report["lease_expired_tasks"].append(task_id)
                    else:
                        reason = f"task active-time budget exhausted after {task_run_timeout_seconds}s"
                        self._complete_active_time_budget(task_id, timing, now, task_run_timeout_seconds)
                        task_result = "completed"
                        report["timed_out_tasks"].append(task_id)
                    report[f"{task_result}_tasks"] += 1
                    instance_id = raw.get("instance_id") or ""
                    if instance_id:
                        instance_info = self.mark_instance_terminating(
                            instance_id, reason=f"{reason}; task_id={task_id}", now=now,
                        )
                        if instance_info:
                            report["instances_to_terminate"].append(instance_info)
                finally:
                    self.release_lock(task_lock_name, task_lock)
            return report
        finally:
            self.release_lock("reconcile", lock)

    def _complete_active_time_budget(self, task_id, timing, now, limit):
        """Called under the same task lock used by pause and worker completion."""
        task_key = self.key(f"task:{task_id}")
        outcome = budget_outcome()
        outcome["native_evaluator_executed"] = "false"
        pipe = self.client.pipeline()
        pipe.hset(task_key, mapping={
            **outcome, **timing, "status": "completed", "finished_at": now,
            "updated_at": now, "worker_id": "", "lease_deadline_ts": "",
            "active_time_limit_seconds": limit,
        })
        pipe.hdel(task_key, "error_message", "last_error", "error_category", "last_requeue_reason")
        pipe.zrem(self.key("tasks:processing"), task_id)
        pipe.sadd(self.key("tasks:completed"), task_id)
        pipe.hincrby(self.key("meta"), "running_tasks", -1)
        pipe.hincrby(self.key("meta"), "completed_tasks", 1)
        pipe.execute()

    def pending_terminating_instances(self) -> list[dict[str, Any]]:
        instances = []
        for instance_id in sorted(self.client.smembers(self.key("instances:terminating"))):
            raw = self.client.hgetall(self.key(f"instance:{instance_id}"))
            if not raw or raw.get("status") != "terminating":
                continue
            instances.append(
                self._terminating_instance_info(
                    instance_id,
                    raw,
                    reason=raw.get("last_error", "instance recycle requested"),
                )
            )
        return instances

    def mark_instance_terminating(
        self,
        instance_id: str,
        reason: str,
        now: int | None = None,
    ) -> dict[str, Any] | None:
        now = now or int(time.time())
        raw = self.client.hgetall(self.key(f"instance:{instance_id}"))
        if not raw:
            return None
        status = raw.get("status", "")
        if status in {"terminating", "terminated", "retained"}:
            return None

        if self.retain_failed_instances_enabled():
            self.retain_instance(instance_id, reason)
            return None

        metadata = json.loads(raw.get("metadata") or "{}")
        snapshot = str(metadata.get("snapshot", "default"))
        self.client.zrem(self.key("instances:leased"), instance_id)
        self.client.lrem(self.key("instances:available"), 0, instance_id)
        self.client.lrem(self.key(f"instances:available:{snapshot}"), 0, instance_id)
        if status == "available":
            self.client.hincrby(self.key("meta"), "available_instance_count", -1)
        self.client.sadd(self.key("instances:terminating"), instance_id)
        self.client.hset(
            self.key(f"instance:{instance_id}"),
            mapping={
                "status": "terminating",
                "worker_id": "",
                "task_id": "",
                "lease_deadline_ts": "",
                "updated_at": now,
                "last_error": reason,
            },
        )
        return self._terminating_instance_info(instance_id, raw, reason)

    def _terminating_instance_info(
        self,
        instance_id: str,
        raw: dict[str, str],
        reason: str,
    ) -> dict[str, Any]:
        metadata = json.loads(raw.get("metadata") or "{}")
        snapshot = str(metadata.get("snapshot", "default"))
        return {
            "instance_id": instance_id,
            "snapshot": snapshot,
            "os_type": raw.get("os_type", "Ubuntu"),
            "image_id": metadata.get("image_id", ""),
            "image_name": metadata.get("image_name", snapshot),
            "image_visibility": metadata.get("image_visibility", ""),
            "image_os_type": metadata.get("image_os_type", raw.get("os_type", "")),
            "system_disk_size_gb": metadata.get("system_disk_size_gb", ""),
            "reason": reason,
        }

    def mark_instances_terminated(
        self,
        instance_ids: list[str],
        reason: str = "terminated by master",
        now: int | None = None,
    ) -> None:
        now = now or int(time.time())
        pipe = self.client.pipeline()
        terminated_count = 0
        for instance_id in instance_ids:
            raw = self.client.hgetall(self.key(f"instance:{instance_id}"))
            if not raw:
                continue
            status = raw.get("status", "")
            metadata = json.loads(raw.get("metadata") or "{}")
            snapshot = str(metadata.get("snapshot", "default"))
            if status == "available":
                pipe.hincrby(self.key("meta"), "available_instance_count", -1)
            if status != "terminated":
                terminated_count += 1
            pipe.zrem(self.key("instances:leased"), instance_id)
            pipe.lrem(self.key("instances:available"), 0, instance_id)
            pipe.lrem(self.key(f"instances:available:{snapshot}"), 0, instance_id)
            pipe.srem(self.key("instances:quarantine"), instance_id)
            pipe.srem(self.key("instances:terminating"), instance_id)
            pipe.sadd(self.key("instances:terminated"), instance_id)
            pipe.hset(
                self.key(f"instance:{instance_id}"),
                mapping={
                    "status": "terminated",
                    "worker_id": "",
                    "task_id": "",
                    "lease_deadline_ts": "",
                    "terminated_at": now,
                    "updated_at": now,
                    "last_error": reason,
                },
            )
        if terminated_count:
            pipe.hincrby(self.key("meta"), "terminated_instance_count", terminated_count)
        pipe.execute()

    def is_run_terminal(self) -> bool:
        meta = self.client.hgetall(self.key("meta"))
        total = _int(meta.get("total_tasks"), 0)
        if total <= 0:
            return False
        pending = _int(meta.get("pending_tasks"), 0)
        running = _int(meta.get("running_tasks"), 0)
        completed = self.client.scard(self.key("tasks:completed"))
        failed = self.client.scard(self.key("tasks:failed"))
        api_incomplete = self.client.scard(self.key("tasks:api_incomplete"))
        infra_incomplete = self.client.scard(self.key("tasks:infra_incomplete"))
        terminal = completed + failed + api_incomplete + infra_incomplete
        return terminal >= total and pending <= 0 and running <= 0

    def build_run_summary(self) -> dict[str, Any]:
        meta = self.client.hgetall(self.key("meta"))
        task_ids = sorted(self.client.hkeys(self.key("tasks:payload")))
        status_counts: dict[str, int] = defaultdict(int)
        domain_counts: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "api_incomplete": 0,
                "infra_incomplete": 0,
                "score_sum": 0.0,
            }
        )
        tasks = []
        for task_id in task_ids:
            raw = self.client.hgetall(self.key(f"task:{task_id}"))
            status = raw.get("status", "unknown")
            domain = raw.get("domain", "unknown")
            score = _float(raw.get("score"), 0.0)
            reported_score = (
                None
                if status in {"api_incomplete", "infra_incomplete"}
                else score
            )
            status_counts[status] += 1
            domain_counts[domain]["total"] += 1
            if status == "completed":
                domain_counts[domain]["completed"] += 1
                domain_counts[domain]["score_sum"] += score
            elif status == "failed":
                domain_counts[domain]["failed"] += 1
            elif status == "api_incomplete":
                domain_counts[domain]["api_incomplete"] += 1
            elif status == "infra_incomplete":
                domain_counts[domain]["infra_incomplete"] += 1
            started_at = _int(raw.get("started_at"), 0)
            finished_at = _int(raw.get("finished_at"), 0)
            tasks.append(
                {
                    "task_id": task_id,
                    "domain": domain,
                    "example_id": raw.get("example_id", ""),
                    "status": status,
                    "attempt": _int(raw.get("attempt"), 0),
                    "max_attempts": _int(raw.get("max_attempts"), 0),
                    "score": reported_score,
                    "artifact_uri": raw.get("artifact_uri", ""),
                    "error_message": raw.get("error_message", ""),
                    "error_category": raw.get("error_category", ""),
                    "evaluation_status": raw.get("evaluation_status", ""),
                    "failure_reason_code": raw.get("failure_reason_code", ""),
                    "scoring_basis": raw.get("scoring_basis", ""),
                    "native_evaluator_executed": raw.get("native_evaluator_executed", ""),
                    **active_time_metrics(raw, finished_at or time.time()),
                    "duration_seconds": finished_at - started_at
                    if started_at and finished_at
                    else None,
                }
            )

        domains = {}
        for domain, values in sorted(domain_counts.items()):
            completed = values["completed"]
            domains[domain] = {
                **values,
                "average_score": values["score_sum"] / completed if completed else 0.0,
            }

        summary = {
            "run_id": self.run_id,
            "status": meta.get("status", ""),
            "total_tasks": _int(meta.get("total_tasks"), len(task_ids)),
            "status_counts": dict(sorted(status_counts.items())),
            "completed_tasks": self.client.scard(self.key("tasks:completed")),
            "failed_tasks": self.client.scard(self.key("tasks:failed")),
            "api_incomplete_tasks": self.client.scard(
                self.key("tasks:api_incomplete")
            ),
            "infra_incomplete_tasks": self.client.scard(
                self.key("tasks:infra_incomplete")
            ),
            "pending_tasks": _int(meta.get("pending_tasks"), 0),
            "processing_tasks": _int(meta.get("running_tasks"), 0),
            "run_terminal": self.is_run_terminal(),
            "domains": domains,
            "tasks": tasks,
            "updated_at": int(time.time()),
        }
        return summary

    def save_run_summary(self, summary: dict[str, Any] | None = None) -> dict[str, Any]:
        summary = summary or self.build_run_summary()
        self.client.set(self.key("summary"), json.dumps(summary, ensure_ascii=False))
        self.client.hset(
            self.key("meta"),
            mapping={"summary_updated_at": int(time.time()), "updated_at": int(time.time())},
        )
        if summary.get("run_terminal"):
            self.expire_run_state()
        return summary

    def _load_instance(self, instance_id: str) -> InstanceRecord | None:
        raw = self.client.hgetall(self.key(f"instance:{instance_id}"))
        if not raw:
            return None
        metadata = json.loads(raw.get("metadata") or "{}")
        return InstanceRecord(
            instance_id=raw["instance_id"],
            private_ip=raw.get("private_ip", ""),
            public_ip=raw.get("public_ip") or None,
            os_type=raw.get("os_type", "Ubuntu"),
            metadata=metadata,
        )

    def _retry_or_fail_processing_task(
        self,
        task_id: str,
        raw: dict[str, str],
        reason: str,
        now: int,
    ) -> str:
        attempt = _int(raw.get("attempt"), 0)
        max_attempts = _int(raw.get("max_attempts"), 3)
        self.client.zrem(self.key("tasks:processing"), task_id)
        self.client.hincrby(self.key("meta"), "running_tasks", -1)
        if attempt < max_attempts:
            retry_score = int(time.time() * 1000)
            self.client.zadd(
                GLOBAL_READY_TASKS_KEY,
                {_global_task_member(self.run_id, task_id): retry_score},
            )
            self.client.hset(
                self.key(f"task:{task_id}"),
                mapping={
                    "status": "pending",
                    "worker_id": "",
                    "instance_id": "",
                    "lease_deadline_ts": "",
                    "started_at": "",
                    "updated_at": now,
                    "last_requeue_reason": reason,
                    "last_error": reason,
                },
            )
            self.client.hdel(self.key(f"task:{task_id}"), "finished_at")
            self.client.hincrby(self.key("meta"), "pending_tasks", 1)
            return "requeued"

        self.client.hset(
            self.key(f"task:{task_id}"),
            mapping={
                "status": "failed",
                "worker_id": "",
                "lease_deadline_ts": "",
                "finished_at": now,
                "updated_at": now,
                "error_message": reason,
                "last_error": reason,
            },
        )
        self.client.sadd(self.key("tasks:failed"), task_id)
        self.client.hincrby(self.key("meta"), "failed_tasks", 1)
        return "failed"


def _task_from_json(payload: str) -> TaskSpec:
    raw = json.loads(payload)
    return TaskSpec(
        task_id=raw["task_id"],
        domain=raw["domain"],
        example_id=raw["example_id"],
        max_attempts=int(raw.get("max_attempts", 3)),
        metadata=raw.get("metadata") or {},
    )


def _task_payload_for_run(run_id: str, task: TaskSpec) -> dict[str, Any]:
    payload = asdict(task)
    metadata = dict(task.metadata)
    metadata["run_id"] = run_id
    payload["metadata"] = metadata
    payload["run_id"] = run_id
    return payload


def _global_task_member(run_id: str, task_id: str) -> str:
    return json.dumps(
        {"run_id": run_id, "task_id": task_id},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _global_task_ref(member: str) -> tuple[str, str] | None:
    try:
        raw = json.loads(member)
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    run_id = str(raw.get("run_id") or "")
    task_id = str(raw.get("task_id") or "")
    if not run_id or not task_id:
        return None
    return run_id, task_id


def _json_object(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
