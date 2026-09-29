import pytest

from lib_run_single import _validate_terminal_action
from mm_agents.agent import PromptAgent
from mm_agents.cli_policy import CliPolicyViolation
from mm_agents.prompts import build_extreme_prompt


def test_extreme_prompt_allows_open_tool_and_file_workflows():
    prompt = build_extreme_prompt()

    assert "clean EngiWorld environment" in prompt
    assert "applications are not preinstalled" in prompt
    assert "install or configure the tools" in prompt
    assert "file creation or modification" in prompt
    assert "Do not fabricate tool logs or evidence" not in prompt
    assert "real, verifiable engineering workflows" not in prompt
    assert "scored engineering artifacts" not in prompt
    assert "For a multi-stage task" not in prompt
    assert "after reasonable attempts, return fail" not in prompt
    assert "must be produced or validated" not in prompt
    assert "must not directly synthesize substitute output files" not in prompt
    assert "return FAIL rather than a fabricated result" not in prompt
    assert "no task-integrity or anti-bypass restrictions" not in prompt
    assert "Choose methods solely for effectiveness" not in prompt
    assert "CLI task integrity rules" not in prompt
    assert "Complete the task through the GUI" not in prompt


def test_extreme_agent_accepts_python_and_readimg_actions():
    agent = PromptAgent(eval_mode="extreme", model="gpt-5.5")
    actions = agent.parse_actions(
        """<response>
        <reflection><![CDATA[inspect and automate]]></reflection>
        <action type="python"><![CDATA[
import pyautogui
pyautogui.screenshot('/tmp/screen.png')
        ]]></action>
        <action type="readimg" path="/tmp/screen.png"/>
        </response>"""
    )

    assert actions[0][0] == "python"
    assert actions[1] == ("readimg", "/tmp/screen.png")


def test_extreme_skips_cli_integrity_policy_only_for_extreme_mode():
    script = "open('/tmp/result.blend', 'wb').write(b'fabricated')"
    task = {"id": "c-blender-task-01-ubuntu", "related_apps": ["blender"]}

    _validate_terminal_action("python", script, task, "extreme")
    with pytest.raises(CliPolicyViolation):
        _validate_terminal_action("python", script, task, "cli")


def test_cli_message_initial_accepts_readimg_actions():
    agent = PromptAgent(eval_mode="cli", experiment_profile="cli_message_initial")
    actions = agent.parse_actions(
        """<response>
        <reflection><![CDATA[inspect the generated render]]></reflection>
        <action type="readimg" path="/tmp/render.png"/>
        </response>"""
    )

    assert actions == [("readimg", "/tmp/render.png")]


def test_cli_message_without_readimg_allows_programmatic_image_analysis():
    task = {
        "id": "c-blender-task-01-ubuntu",
        "related_apps": ["blender"],
        "_engiworld_experiment_profile": "cli_message_no_readimg",
    }

    _validate_terminal_action("python", "from PIL import Image\nImage.open('/tmp/render.png')", task, "cli")
