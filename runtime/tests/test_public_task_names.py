"""The public layout must preserve historical task selection and run limits."""

from collections import Counter
import ast
from dataclasses import replace
import importlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

from engiworld.agents.profiles import get_agent_profile
from engiworld.scheduler import master, worker
from engiworld.scheduler.runner import _agent_config_for_task, resolve_engine_path
from engiworld.scheduler.task_loader import load_tasks


RUNTIME = Path(__file__).resolve().parents[1]
TASKS = RUNTIME.parent / "task"


def test_full_corpus_partition_and_interface_budgets():
    tasks = load_tasks(TASKS)
    assert Counter(task.metadata["task_kind"] for task in tasks) == {
        "single-software-execution": 931, "cross-software-coordination": 60, "software-selection": 140,
        "design-optimization": 40, "vision-guided-modeling": 120, "open-environment-engineering": 10,
    }
    assert Counter(task.metadata["eval_mode"] for task in tasks) == {"cli": 691, "gui": 610}
    with patch.dict("os.environ", {}, clear=True):
        for task in tasks:
            config = _agent_config_for_task(get_agent_profile("openai-compatible").agent_config, task)
            extended = task.metadata["task_kind"] in {"cross-software-coordination", "open-environment-engineering"}
            expected = (150 if extended else 100) if config.eval_mode in {"cli", "extreme"} else (300 if extended else 200)
            assert config.max_steps == expected, task.task_id
            assert config.history_turns == 15


def test_main_experiment_split_preserves_the_300_task_cohort():
    requested = (TASKS / "splits/main-300.txt").read_text().splitlines()
    requested = [line for line in requested if line and not line.startswith("#")]
    assert len(requested) == len(set(requested)) == 300
    selected = master._select_tasks_by_ids(load_tasks(TASKS), requested)
    assert {task.metadata["source_task_id"] for task in selected} == set(requested)
    assert Counter(task.metadata["eval_mode"] for task in selected) == {"cli": 152, "gui": 148}
    assert Counter(task.metadata["task_kind"] for task in selected) == {
        "single-software-execution": 175, "cross-software-coordination": 24, "software-selection": 28,
        "design-optimization": 33, "vision-guided-modeling": 36, "open-environment-engineering": 4,
    }


def test_updated_main_experiment_contains_306_tasks_and_all_open_environment_tasks():
    requested = (TASKS / "splits/main-306.txt").read_text().splitlines()
    assert len(requested) == len(set(requested)) == 306
    selected = master._select_tasks_by_ids(load_tasks(TASKS), requested)
    assert {task.metadata["source_task_id"] for task in selected} == set(requested)
    assert Counter(task.metadata["eval_mode"] for task in selected) == {"cli": 158, "gui": 148}
    assert Counter(task.metadata["task_kind"] for task in selected) == {
        "single-software-execution": 175, "software-selection": 28,
        "vision-guided-modeling": 36, "design-optimization": 33,
        "cross-software-coordination": 24, "open-environment-engineering": 10,
    }


def test_previous_json_ids_and_directory_ids_select_the_same_tasks():
    migration = json.loads((TASKS / "id-migration-20261009.json").read_text())["tasks"]
    tasks = load_tasks(TASKS)
    for field in ("old_id", "old_path", "new_id", "new_path"):
        selected = master._select_tasks_by_ids(tasks, [row[field] for row in migration])
        assert [task.metadata["source_task_id"] for task in selected] == [row["new_id"] for row in migration]


def test_every_historical_task_selects_the_same_internal_id():
    aliases = json.loads((TASKS / "aliases.json").read_text())
    tasks = {task.task_id: task for task in load_tasks(TASKS)}
    assert len(aliases) >= 300
    assert set(aliases.values()) == set(tasks)
    for old, new in aliases.items():
        selected = load_tasks(TASKS, path_prefixes=[old + "/"])
        assert [task.task_id for task in selected] == [new], old
        assert selected[0].metadata["source_task_id"] == tasks[new].metadata["source_task_id"]


def test_release_layout_has_unique_ids_and_explicit_interfaces():
    tasks = load_tasks(TASKS)
    ids = [task.metadata["source_task_id"] for task in tasks]
    assert len(ids) == len(set(ids)) == 1301
    for task in tasks:
        category, interface, software, number = task.task_id.split("/")
        assert interface == task.metadata["eval_mode"]
        assert software == task.metadata["app"]
        assert task.metadata["source_task_id"] == "--".join(
            [category, interface, software, number, task.metadata["os_type"].lower()])
        if category == "open-environment-engineering":
            assert (interface, software) == ("cli", "agent-selected")


