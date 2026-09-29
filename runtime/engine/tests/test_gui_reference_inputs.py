import pytest

from mm_agents.agent import PromptAgent, parse_gui_actions, _declared_gui_reference_url


def config(path):
    return {"config": [{"type": "upload_file", "parameters": {"files": [{"path": path}]}}]}


def response(url):
    return f'''<response><reflection>Read the task supplement.</reflection>
<action type="pyautogui"><![CDATA[
import pyautogui
pyautogui.hotkey('ctrl', 't')
pyautogui.write({(url + chr(10))!r})
]]></action></response>'''


@pytest.mark.parametrize("path,url", [
    ("/home/user/Desktop/supplement.csv", "file:///home/user/Desktop/supplement.csv"),
    ("C:/Users/User/Desktop/supplement.csv", "file:///C:/Users/User/Desktop/supplement.csv"),
    ("/home/user/Desktop/input notes.csv", "file:///home/user/Desktop/input%20notes.csv"),
    ("C:/Users/user/Desktop/mods.json", "file:///C:/Users/user/Desktop/mods.json"),
    ("C:/Users/User/Desktop/MODS.JSON", "file:///c:/users/user/desktop/mods.json"),
])
def test_gui_can_open_declared_reference(path, url):
    assert parse_gui_actions(response(url), config(path))[0][0] == "pyautogui"


@pytest.mark.parametrize("url", [
    "file:///home/user/Desktop/result.csv",
    "file:///home/user/Desktop/reference_dimensions.csv",
    "file:///tmp/supplement.csv",
    "file:///home/user/Desktop/result.step",
    "file:///home/user/Desktop/supplement.csv?other=true",
])
def test_gui_reference_exception_is_limited_to_declared_input(url):
    with pytest.raises(ValueError):
        parse_gui_actions(response(url), config("/home/user/Desktop/supplement.csv"))


def test_evaluator_upload_does_not_allow_gui_reading():
    task = {"evaluator": {"postconfig": config("/home/user/Desktop/supplement.csv")["config"]}}
    with pytest.raises(ValueError):
        parse_gui_actions(response("file:///home/user/Desktop/supplement.csv"), task)


def test_gui_reference_exception_does_not_allow_python_file_access():
    xml = response("file:///home/user/Desktop/supplement.csv").replace(
        "import pyautogui", "import pyautogui\nopen('/home/user/Desktop/supplement.csv').read()"
    )
    with pytest.raises(ValueError):
        parse_gui_actions(xml, config("/home/user/Desktop/supplement.csv"))


@pytest.mark.parametrize("mode", ["gui", "gui-screenshot-a11y"])
@pytest.mark.parametrize("extension", ["csv", "json"])
def test_agent_passes_task_inputs_to_gui_parser(mode, extension):
    agent = PromptAgent.__new__(PromptAgent)
    agent.eval_mode = mode
    agent._task_config = config(f"/home/user/Desktop/reference.{extension}")
    agent.actions = []
    assert agent.parse_actions(response(f"file:///home/user/Desktop/reference.{extension}"))[0][0] == "pyautogui"


@pytest.mark.parametrize("extension", ["csv", "json", "yaml", "yml", "pdf", "txt", "md", "markdown"])
def test_reference_formats_are_readable(extension):
    path = f"/home/user/Desktop/reference.{extension}"
    task = config(path)
    assert _declared_gui_reference_url("file://" + path, task)
    assert parse_gui_actions(response("file://" + path), task)[0][0] == "pyautogui"


@pytest.mark.parametrize("url", [
    "file:///tmp/mods.json",
    "file:///home/user/Desktop/result.json",
    "file:///home/user/Desktop/mods.json?other=true",
    "file:///home/user/Desktop/mods.json#fragment",
    "file:///home/user/Desktop/../mods.json",
])
def test_json_reference_does_not_allow_other_paths(url):
    with pytest.raises(ValueError):
        parse_gui_actions(response(url), config("/home/user/Desktop/mods.json"))


def test_evaluator_json_is_not_a_declared_reference():
    task = {"evaluator": {"postconfig": config("/home/user/Desktop/metrics.json")["config"]}}
    with pytest.raises(ValueError):
        parse_gui_actions(response("file:///home/user/Desktop/metrics.json"), task)


@pytest.mark.parametrize("extension", ["step", "fcstd", "blend", "ifc", "kicad_pcb"])
def test_uploaded_native_projects_keep_existing_checks(extension):
    path = f"/home/user/Desktop/model.{extension}"
    with pytest.raises(ValueError):
        parse_gui_actions(response("file://" + path), config(path))


def test_json_reference_does_not_skip_other_action_checks():
    xml = response("file:///home/user/Desktop/mods.json").replace(
        "import pyautogui", "import pyautogui\nimport subprocess\nsubprocess.run(['whoami'])"
    )
    with pytest.raises(ValueError):
        parse_gui_actions(xml, config("/home/user/Desktop/mods.json"))
