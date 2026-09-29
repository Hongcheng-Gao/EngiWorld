import json
import unittest
from argparse import Namespace

from engiworld.scheduler.error_policy import MODEL_ENVIRONMENT_ERROR_CATEGORY
from engiworld.scheduler.master import _agent_settings_from_args
from engiworld.scheduler.redis_store import RedisStore
from engiworld.scheduler.schemas import InstanceRecord, TaskSpec


class MemoryRedis:
    def __init__(self):
        self.hashes = {}
        self.sets = {}
        self.sorted_sets = {}
        self.lists = {}

    def hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    def hget(self, key, field):
        return self.hashes.get(key, {}).get(field)

    def hset(self, key, mapping=None, **kwargs):
        target = self.hashes.setdefault(key, {})
        if mapping:
            target.update({name: str(value) for name, value in mapping.items()})

    def hdel(self, key, *fields):
        for field in fields:
            self.hashes.setdefault(key, {}).pop(field, None)

    def hincrby(self, key, field, amount):
        target = self.hashes.setdefault(key, {})
        target[field] = str(int(target.get(field, 0)) + amount)
        return int(target[field])

    def sadd(self, key, *values):
        self.sets.setdefault(key, set()).update(values)

    def smembers(self, key):
        return set(self.sets.get(key, set()))

    def scard(self, key):
        return len(self.sets.get(key, set()))

    def zrem(self, key, value):
        self.sorted_sets.setdefault(key, {}).pop(value, None)

    def lrem(self, key, count, value):
        self.lists[key] = [item for item in self.lists.get(key, []) if item != value]


