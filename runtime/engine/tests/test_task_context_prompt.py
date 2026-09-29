import base64

import pytest
from PIL import Image
from io import BytesIO
from pathlib import Path

from mm_agents.agent import (
    PromptAgent,
    _build_cli_observation_content,
    _shorten_messages_preserving_fixed_context,
)
from mm_agents.prompts import (
    build_cli_prompt,
    build_system_prompt,
    build_task_context_prompt,
    experiment_profile_allows_readimg,
    experiment_profile_has_fixed_reference_image,
    experiment_profile_has_fixed_reference_path,
    experiment_profile_image_action,
    normalize_experiment_profile,
)


def test_task_context_prompt_uses_explicit_profile_without_task_metadata_leak():
    prompt = build_task_context_prompt(
        {
            "id": "c-altium-orcad-open-task-01-windows",
            "evaluator": {"func": "hidden_evaluator"},
            "_engiworld_experiment_profile": "cli_message_initial",
        },
        eval_mode="cli",
    )
    assert "Observation:" not in prompt
    assert "Task resources:" not in prompt
    assert "attached to every user message" not in prompt
    assert "hidden_evaluator" not in prompt
    assert "readimg result is attached" not in prompt


def test_profile_aliases_and_defaults_are_stable():
    assert normalize_experiment_profile("cli-message", "cli") == "cli_message_initial"
    assert normalize_experiment_profile("cli-message-no-readimg", "cli") == "cli_message_no_readimg"
    assert normalize_experiment_profile("gui-message", "gui") == "gui_message_initial"
    assert normalize_experiment_profile(None, "gui") == "gui_main"
    assert normalize_experiment_profile(None, "gui-screenshot-a11y") == "gui_screenshot_a11y"
    assert normalize_experiment_profile(None, "gui-a11y") == "base"
    assert normalize_experiment_profile(None, "computer13") == "base"
    assert experiment_profile_allows_readimg("cli_main")
    assert experiment_profile_allows_readimg("cli_message_initial")
    assert not experiment_profile_allows_readimg("cli_message_no_readimg")
    assert experiment_profile_allows_readimg("cli_environment_initial")
    assert not experiment_profile_allows_readimg("gui_main")
    assert experiment_profile_has_fixed_reference_image("gui_message_initial")
    assert experiment_profile_has_fixed_reference_image("cli_message_initial")
    assert experiment_profile_has_fixed_reference_image("cli_message_no_readimg")
    assert not experiment_profile_has_fixed_reference_image("gui_main")
    assert experiment_profile_has_fixed_reference_path("cli_environment_initial")
    assert not experiment_profile_has_fixed_reference_path("cli_message_initial")
    assert normalize_experiment_profile("extreme", "extreme") == "open_engineering"
    assert normalize_experiment_profile("open-engineering", "extreme") == "open_engineering"
    assert experiment_profile_allows_readimg("open_engineering")


def test_cli_prompt_without_readimg_removes_the_action_from_the_envelope():
    prompt = build_cli_prompt(allow_readimg=False)
    assert "`bash` / `python` / `wait` / `fail` / `done`" in prompt
    assert '<action type="readimg"' not in prompt
    assert "readimg returns no stdout" not in prompt
    assert "receive only the previous turn's terminal output" not in prompt


def test_prompt_hides_sampling_parameters_from_runtime_settings():
    prompt = build_system_prompt("cli", "cli_main", {
        "max_steps": 100,
        "temperature": 1.0,
        "top_p": 1.0,
    })
    assert "Maximum steps:" not in prompt
    assert "Temperature:" not in prompt
    assert "Top-p:" not in prompt


def test_screenshot_a11y_prompt_explains_tree_columns_and_center_coordinates():
    prompt = build_system_prompt("gui-screenshot-a11y", "gui_screenshot_a11y")
    assert "tab-separated table" in prompt
    assert "position (top-left x&y)" in prompt
    assert "x + w/2, y + h/2" in prompt


def test_system_prompt_keeps_gui_action_space_without_profile_explanations():
    prompt = build_system_prompt("gui", "gui_main")
    assert "action's `type` attribute MUST be one of: `pyautogui` / `wait` / `fail` / `done`" in prompt
    assert "Observation:" not in prompt
    assert "Task resources:" not in prompt
    assert "not attached as extra images" not in prompt


