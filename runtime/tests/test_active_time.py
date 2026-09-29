import contextlib
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from engiworld.active_time import (
    ActiveTaskDeadline, ActiveTimeBudgetExceeded, BUDGET_EXHAUSTED,
    PauseTrackingError, active_time_metrics, pause_mapping, task_paused, track_task_pauses,
)
from engiworld.agents.openai_compatible import OpenAICompatibleEndpoint, _wait_for_endpoint_change
from engiworld.scheduler.redis_store import RedisStore
from engiworld.scheduler.schemas import TaskSpec
from test_api_incomplete import MemoryRedis


def running_task():
    return {"status": "running", "started_at": "1000", "attempt": "1",
            "instance_id": "i-1", "worker_id": "w-1", "max_attempts": "3",
            "lease_deadline_ts": "99999"}


def test_multiple_overlapping_pauses_and_resume_preserve_original_start():
    raw = running_task()
    raw.update(pause_mapping(raw, "api", True, 1100))
    raw.update(pause_mapping(raw, "manual", True, 1150))
    raw.update(pause_mapping(raw, "api", False, 1200))
    assert active_time_metrics(raw, 1250)["active_duration_seconds"] == 100
    raw.update(pause_mapping(raw, "manual", False, 1300))
    raw.update(pause_mapping(raw, "api", True, 1400))
    raw.update(pause_mapping(raw, "api", False, 1500))
    assert raw["started_at"] == "1000"
    assert active_time_metrics(raw, 1600) == {
        "wall_duration_seconds": 600, "paused_seconds": 300, "active_duration_seconds": 300,
    }


def test_legacy_main_experiment_ledger_and_duplicate_pause_are_counted_once():
    raw = running_task()
    raw.update(user_paused="1", user_paused_at="1200")
    raw["user_active_time_ledger"] = json.dumps({
        "attempt": "1", "instance_id": "i-1", "original_started_at": 1000,
        "closed": [{"start": 1050, "end": 1100}], "open": {"start": 1200},
    })
    raw.update(pause_mapping(raw, "api", True, 1200))
    assert active_time_metrics(raw, 1400)["paused_seconds"] == 250
    raw["attempt"] = "2"
    raw.pop("user_paused")
    assert active_time_metrics(raw, 1400)["paused_seconds"] == 0


def test_start_time_cannot_be_reset_to_extend_the_same_attempt():
    raw = running_task()
    raw.update(pause_mapping(raw, "api", True, 1100))
    raw["started_at"] = "1100"
    with pytest.raises(PauseTrackingError, match="start changed"):
        active_time_metrics(raw, 1300)


def test_nested_pause_and_exception_close_only_the_outer_interval():
    events = []
    with track_task_pauses(lambda reason, paused: events.append((reason, paused))):
        with pytest.raises(ValueError):
            with task_paused("manual"), task_paused("manual"):
                raise ValueError("interrupted pause")
    assert events == [("manual", True), ("manual", False)]


def test_api_hot_swap_pause_shorter_than_heartbeat_is_not_lost(monkeypatch):
    now = [1000.0]
    raw = running_task()
    monkeypatch.setattr(time, "monotonic", lambda: now[0])
    monkeypatch.setattr(time, "sleep", lambda seconds: now.__setitem__(0, now[0] + seconds))

    def record(reason, paused):
        raw.update(pause_mapping(raw, reason, paused, now[0]))

    endpoint = OpenAICompatibleEndpoint("http://test", "fake", "updated")
    with track_task_pauses(record):
        assert _wait_for_endpoint_change(lambda: endpoint, previous_revision="old",
                                        provider_name="test", wait_seconds=100,
                                        poll_seconds=5) is endpoint
    assert active_time_metrics(raw, 1010)["paused_seconds"] == 5


class TimingRedis(MemoryRedis):
    def pipeline(self):
        client = self
        commands = []

        class Pipeline:
            def __getattr__(self, name):
                def enqueue(*args, **kwargs):
                    commands.append((name, args, kwargs))
                    return self
                return enqueue

            def execute(self):
                return [getattr(client, name)(*args, **kwargs) for name, args, kwargs in commands]

        return Pipeline()

    def zrange(self, key, start, end):
        values = list(self.sorted_sets.get(key, {}))
        return values[start:] if end == -1 else values[start:end + 1]

    def zadd(self, key, mapping):
        self.sorted_sets.setdefault(key, {}).update(mapping)


def timing_store():
    client = TimingRedis()
    store = RedisStore("redis://unused", "test", client=client)
    store.acquire_lock = lambda *args, **kw: "lock"
    store.release_lock = lambda *args, **kw: True
    store.mark_instance_terminating = lambda *args, **kw: {"instance_id": "i-1"}
    client.hashes[store.key("task:t-1")] = running_task()
    client.sorted_sets[store.key("tasks:processing")] = {"t-1": 99999}
    client.hashes[store.key("meta")] = {"running_tasks": "1"}
    return store, client.hashes[store.key("task:t-1")]