def test_exact_task_selection_does_not_include_reverse_variant():
    selected = load_tasks(TASKS, path_prefixes=["single-software-execution/gui/cadence-orcad/task-04/"])
    assert [task.task_id for task in selected] == ["single-software-execution/gui/cadence-orcad/task-04"]
    reverse = load_tasks(TASKS, path_prefixes=["single-software-execution/gui/cadence-orcad/task-04-reverse/"])
    assert len(reverse) == 1
    assert reverse[0].task_id.endswith("/task-04-reverse")


def test_old_package_and_factory_paths_remain_importable():
    module = importlib.import_module("arena_osworld.agents.openai_compatible")
    assert callable(module.create_agent)
    compatibility = importlib.import_module("arena_osworld.scheduler.osworld_runner")
    assert compatibility.resolve_osworld_path() == RUNTIME / "engine"


def test_engine_resolution_does_not_depend_on_launch_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch.dict("os.environ", {}, clear=True):
        assert resolve_engine_path() == RUNTIME / "engine"
        assert resolve_engine_path("third_party/OSWorld") == RUNTIME / "engine"


def test_retry_preserves_legacy_open_ended_limit_and_accepts_explicit_override():
    parser = master.build_parser()
    args = parser.parse_args(["plan", "--allow-nonstandard-step-limits"])
    args.retry_source_agent_profile = "openai-compatible"
    args.retry_source_agent_config = {"top10_max_steps": 123}
    _, config, _ = master._agent_settings_from_args(args)
    assert config.open_ended_max_steps == 123
    assert config.top10_max_steps is None
    args.open_ended_max_steps = 140
    _, config, _ = master._agent_settings_from_args(args)
    task = load_tasks(TASKS, path_prefixes=["open-environment-engineering/"], limit=1)[0]
    assert _agent_config_for_task(config, task).max_steps == 140
    historical = replace(config, open_ended_max_steps=None, top10_max_steps=123)
    assert _agent_config_for_task(historical, task).max_steps == 123


def test_worker_converts_public_flags_into_configuration_without_starting_worker():
    flags = ["worker", "--engine-path", str(RUNTIME / "engine"), "--open-ended-max-steps", "150"]
    with patch("sys.argv", flags), patch.object(worker, "_run_worker_loop") as run:
        worker.main()
    assert run.call_count == 1
    assert run.call_args.args[1].engine_path == str(RUNTIME / "engine")
    assert run.call_args.args[2].open_ended_max_steps == 150
    legacy = worker.build_parser().parse_args(["--top10-max-steps", "125"])
    assert legacy.open_ended_max_steps == 125


def test_open_ended_uses_blank_image_and_unrestricted_terminal_execution():
    with patch.dict("os.environ", {}, clear=True):
        tasks = load_tasks(TASKS, path_prefixes=["top-10-hardest/"])
        assert len(tasks) == 10
        for task in tasks:
            assert task.metadata["snapshot"] == "top-10"
            example = task.metadata["task_json"]
            assert example["snapshot"] == "top-10"
            assert "no engineering applications preinstalled" in example["instruction"]
            assert "No particular software is required" in example["instruction"]
            assert "are available but none is mandatory" not in example["instruction"]
            assert all(step["type"] == "upload_file" for step in example["config"])
            for mode in ("auto", "cli", "cli-text"):
                base = replace(get_agent_profile("openai-compatible").agent_config,
                               eval_mode=mode, experiment_profile="cli_main")
                config = _agent_config_for_task(base, task)
                assert config.eval_mode == "extreme"
                assert config.experiment_profile == "open_engineering"
                assert config.observation_type == "terminal"
                assert config.max_steps == 150
                assert config.history_turns == 15


def test_open_ended_prompt_and_execution_allow_installing_tools():
    # Load the real gate without importing the optional desktop/ML dependencies.
    with patch.object(sys, "path", [str(RUNTIME / "engine"), *sys.path]):
        from mm_agents.cli_policy import CliPolicyViolation, validate_cli_action
        from mm_agents.prompts import build_system_prompt
    source = RUNTIME / "engine/lib_run_single.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name in {"_validate_terminal_action", "_restricts_visual_file_access"}]
    namespace = {"validate_cli_action": validate_cli_action}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), "exec"), namespace)
    check = namespace["_validate_terminal_action"]
    task = load_tasks(TASKS, path_prefixes=["open-environment-engineering/"], limit=1)[0]
    config = _agent_config_for_task(get_agent_profile("openai-compatible").agent_config, task)
    prompt = build_system_prompt(config.eval_mode, config.experiment_profile)
    assert "clean EngiWorld environment" in prompt
    assert "applications are not preinstalled" in prompt
    assert "install or configure the tools" in prompt
    assert "CLI task integrity rules" not in prompt
    check("bash", "pip install cadquery", task.metadata["task_json"], config.eval_mode)
    with pytest.raises(CliPolicyViolation):
        check("bash", "pip install cadquery", task.metadata["task_json"], "cli")