def test_cli_experiment_overlays_avoid_defensive_screenshot_wording():
    for profile in (
        "cli_main",
        "cli_message_initial",
        "cli_environment_initial",
    ):
        prompt = build_system_prompt("cli", profile)
        assert "no screenshot action" not in prompt.lower()


def test_unknown_profile_fails_loudly():
    with pytest.raises(ValueError, match="Unknown experiment profile"):
        normalize_experiment_profile("not-a-real-profile", "cli")


def test_runner_settings_stay_out_of_system_prompt_and_task_instruction_is_present():
    agent = PromptAgent(
        eval_mode="gui",
        model="gpt-4o",
        max_steps=200,
        max_trajectory_length=15,
        max_tokens=8192,
        wait_seconds=120,
        action_timeout_seconds=120,
        post_action_delay_seconds=2.0,
        screen_width=1920,
        screen_height=1080,
    )
    agent.call_llm = lambda _payload: '<response><reflection><![CDATA[done]]></reflection><action type="done"/></response>'
    agent.predict("Save the requested model.", {"screenshot": b"png"})
    prompt = agent._first_system_text
    assert "History turns retained" not in prompt
    assert "Default wait seconds" not in prompt
    assert "Per-action timeout seconds" not in prompt
    assert "Maximum output tokens" not in prompt
    assert (
        "# Task\n\nThe task you need to complete is:\n\n"
        "<task_instruction>\nSave the requested model.\n</task_instruction>"
    ) in prompt


def test_gui_timing_rules_use_runtime_values_and_keep_wait_separate_from_sleep():
    prompt = build_system_prompt("gui", "gui_main", {
        "wait_seconds": 90,
        "action_timeout_seconds": 135,
        "post_action_delay_seconds": 3.5,
    })
    assert "including any sleeps, shares a 135-second wall-clock limit" in prompt
    assert "A wait occupies one step, defaults to 90 seconds" in prompt
    assert "runtime waits 3.5 seconds before taking the next observation" in prompt
    assert "sleep-only `pyautogui` action" in prompt
    assert "{ACTION_TIMEOUT_SECONDS}" not in prompt
    assert "{WAIT_SECONDS}" not in prompt
    assert "{POST_ACTION_DELAY_SECONDS}" not in prompt


def test_gui_file_rules_describe_visible_workflow():
    prompt = build_system_prompt("gui", "gui_main")
    assert "file managers, file pickers, and the application's Open and Save dialogs" in prompt
    assert "Python filesystem access" in prompt
    assert "run is failed even if the final file is correct" in prompt


def test_cli_prompt_explains_process_state_and_persistent_task_state():
    prompt = build_system_prompt("cli", "cli_main", {
        "post_action_delay_seconds": 2,
        "screen_resolution": "1920x1080",
    })
    assert "Each `bash` action starts a fresh shell" in prompt
    assert "Files written to disk and deliberately detached background processes do persist" in prompt
    assert "Each `python` action runs in a fresh interpreter" in prompt
    assert "Python standard-library code for calculations" in prompt
    assert "`math`, `statistics`, `decimal`, and `fractions`" in prompt
    assert "Third-party Python packages such as `numpy` and `scipy` are not permitted" in prompt
    assert "unless they are part of the required application's official Python API" in prompt
    assert "required application's official Python API" in prompt
    assert "One model response counts as one experiment step" not in prompt
    assert "not additional experiment steps" not in prompt
    assert "Each `bash` or `python` action has its own 120-second" in prompt
    assert "later actions in the same response still run" in prompt
    assert "joined with `&&`" in prompt
    assert "mixed XML order is not preserved" in prompt
    assert "`bash`, `readimg`, `python` executes as `bash`, `python`, `readimg`" in prompt
    assert "terminal output and return code are reported" in prompt
    assert "OSWorld Server" not in prompt
    assert "Post-action delay seconds" not in prompt
    assert "Screen resolution" not in prompt
    assert "The following operations are not allowed. They are rejected before execution" in prompt
    assert "Do not understand or operate the required application through desktop screenshots" in prompt
    assert "use terminal code or system APIs to move or click the mouse" in prompt