def test_cloud_five_hours_excludes_pause_and_exhaustion_completes_without_retry():
    store, raw = timing_store()
    store.set_task_pause("t-1", "i-1", "w-1", 1, "manual", True, now=1100)
    store.set_task_pause("t-1", "i-1", "w-1", 1, "manual", False, now=4700)
    first = store.requeue_expired_leases(now=19000)
    assert first["timed_out_tasks"] == []  # Five wall hours, only four active hours.
    assert raw["status"] == "running"
    second = store.requeue_expired_leases(now=22600)
    assert second["completed_tasks"] == 1
    assert second["requeued_tasks"] == 0
    assert raw["status"] == "completed" and float(raw["score"]) == 0
    assert raw["failure_reason_code"] == BUDGET_EXHAUSTED
    assert raw["native_evaluator_executed"] == "false"
    assert float(raw["active_duration_seconds"]) == 18000
    assert raw["worker_id"] == ""  # A late worker result loses ownership.
    assert store.requeue_expired_leases(now=22601)["completed_tasks"] == 0


def test_ongoing_pause_does_not_exhaust_active_budget():
    store, raw = timing_store()
    store.set_task_pause("t-1", "i-1", "w-1", 1, "manual", True, now=1100)
    report = store.requeue_expired_leases(now=22600)
    assert not report["timed_out_tasks"]
    assert raw["status"] == "running"


def test_lost_lease_is_not_misclassified_as_model_budget_zero():
    store, raw = timing_store()
    raw["lease_deadline_ts"] = "2000"
    raw["max_attempts"] = "1"
    report = store.requeue_expired_leases(now=22600)
    assert report["lease_expired_tasks"] == ["t-1"]
    assert not report["timed_out_tasks"]
    assert raw["status"] == "failed"
    assert "score" not in raw


@pytest.mark.parametrize("worker,instance,attempt", [("stale", "i-1", 1), ("w-1", "old", 1), ("w-1", "i-1", 2)])
def test_pause_rejects_stale_worker_vm_or_attempt(worker, instance, attempt):
    store, raw = timing_store()
    with pytest.raises(PauseTrackingError):
        store.set_task_pause("t-1", instance, worker, attempt, "manual", True, now=1100)
    assert raw["started_at"] == "1000" and "active_time_ledger" not in raw


@pytest.mark.skipif(sys.platform != "linux", reason="Local evaluator uses Linux SIGALRM")
def test_real_deadline_excludes_pause_then_expires_during_active_wait():
    budget = ActiveTaskDeadline(0.3)
    with pytest.raises(ActiveTimeBudgetExceeded):
        with budget.running():
            with task_paused("manual"):
                time.sleep(0.4)  # Longer than the total budget, but paused.
            time.sleep(0.5)  # An ordinary wait remains active and must be interrupted.
    assert budget.metrics()["paused_seconds"] >= 0.4
    assert 0.29 <= budget.metrics()["active_duration_seconds"] < 0.5


@pytest.mark.parametrize("smoke", [False, True])
def test_local_budget_result_and_smoke_failure_have_different_classifications(tmp_path, monkeypatch, smoke):
    import engiworld.local_eval as local

    image = tmp_path / "test.qcow2"
    image.touch()
    task = TaskSpec("single-software/gui/example/task-01", "example", "task-01",
                    metadata={"os_type": "Ubuntu", "eval_mode": "gui"})
    monkeypatch.setattr(local, "preflight", lambda *a: task)
    monkeypatch.setattr(local.sys, "platform", "linux")
    exists = Path.exists
    monkeypatch.setattr(Path, "exists", lambda p: False if str(p).replace("\\", "/") == "/dev/kvm" else exists(p))
    monkeypatch.setenv("OPENAI_API_KEY", "fake")

    @contextlib.contextmanager
    def deadline(seconds):
        yield SimpleNamespace(metrics=lambda: {"active_duration_seconds": 18000,
                                               "paused_seconds": 3600, "wall_duration_seconds": 21600})

    def expired(*args, **kwargs):
        raise ActiveTimeBudgetExceeded("active budget used")

    monkeypatch.setattr(local, "task_deadline", deadline)
    monkeypatch.setattr(local, "run_single_task", expired)
    monkeypatch.setattr(local, "smoke_test", expired)
    args = ["--task", task.task_id, "--image", str(image), "--model", "test",
            "--result-dir", str(tmp_path / "results")]
    if smoke:
        args.append("--smoke-test")
    assert local.main(args) == int(smoke)
    path = next((tmp_path / "results").glob("*/summary.json"))
    summary = json.loads(path.read_text())
    assert summary["paused_seconds"] == 3600
    if smoke:
        assert summary["score"] is None and summary["error_category"] == "environment_timeout"
        assert not (path.parent / "evaluation.json").exists()
    else:
        assert summary["score"] == 0 and summary["error"] is None
        assert summary["failure_reason_code"] == BUDGET_EXHAUSTED
        assert summary["native_evaluator_executed"] is False
        assert json.loads((path.parent / "evaluation.json").read_text()) == summary
