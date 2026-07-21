import pytest

from lib_run_single import _validate_terminal_action
from mm_agents.agent import PromptAgent
from mm_agents.cli_policy import CliPolicyViolation
from mm_agents.prompts import build_extreme_prompt


def test_extreme_prompt_is_explicitly_unrestricted():
    prompt = build_extreme_prompt()

    assert "Unrestricted extreme-task mode" in prompt
    assert "no task-integrity or anti-bypass restrictions" in prompt
    assert "pyautogui" in prompt
    assert "CLI task integrity rules" not in prompt
    assert "Complete the task through the GUI" not in prompt
    assert "integrity rules below still govern" not in prompt
    assert "Unrestricted general-purpose Python" in prompt


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