def test_text_only_profile_does_not_name_image_actions():
    prompt = build_system_prompt("cli-text", "cli_text")
    assert "readimg" not in prompt
    assert "Do not understand or operate the required application through desktop screenshots" in prompt


def test_cli_message_profile_keeps_readimg_without_profile_explanations():
    prompt = build_system_prompt("cli", "cli_message_initial")
    assert '<action type="readimg"' in prompt
    assert "Observation:" not in prompt
    assert "Task resources:" not in prompt


def test_cli_message_without_readimg_keeps_only_the_fixed_reference_image_channel():
    prompt = build_system_prompt("cli", "cli_message_no_readimg")
    assert "readimg" not in prompt
    assert "image reads" not in prompt
    assert "Observation:" not in prompt
    assert "Task resources:" not in prompt

    agent = PromptAgent(eval_mode="cli", experiment_profile="cli_message_no_readimg")
    with pytest.raises(ValueError, match="not allowed"):
        agent.parse_actions(
            '<response><reflection><![CDATA[inspect]]></reflection>'
            '<action type="readimg" path="/tmp/render.png"/></response>'
        )


def test_cli_text_prompt_starts_with_the_terminal_workflow():
    prompt = build_system_prompt("cli-text", "cli_text")
    assert prompt.startswith("Complete the task through the required application(s)' command-line")
    assert "Assess the current state from terminal output, return codes" in prompt
    assert "to read and process image files" in prompt
    assert "`struct` and `zlib`" in prompt
    assert "only the previous turn's terminal output" not in prompt


def test_open_engineering_profile_uses_the_extreme_action_space():
    prompt = build_system_prompt("extreme", "open_engineering")
    assert "clean OSWorld environment" in prompt
    assert "install or configure the tools" in prompt
    assert '<action type="readimg"' in prompt
    assert "Observation:" not in prompt
    assert "Task resources:" not in prompt


def test_gui_message_profile_keeps_gui_action_space_without_profile_explanations():
    prompt = build_system_prompt("gui", "gui_message_initial")
    assert "`pyautogui` / `wait` / `fail` / `done`" in prompt
    assert "Observation:" not in prompt
    assert "Task resources:" not in prompt
    assert "readimg" not in prompt


def test_message_profile_loads_only_setup_images(tmp_path: Path):
    drawing = tmp_path / "drawing.png"
    drawing.write_bytes(b"not-decoded-until-message-build")
    evaluator = tmp_path / "answer.png"
    evaluator.write_bytes(b"hidden")
    agent = PromptAgent(eval_mode="cli", experiment_profile="cli_message_initial")
    agent.set_task_config({
        "config": [{"type": "upload_file", "parameters": {"files": [{"local_path": str(drawing), "path": "/vm/drawing.png"}]}}],
        "evaluator": {"postconfig": [{"type": "upload_file", "parameters": {"files": [{"local_path": str(evaluator), "path": "/vm/answer.png"}]}}]},
    })
    assert [path for path, _data in agent._fixed_initial_images] == ["/vm/drawing.png"]


def test_message_profile_loads_non_uploaded_image_from_public_init_file(tmp_path: Path):
    task_dir = tmp_path / "init-image" / "messgae" / "cli-demo" / "task-01"
    init_dir = task_dir / "init_file"
    init_dir.mkdir(parents=True)
    drawing = init_dir / "drawing.png"
    drawing.write_bytes(b"message-image")
    (task_dir / "ground_truth").mkdir()
    (task_dir / "ground_truth" / "answer.png").write_bytes(b"hidden")
    task_json = task_dir / "task-01.json"
    task_json.write_text("{}", encoding="utf-8")

    agent = PromptAgent(eval_mode="cli", experiment_profile="cli_message_initial")
    agent.set_task_config({
        "_engiworld_config_path": str(task_json),
        "config": [],
    })

    assert agent._fixed_initial_images == [("drawing.png", b"message-image")]