class ApiIncompleteTest(unittest.TestCase):
    def setUp(self):
        self.client = MemoryRedis()
        self.store = RedisStore("redis://unused", "run-1", client=self.client)
        self.store.acquire_lock = lambda *args, **kwargs: "lock"
        self.store.release_lock = lambda *args, **kwargs: True

    def test_model_api_error_is_terminal_but_not_failed(self):
        task = TaskSpec(
            task_id="task-v/kicad/task-01@run-1",
            domain="task-v/kicad",
            example_id="task-01",
            metadata={"snapshot": "KiCad", "base_task_id": "task-v/kicad/task-01"},
        )
        instance = InstanceRecord(
            instance_id="i-1",
            private_ip="10.0.0.1",
            metadata={"snapshot": "KiCad"},
        )
        self.client.hashes[self.store.key(f"task:{task.task_id}")] = {
            "worker_id": "worker-1",
            "instance_id": "i-1",
            "attempt": "1",
            "max_attempts": "3",
        }
        self.client.hashes[self.store.key("instance:i-1")] = {"worker_id": "worker-1"}
        self.client.hashes[self.store.key("meta")] = {
            "total_tasks": "1",
            "pending_tasks": "0",
            "running_tasks": "1",
        }

        completion = self.store.complete_task_and_release_instance(
            task=task,
            instance=instance,
            worker_id="worker-1",
            score=0.0,
            error="API failed after 10 attempts",
            error_category="model_api",
            recycle_instance=True,
        )

        self.assertEqual(completion["task_status"], "api_incomplete")
        self.assertFalse(completion["will_retry"])
        self.assertEqual(self.client.scard(self.store.key("tasks:failed")), 0)
        self.assertEqual(self.client.scard(self.store.key("tasks:api_incomplete")), 1)
        self.assertNotIn(
            "score",
            self.client.hashes[self.store.key(f"task:{task.task_id}")],
        )
        self.assertTrue(self.store.is_run_terminal())

    def test_retry_selection_uses_stable_base_task_id(self):
        task_id = "task-v/kicad/task-01@run-1"
        self.client.sets[self.store.key("tasks:api_incomplete")] = {task_id}
        self.client.hashes[self.store.key("tasks:payload")] = {
            task_id: json.dumps(
                {"metadata": {"base_task_id": "task-v/kicad/task-01"}}
            )
        }

        self.assertEqual(
            self.store.api_incomplete_base_task_ids(),
            ["task-v/kicad/task-01"],
        )

    def test_infra_error_is_terminal_but_not_failed_or_retried(self):
        task = TaskSpec(
            task_id="task-c/freecad/task-01@run-1",
            domain="task-c/freecad",
            example_id="task-01",
            metadata={
                "snapshot": "FreeCAD0.21.2",
                "base_task_id": "task-c/freecad/task-01",
            },
        )
        instance = InstanceRecord(
            instance_id="i-infra",
            private_ip="10.0.0.2",
            metadata={"snapshot": "FreeCAD0.21.2"},
        )
        self.client.hashes[self.store.key(f"task:{task.task_id}")] = {
            "worker_id": "worker-1",
            "instance_id": "i-infra",
            "attempt": "1",
            "max_attempts": "3",
        }
        self.client.hashes[self.store.key("instance:i-infra")] = {
            "worker_id": "worker-1"
        }
        self.client.hashes[self.store.key("meta")] = {
            "total_tasks": "1",
            "pending_tasks": "0",
            "running_tasks": "1",
        }

        completion = self.store.complete_task_and_release_instance(
            task=task,
            instance=instance,
            worker_id="worker-1",
            score=None,
            error="sandbox permission error",
            error_category="infra",
            recycle_instance=True,
        )

        self.assertEqual(completion["task_status"], "infra_incomplete")
        self.assertFalse(completion["will_retry"])
        self.assertEqual(self.client.scard(self.store.key("tasks:failed")), 0)
        self.assertEqual(
            self.client.scard(self.store.key("tasks:infra_incomplete")), 1
        )
        self.assertNotIn(
            "score",
            self.client.hashes[self.store.key(f"task:{task.task_id}")],
        )
        self.assertTrue(self.store.is_run_terminal())

    def test_infra_retry_selection_uses_stable_base_task_id(self):
        task_id = "task-c/freecad/task-01@run-1"
        self.client.sets[self.store.key("tasks:infra_incomplete")] = {task_id}
        self.client.hashes[self.store.key("tasks:payload")] = {
            task_id: json.dumps(
                {"metadata": {"base_task_id": "task-c/freecad/task-01"}}
            )
        }

        self.assertEqual(
            self.store.infra_incomplete_base_task_ids(),
            ["task-c/freecad/task-01"],
        )

    def test_legacy_model_environment_failure_is_infra_incomplete(self):
        task = TaskSpec(
            task_id="open/gui-cad/task-01@run-1",
            domain="open/gui-cad",
            example_id="task-01",
            metadata={"snapshot": "Windows-CAD"},
        )
        instance = InstanceRecord(
            instance_id="i-model-environment",
            private_ip="10.0.0.3",
            metadata={"snapshot": "Windows-CAD"},
        )
        self.client.hashes[self.store.key(f"task:{task.task_id}")] = {
            "worker_id": "worker-1",
            "instance_id": instance.instance_id,
            "attempt": "1",
            "max_attempts": "3",
        }
        self.client.hashes[self.store.key(f"instance:{instance.instance_id}")] = {
            "worker_id": "worker-1"
        }
        self.client.hashes[self.store.key("meta")] = {
            "total_tasks": "1",
            "pending_tasks": "0",
            "running_tasks": "1",
        }

        completion = self.store.complete_task_and_release_instance(
            task=task,
            instance=instance,
            worker_id="worker-1",
            score=0.0,
            error="OSWorld Server port 5000 became unavailable",
            error_category=MODEL_ENVIRONMENT_ERROR_CATEGORY,
            recycle_instance=True,
        )

        task_state = self.client.hashes[self.store.key(f"task:{task.task_id}")]
        self.assertEqual(completion["task_status"], "infra_incomplete")
        self.assertFalse(completion["will_retry"])
        self.assertNotIn("score", task_state)
        self.assertEqual(task_state["error_category"], "infra")
        self.assertEqual(self.client.scard(self.store.key("tasks:completed")), 0)
        self.assertEqual(self.client.scard(self.store.key("tasks:infra_incomplete")), 1)
        self.assertTrue(self.store.is_run_terminal())

    def test_retry_run_inherits_agent_settings(self):
        args = Namespace(
            agent=None,
            retry_source_agent_profile="qwen3.7-plus",
            retry_source_agent_config={
                "name": "qwen3.7-plus",
                "max_steps": 23,
            },
            retry_source_agent_env={"OPENAI_BASE_URL": "http://example.test/v1"},
            action_space=None,
            observation_type=None,
            max_steps=None,
            sleep_after_execution=None,
            screen_width=None,
            screen_height=None,
            agent_env=[],
        )

        profile, config, env = _agent_settings_from_args(args)

        self.assertEqual(profile, "qwen3.7-plus")
        self.assertEqual(config.max_steps, 23)
        self.assertEqual(env["OPENAI_BASE_URL"], "http://example.test/v1")

    def test_formal_profile_rejects_flat_step_budget(self):
        args = Namespace(
            agent="gemini-3.7-flash-high",
            max_steps=25,
            agent_env=[],
        )

        with self.assertRaisesRegex(ValueError, "Formal EngiWorld profiles"):
            _agent_settings_from_args(args)

        args.allow_nonstandard_step_limits = True
        _, config, _ = _agent_settings_from_args(args)
        self.assertEqual(config.max_steps, 25)
        self.assertIsNone(config.gui_max_steps)
        self.assertIsNone(config.cli_max_steps)
        self.assertIsNone(config.gui_multi_max_steps)
        self.assertIsNone(config.cli_multi_max_steps)
        self.assertIsNone(config.top10_max_steps)
        self.assertIsNone(config.open_max_steps)
        self.assertIsNone(config.multi_max_steps)

    def test_new_run_requires_explicit_agent_profile(self):
        args = Namespace(
            agent=None,
            retry_source_agent_profile=None,
            agent_env=[],
        )

        with self.assertRaisesRegex(ValueError, "--agent is required"):
            _agent_settings_from_args(args)


if __name__ == "__main__":
    unittest.main()
