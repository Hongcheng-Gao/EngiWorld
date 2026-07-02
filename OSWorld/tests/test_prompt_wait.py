import pytest

from mm_agents.agent import parse_cli_actions, parse_gui_actions
from mm_agents.prompts import build_cli_prompt, build_gui_prompt


def test_gui_wait_defaults_to_120_seconds():
    actions = parse_gui_actions(
        '<response><reflection><![CDATA[pause]]></reflection><action type="wait"/></response>'
    )
    assert actions == [("WAIT", "120")]


def test_gui_wait_accepts_seconds_attribute():
    actions = parse_gui_actions(
        '<response><reflection><![CDATA[pause]]></reflection><action type="wait" seconds="300"/></response>'
    )
    assert actions == [("WAIT", "300")]


def test_cli_wait_accepts_seconds_attribute():
    actions = parse_cli_actions(
        '<response><reflection><![CDATA[pause]]></reflection><action type="wait" seconds="2.5"/></response>'
    )
    assert actions == [("WAIT", "2.5")]


def test_cli_wait_rejects_out_of_range_seconds():
    with pytest.raises(ValueError):
        parse_cli_actions(
            '<response><reflection><![CDATA[pause]]></reflection><action type="wait" seconds="1801"/></response>'
        )


def test_done_rejects_seconds_attribute():
    with pytest.raises(ValueError):
        parse_gui_actions(
            '<response><reflection><![CDATA[done]]></reflection><action type="done" seconds="120"/></response>'
        )


def test_prompts_document_wait_seconds():
    assert 'action type="wait" seconds="300"' in build_gui_prompt()
    assert 'action type="wait" seconds="300"' in build_cli_prompt()
    assert "defaults to 120 seconds" in build_gui_prompt()
    assert "defaults to 120 seconds" in build_cli_prompt()