def test_message_profile_places_labeled_initial_images_after_system_prompt(tmp_path: Path):
    drawing = tmp_path / "drawing.png"
    drawing.write_bytes(b"not-a-real-image")
    agent = PromptAgent(eval_mode="cli", experiment_profile="cli_message_initial")
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
    agent._fixed_initial_images = [("/vm/drawing.png", png)]
    agent.call_llm = lambda payload: (
        setattr(agent, "_captured_payload", payload)
        or '<response><reflection><![CDATA[done]]></reflection><action type="done"/></response>'
    )
    agent.predict("Build the requested model.", {"bash_runs": []})
    messages = agent._captured_payload["messages"]
    assert [message["role"] for message in messages] == ["system", "user", "user"]
    assert [part["type"] for part in messages[1]["content"]] == ["text", "image_url"]
    assert messages[1]["content"][0]["text"] == "This is the reference image for this task."
    assert messages[2]["content"] == [{
        "type": "text",
        "text": "This is turn 1 of the task. There is currently no new terminal output.",
    }]


def test_gui_message_profile_places_reference_image_before_current_screenshot():
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
    agent = PromptAgent(eval_mode="gui", experiment_profile="gui_message_initial", model="gpt-4o")
    agent._fixed_initial_images = [("drawing.png", png)]
    agent.call_llm = lambda payload: (
        setattr(agent, "_captured_payload", payload)
        or '<response><reflection><![CDATA[continue]]></reflection><action type="wait" seconds="0"/></response>'
    )

    agent.predict("Build the requested model.", {"screenshot": png})

    messages = agent._captured_payload["messages"]
    assert [message["role"] for message in messages] == ["system", "user", "user"]
    assert messages[1]["content"][0]["text"] == "This is the reference image for this task."
    assert "current screen screenshot" in messages[2]["content"][0]["text"]


def test_message_profile_keeps_one_initial_image_message_in_every_request_before_rolling_history():
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
    agent = PromptAgent(eval_mode="cli", experiment_profile="cli_message_initial")
    agent._fixed_initial_images = [("/vm/drawing.png", png)]
    payloads = []

    def capture(payload):
        payloads.append(payload)
        return '<response><reflection><![CDATA[inspect]]></reflection><action type="wait" seconds="0"/></response>'

    agent.call_llm = capture
    agent.predict("Build the requested model.", {"bash_runs": []})
    agent.predict("Build the requested model.", {"bash_runs": []})

    for payload in payloads:
        messages = payload["messages"]
        initial_indexes = [
            index
            for index, message in enumerate(messages)
            if any(
                part.get("text") == "This is the reference image for this task."
                for part in message.get("content", [])
            )
        ]
        assert initial_indexes == [1]
    messages = payloads[-1]["messages"]
    assert [message["role"] for message in messages] == [
        "system", "user", "user", "assistant", "user",
    ]
    assert messages[1]["content"][0]["text"] == "This is the reference image for this task."
    assert messages[2]["content"][0]["text"] == (
        "This is turn 1 of the task. There is currently no new terminal output."
    )
    assert messages[-1]["content"][0]["text"] == (
        "This is turn 2 of the task. There is currently no new terminal output."
    )


def test_environment_cli_first_request_contains_fixed_reference_path():
    agent = PromptAgent(eval_mode="cli", experiment_profile="cli_environment_initial")
    agent._fixed_initial_images = [("/vm/drawing.png", b"not-sent-to-model")]
    agent.call_llm = lambda payload: (
        setattr(agent, "_captured_payload", payload)
        or '<response><reflection><![CDATA[start]]></reflection><action type="wait" seconds="0"/></response>'
    )

    agent.predict("Build the requested model.", {"bash_runs": [], "images": []})

    messages = agent._captured_payload["messages"]
    assert [message["role"] for message in messages] == ["system", "user", "user"]
    assert messages[1]["content"] == [{
        "type": "text",
        "text": (
            "The reference image for this task is available at:\n"
            "/vm/drawing.png\n\n"
            "Use readimg when you need to inspect it."
        ),
    }]
    assert messages[2]["content"] == [{
        "type": "text",
        "text": "This is turn 1 of the task. There is currently no new terminal output.",
    }]


