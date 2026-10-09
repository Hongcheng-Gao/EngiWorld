from collections import Counter
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from engiworld.agents.profiles import get_agent_profile
from engiworld.scheduler.runner import _agent_config_for_task, load_task_config
from engiworld.scheduler.schemas import EvalConfig, TaskSpec
from engiworld.scheduler.task_loader import load_tasks

TASK_ROOT = Path(__file__).resolve().parents[2] / "task"


def test_all_120_released_reference_tasks_default_to_message():
    tasks = load_tasks(TASK_ROOT)
    profile = get_agent_profile("openai-compatible")
    selected = []
    with patch.dict("os.environ", {}, clear=True):
        for task in tasks:
            config = _agent_config_for_task(profile.agent_config, task)
            if task.task_id.startswith("vision-guided-modeling/"):
                selected.append(config)
                example = load_task_config(EvalConfig(run_id="test", task_root=str(TASK_ROOT)), task)
                assert Path(example["_engiworld_config_path"]).is_file()
                assert config.experiment_profile == f"{config.eval_mode}_message_initial"
                assert config.max_steps == (100 if config.eval_mode == "cli" else 200)
                assert config.history_turns == 15
            elif task.task_id.startswith("open-environment-engineering/"):
                assert config.experiment_profile == "open_engineering"
            else:
                assert config.experiment_profile is None
    assert len(tasks) == 1301
    assert Counter(c.experiment_profile for c in selected) == {
        "gui_message_initial": 60, "cli_message_initial": 60,
    }


@pytest.mark.parametrize("mode", ["gui", "cli"])
def test_explicit_experiment_profile_is_preserved(mode):
    task = TaskSpec(task_id=f"init-image/messgae/{mode}-test/task-01@run",
                    domain=f"init-image/messgae/{mode}-test", example_id="task-01")
    config = replace(get_agent_profile("openai-compatible").agent_config,
                     experiment_profile=f"{mode}_main")
    assert _agent_config_for_task(config, task).experiment_profile == f"{mode}_main"


def test_cli_text_default_keeps_visual_action_restriction():
    task = TaskSpec(task_id="init-image/messgae/cli-test/task-01@run",
                    domain="init-image/messgae/cli-test", example_id="task-01")
    config = replace(get_agent_profile("openai-compatible").agent_config, eval_mode="cli-text")
    with patch.dict("os.environ", {}, clear=True):
        resolved = _agent_config_for_task(config, task)
    assert resolved.experiment_profile == "cli_message_no_readimg"