def test_environment_cli_keeps_reference_path_before_rolling_history():
    agent = PromptAgent(
        eval_mode="cli",
        experiment_profile="cli_environment_initial",
        max_trajectory_length=1,
    )
    agent._fixed_initial_images = [("/vm/drawing.png", b"not-sent-to-model")]
    payloads = []
    agent.call_llm = lambda payload: (
        payloads.append(payload)
        or '<response><reflection><![CDATA[continue]]></reflection><action type="wait" seconds="0"/></response>'
    )

    agent.predict("Build the requested model.", {"bash_runs": [], "images": []})
    agent.predict("Build the requested model.", {"bash_runs": [], "images": []})

    for payload in payloads:
        messages = payload["messages"]
        assert messages[1]["role"] == "user"
        assert messages[1]["content"][0]["text"].startswith(
            "The reference image for this task is available at:"
        )
        assert not any(part.get("type") == "image_url" for part in messages[1]["content"])


def test_empty_cli_observation_still_produces_a_user_turn():
    assert _build_cli_observation_content([], [], step=7) == [{
        "type": "text",
        "text": "This is turn 7 of the task. There is currently no new terminal output.",
    }]


def test_cli_user_message_explains_terminal_and_readimg_results_in_order():
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
    agent = PromptAgent(eval_mode="cli", experiment_profile="cli_environment_initial")
    agent.call_llm = lambda payload: (
        setattr(agent, "_captured_payload", payload)
        or '<response><reflection><![CDATA[continue]]></reflection><action type="wait" seconds="0"/></response>'
    )

    agent.predict("Build the requested model.", {
        "bash_runs": [{
            "command": "echo ok",
            "stdout": "ok\nwarning from stderr\n",
            "stderr": "policy rejection",
            "returncode": -2,
        }],
        "images": [("/tmp/first.png", png), ("/tmp/second.png", png)],
    })

    content = agent._captured_payload["messages"][-1]["content"]
    assert [part["type"] for part in content] == ["text", "image_url", "image_url"]
    assert content[0]["text"].startswith("This is turn 1 of the task.")
    assert "results of the terminal actions you requested" in content[0]["text"]
    assert "terminal output and returncode" in content[0]["text"]
    assert "ok\nwarning from stderr" in content[0]["text"]
    assert "[runtime error]\npolicy rejection" in content[0]["text"]
    assert "images returned by the readimg actions you requested, in request order" in content[0]["text"]
    assert content[0]["text"].index("/tmp/first.png") < content[0]["text"].index("/tmp/second.png")


def test_readimg_images_remain_in_recent_cli_history():
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
    agent = PromptAgent(eval_mode="cli", experiment_profile="cli_main")
    payloads = []
    agent.call_llm = lambda payload: (
        payloads.append(payload)
        or '<response><reflection><![CDATA[continue]]></reflection><action type="wait" seconds="0"/></response>'
    )

    agent.predict("Build the requested model.", {"bash_runs": [], "images": [("/tmp/render.png", png)]})
    agent.predict("Build the requested model.", {"bash_runs": [{"command": "echo next", "stdout": "next", "stderr": "", "returncode": 0}], "images": []})

    history_image_messages = [
        message for message in payloads[-1]["messages"][:-1]
        if any(part.get("type") == "image_url" for part in message.get("content", []))
    ]
    assert len(history_image_messages) == 1
    assert "/tmp/render.png" in history_image_messages[0]["content"][0]["text"]


def test_context_shortening_keeps_fixed_reference_image_message():
    messages = [
        {"role": "system", "content": [{"type": "text", "text": "rules"}]},
        {"role": "user", "content": [
            {"type": "text", "text": "This is the reference image for this task."},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,x"}},
        ]},
        {"role": "assistant", "content": [{"type": "text", "text": "old action"}]},
        {"role": "user", "content": [{"type": "text", "text": "latest observation"}]},
    ]

    shortened = _shorten_messages_preserving_fixed_context(messages)

    assert [message["role"] for message in shortened] == ["system", "user", "user"]
    assert shortened[1]["content"][0]["text"] == "This is the reference image for this task."
    assert shortened[-1]["content"][0]["text"] == "latest observation"


def test_context_shortening_keeps_fixed_reference_path_message():
    messages = [
        {"role": "system", "content": [{"type": "text", "text": "rules"}]},
        {"role": "user", "content": [{
            "type": "text",
            "text": (
                "The reference image for this task is available at:\n"
                "/vm/drawing.png\n\n"
                "Use readimg when you need to inspect it."
            ),
        }]},
        {"role": "assistant", "content": [{"type": "text", "text": "old action"}]},
        {"role": "user", "content": [{"type": "text", "text": "latest observation"}]},
    ]

    shortened = _shorten_messages_preserving_fixed_context(messages)

    assert [message["role"] for message in shortened] == ["system", "user", "user"]
    assert shortened[1]["content"][0]["text"].startswith(
        "The reference image for this task is available at:"
    )
    assert shortened[-1]["content"][0]["text"] == "latest observation"


def test_cli_history_keeps_five_complete_recent_turns_plus_current_user():
    agent = PromptAgent(
        eval_mode="cli",
        experiment_profile="cli_main",
        max_trajectory_length=5,
    )
    payloads = []
    agent.call_llm = lambda payload: (
        payloads.append(payload)
        or '<response><reflection><![CDATA[continue]]></reflection><action type="wait" seconds="0"/></response>'
    )

    agent.predict("Build the requested model.", {"bash_runs": [], "images": []})
    for step in range(2, 9):
        agent.predict("Build the requested model.", {
            "bash_runs": [{
                "command": f"echo step-{step}",
                "stdout": f"step-{step}",
                "stderr": "",
                "returncode": 0,
            }],
            "images": [],
        })

    messages = payloads[-1]["messages"]
    roles = [message["role"] for message in messages]
    joined = str(messages)
    assert roles.count("assistant") == 5
    assert roles.count("user") == 7
    assert "step-2" not in joined
    assert "step-3" in joined
    assert "step-8" in joined
    assert "This is turn 3 of the task." in joined
    assert "This is turn 8 of the task." in joined


@pytest.mark.parametrize("eval_mode", ["gui", "gui-screenshot-a11y", "gui-a11y"])
def test_gui_user_messages_include_the_current_turn_number(eval_mode):
    agent = PromptAgent(eval_mode=eval_mode, model="gpt-4o")
    payloads = []
    agent.call_llm = lambda payload: (
        payloads.append(payload)
        or '<response><reflection><![CDATA[continue]]></reflection><action type="wait" seconds="0"/></response>'
    )
    obs = {"screenshot": b"png", "accessibility_tree": "<root/>"}

    agent.predict("Continue the task.", obs)
    agent.predict("Continue the task.", obs)

    user_texts = [
        part["text"]
        for message in payloads[-1]["messages"]
        if message["role"] == "user"
        for part in message["content"]
        if part["type"] == "text"
    ]
    assert user_texts[0].startswith("This is turn 1 of the task.")
    assert user_texts[-1].startswith("This is turn 2 of the task.")


@pytest.mark.parametrize("scale, expected_size", [(0.2, (384, 216)), (0.6, (1152, 648))])
def test_gui_screenshot_scale_only_changes_model_observation(monkeypatch, scale, expected_size):
    monkeypatch.setenv("ARENA_GUI_SCREENSHOT_SCALE", str(scale))
    source = BytesIO()
    Image.new("RGB", (1920, 1080), "white").save(source, format="PNG")
    agent = PromptAgent(eval_mode="gui", model="gpt-4o", screen_width=1920, screen_height=1080)
    payloads = []
    agent.call_llm = lambda payload: (
        payloads.append(payload)
        or '<response><reflection><![CDATA[continue]]></reflection><action type="wait" seconds="0"/></response>'
    )

    agent.predict("Continue the task.", {"screenshot": source.getvalue()})

    image_url = next(
        part["image_url"]["url"]
        for message in payloads[0]["messages"]
        for part in message["content"]
        if part["type"] == "image_url"
    )
    encoded = image_url.split(",", 1)[1]
    with Image.open(BytesIO(base64.b64decode(encoded))) as image:
        assert image.size == expected_size
    assert agent.screen_width == 1920
    assert agent.screen_height == 1080
