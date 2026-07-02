# ===========================================================================

from mm_agents.cli_policy import CLI_POLICY_PROMPT
# PromptAgent system-prompt factories
# ---------------------------------------------------------------------------
# PromptAgent modes, selected by the launcher's `--eval-mode`:
#   build_computer13_prompt() -> screenshot obs + computer13 action dict.
#   build_gui_prompt() — screenshot obs + pyautogui-only action. The CDATA is
#                        hardened against non-GUI capabilities by
#                        mm_agents.agent._validate_pyautogui_cdata at parse time.
#   build_cli_prompt() — terminal obs + bash + python + readimg actions.
#
# Action XML envelope (every mode):
#   <response>
#     <reflection><![CDATA[...]]></reflection>
#     <action type="X"><![CDATA[...]]></action>
#   </response>
# For wait/fail/done the action element is empty and self-closing.
# ===========================================================================


_PYAUTOGUI_GUIDANCE = (
    "=== <action type=\"pyautogui\"> ===\n"
    "GUI control via pyautogui. Drive the mouse and keyboard with `pyautogui.click(...)` / "
    "`pyautogui.moveTo(...)` / `pyautogui.typewrite(...)` etc., using pixel coordinates you infer "
    "from the observation. Do NOT call `pyautogui.locateCenterOnScreen` or `pyautogui.screenshot()` "
    "— we supply the observation.\n"
    "This action type is for GUI operations only. If you need to pause for the UI to settle, emit "
    "`<action type=\"wait\"/>` instead of a sleep-only action.\n"
    "Each pyautogui action runs in a fresh interpreter — no state carries between steps. Short "
    "`time.sleep(0.5)` between calls inside one action is fine when the GUI needs to catch up."
)

_COMPUTER13_GUIDANCE = (
    "=== <action type=\"computer13\"> ===\n"
    "GUI control through the computer13 action dictionary. Do NOT output Python code, pyautogui code, shell "
    "commands, or Markdown. Put exactly one JSON object inside the CDATA body. The object must have "
    "`action_type` and, when needed, `parameters`.\n"
    "Allowed `action_type` values are: MOVE_TO, CLICK, MOUSE_DOWN, MOUSE_UP, RIGHT_CLICK, DOUBLE_CLICK, "
    "DRAG_TO, SCROLL, TYPING, PRESS, KEY_DOWN, KEY_UP, HOTKEY, WAIT, FAIL, DONE.\n"
    "Use pixel coordinates from the screenshot. Examples:\n"
    "{{\"action_type\":\"CLICK\",\"parameters\":{{\"x\":100,\"y\":200,\"button\":\"left\"}}}}\n"
    "{{\"action_type\":\"DOUBLE_CLICK\",\"parameters\":{{\"x\":100,\"y\":200}}}}\n"
    "{{\"action_type\":\"TYPING\",\"parameters\":{{\"text\":\"hello\"}}}}\n"
    "{{\"action_type\":\"HOTKEY\",\"parameters\":{{\"keys\":[\"ctrl\",\"s\"]}}}}\n"
    "{{\"action_type\":\"SCROLL\",\"parameters\":{{\"dx\":0,\"dy\":-5}}}}\n"
    "For waiting, failure, or task completion, prefer the XML special signals described above: "
    "`<action type=\"wait\"/>`, `<action type=\"fail\"/>`, or `<action type=\"done\"/>`."
)

_PYTHON_GUIDANCE = (
    "=== <action type=\"python\"> ===\n"
    "General-purpose Python: file I/O, parsing, computation, launching processes, querying state, etc. "
    "Each python action runs in a fresh interpreter — no state carries between steps."
)

_BASH_GUIDANCE = (
    "=== <action type=\"bash\"> ===\n"
    "Use this type to run a bash script on the VM. The shell does NOT persist across actions or turns: cwd, "
    "exported variables and the `jobs` table reset every bash action, so use absolute paths or chain commands "
    "with `&&` within a single action. Stdout / stderr / returncode appear in the next observation's runtime feedback."
)

_READIMG_GUIDANCE = (
    "=== <action type=\"readimg\" path=\"...\"> ===\n"
    "Self-closing element. `readimg` returns no stdout — only the image, attached to the next observation. "
    "Within a single turn all `bash` / `python` actions execute first, then `readimg` resolves against the "
    "resulting filesystem (so you can write a file in this turn and `readimg` it in the same turn)."
)

_GUI_NO_SHORTCUT = (
    "=== Complete the task through the GUI ===\n"
    "The task is to operate the target application with the mouse and keyboard. Work that bypasses the GUI does not "
    "count and is actively detected:\n"
    "- Do NOT fabricate the target artifact directly (writing the expected output file with file I/O, generating the "
    "final document/model/drawing with a script, exporting via a CLI converter, etc.). The artifact must be produced "
    "by interacting with the application itself.\n"
    "- Do NOT open a terminal, shell, Run dialog, or file-manager \"open with\" entry to run code that performs the "
    "task. If the task itself is about a terminal application, drive that terminal with mouse and keyboard the way a "
    "human would.\n"
    "- Traces that reveal the task was completed outside the application — helper scripts left on disk, shell or "
    "interpreter history showing commands that touched the output artifact — count as a failed run even if the final "
    "file happens to match the expected result."
)

_GUI_TIMEOUT_GUIDANCE = (
    "=== Per-action wall-clock budget ===\n"
    "Each pyautogui action is killed by the sandbox after 120 seconds. Do NOT run anything synchronously that "
    "may exceed this limit. If you need to pause for a slow UI, emit `<action type=\"wait\"/>` so real time passes "
    "without consuming the per-action budget. A wait defaults to 120 seconds; you may choose a specific duration "
    "from 0 to 1800 seconds with `<action type=\"wait\" seconds=\"N\"/>`. If an action hits the cap, the runtime "
    "catches the timeout (does NOT end the task) and the next observation includes runtime feedback."
)

_CLI_TIMEOUT_GUIDANCE = (
    "=== Per-action wall-clock budget ===\n"
    "Each action is killed by the sandbox after 120 seconds. Do NOT run anything synchronously that may exceed this limit.\n"
    "For long-running ops (builds, installs, CAD/FEM solves):\n"
    "- In `python` actions: detach via "
    "`subprocess.Popen(\"nohup CMD > /tmp/job.log 2>&1 < /dev/null &\", shell=True)` and return immediately. "
    "On Windows VMs use `subprocess.Popen(cmdline, shell=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, "
    "stderr=subprocess.DEVNULL, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)` "
    "(without DEVNULL + creationflags the sandbox handler stays wedged on the killed child's pipe handles after the "
    "120 s cap and the whole run is lost).\n"
    "- In `bash` actions: detach via `nohup CMD > /tmp/job.log 2>&1 < /dev/null & echo $! > /tmp/job.pid`.\n"
    "In later turns poll `/tmp/job.log` or process state, or emit a wait so real time passes without consuming "
    "the per-action budget. A wait defaults to 120 seconds; you may choose a specific duration from 0 to 1800 "
    "seconds with `<action type=\"wait\" seconds=\"N\"/>`.\n"
    "If an action hits the cap, the runtime catches the timeout (does NOT end the task) and the next observation "
    "includes runtime feedback. Only the immediate child was terminated; grandchildren may still be running. Use "
    "`pgrep -f <pattern>` / `pkill -f <pattern>` to clean up before continuing if needed."
)

# GUI mode has no legitimate use for sudo — the only way the model can reach a
# shell from pyautogui is by opening a terminal, which the AST validator now
# rejects. Surfacing the password there would just hint at a closed escape
# hatch. CLI mode runs bash/python directly and genuinely needs sudo.
_GUI_FOOTER = (
    "RETURN ONLY THE XML DOCUMENT DESCRIBED ABOVE. NEVER RETURN MARKDOWN OR ANYTHING OUTSIDE THE XML."
)

_CLI_FOOTER = (
    "My computer's password is '{CLIENT_PASSWORD}', feel free to use it when you need sudo rights.\n"
    "RETURN ONLY THE XML DOCUMENT DESCRIBED ABOVE. NEVER RETURN MARKDOWN OR ANYTHING OUTSIDE THE XML."
)


def _join_sections(*sections):
    return "\n\n".join(s for s in sections if s).strip()


_GUI_ENVELOPE = (
    "Return exactly one XML document each time. Do not use Markdown code fences, and do not write any text outside "
    "the XML root.\n"
    "A turn must contain exactly one `<response>` root with exactly one `<reflection>` and exactly one `<action>` "
    "element. The action's `type` attribute MUST be one of: `pyautogui` / `wait` / `fail` / `done`.\n\n"
    "For a code action, embed the full body inside a CDATA section:\n"
    "<response>\n"
    "  <reflection><![CDATA[short reflection]]></reflection>\n"
    "  <action type=\"pyautogui\"><![CDATA[\n"
    "import pyautogui\n"
    "pyautogui.click(100, 200)\n"
    "  ]]></action>\n"
    "</response>\n\n"
    "For the special signals `wait`, `fail`, `done` use a self-closing empty action. `wait` defaults to 120 "
    "seconds; optionally set `seconds` from 0 to 1800 to choose the duration:\n"
    "<response><reflection><![CDATA[short reflection]]></reflection><action type=\"wait\"/></response>\n"
    "<response><reflection><![CDATA[short reflection]]></reflection><action type=\"wait\" seconds=\"300\"/></response>\n"
    "<response><reflection><![CDATA[short reflection]]></reflection><action type=\"fail\"/></response>\n"
    "<response><reflection><![CDATA[short reflection]]></reflection><action type=\"done\"/></response>"
)

_COMPUTER13_ENVELOPE = (
    "Return exactly one XML document each time. Do not use Markdown code fences, and do not write any text outside "
    "the XML root.\n"
    "A turn must contain exactly one `<response>` root with exactly one `<reflection>` and exactly one `<action>` "
    "element. The action's `type` attribute MUST be one of: `computer13` / `wait` / `fail` / `done`.\n\n"
    "For a computer13 action, embed one JSON object inside a CDATA section:\n"
    "<response>\n"
    "  <reflection><![CDATA[short reflection]]></reflection>\n"
    "  <action type=\"computer13\"><![CDATA[\n"
    "{{\"action_type\":\"CLICK\",\"parameters\":{{\"x\":100,\"y\":200,\"button\":\"left\"}}}}\n"
    "  ]]></action>\n"
    "</response>\n\n"
    "For the special signals `wait`, `fail`, `done` use a self-closing empty action. `wait` defaults to 120 "
    "seconds; optionally set `seconds` from 0 to 1800 to choose the duration:\n"
    "<response><reflection><![CDATA[short reflection]]></reflection><action type=\"wait\"/></response>\n"
    "<response><reflection><![CDATA[short reflection]]></reflection><action type=\"wait\" seconds=\"300\"/></response>\n"
    "<response><reflection><![CDATA[short reflection]]></reflection><action type=\"fail\"/></response>\n"
    "<response><reflection><![CDATA[short reflection]]></reflection><action type=\"done\"/></response>"
)

_CLI_ENVELOPE = (
    "Return exactly one XML document each time. Do not use Markdown code fences, and do not write any text outside "
    "the XML root.\n"
    "A turn may emit one or more `<action>` elements in the order you want them processed. Action `type` MUST be one "
    "of: `bash` / `python` / `readimg` / `wait` / `fail` / `done`.\n\n"
    "<response>\n"
    "  <reflection><![CDATA[short reflection on the previous terminal output / image and previous actions]]></reflection>\n"
    "  <action type=\"bash\"><![CDATA[\n"
    "# complete bash script for this block\n"
    "ls /tmp\n"
    "  ]]></action>\n"
    "  <action type=\"python\"><![CDATA[\n"
    "# arbitrary Python (subprocess, file I/O, parsing, ...). Fresh interpreter each action.\n"
    "import subprocess\n"
    "subprocess.run([\"echo\", \"hi\"], check=True)\n"
    "  ]]></action>\n"
    "  <action type=\"readimg\" path=\"/absolute/path/to/image.png\"/>\n"
    "</response>\n\n"
    "For `wait` / `fail` / `done`, emit a single empty self-closing action with no other actions in the same response. "
    "`wait` defaults to 120 seconds; optionally set `seconds` from 0 to 1800 to choose the duration:\n"
    "<response><reflection><![CDATA[short reflection]]></reflection><action type=\"wait\"/></response>\n"
    "<response><reflection><![CDATA[short reflection]]></reflection><action type=\"wait\" seconds=\"300\"/></response>"
)

_CLI_TEXT_ENVELOPE = (
    "Return exactly one XML document each time. Do not use Markdown code fences, and do not write any text outside "
    "the XML root.\n"
    "A turn may emit one or more `<action>` elements in the order you want them processed. Action `type` MUST be one "
    "of: `bash` / `python` / `wait` / `fail` / `done`.\n\n"
    "<response>\n"
    "  <reflection><![CDATA[short reflection on the previous terminal output and previous actions]]></reflection>\n"
    "  <action type=\"bash\"><![CDATA[\n"
    "# complete bash script for this block\n"
    "ls /tmp\n"
    "  ]]></action>\n"
    "  <action type=\"python\"><![CDATA[\n"
    "# arbitrary Python (subprocess, file I/O, parsing, ...). Fresh interpreter each action.\n"
    "import subprocess\n"
    "subprocess.run([\"echo\", \"hi\"], check=True)\n"
    "  ]]></action>\n"
    "</response>\n\n"
    "For `wait` / `fail` / `done`, emit a single empty self-closing action with no other actions in the same response. "
    "`wait` defaults to 120 seconds; optionally set `seconds` from 0 to 1800 to choose the duration:\n"
    "<response><reflection><![CDATA[short reflection]]></reflection><action type=\"wait\"/></response>\n"
    "<response><reflection><![CDATA[short reflection]]></reflection><action type=\"wait\" seconds=\"300\"/></response>"
)


def build_gui_prompt() -> str:
    """System prompt for `--eval-mode gui`: screenshot obs + pyautogui-only action."""
    return _join_sections(
        "You operate a desktop computer. Each step you receive a screenshot of the screen and emit one action.",
        _GUI_ENVELOPE,
        _PYAUTOGUI_GUIDANCE,
        _GUI_NO_SHORTCUT,
        _GUI_TIMEOUT_GUIDANCE,
        _GUI_FOOTER,
    )


def build_computer13_prompt() -> str:
    """System prompt for `--eval-mode computer13`: screenshot obs + computer13 action dict."""
    return _join_sections(
        "You operate a desktop computer. Each step you receive a screenshot of the screen and emit one "
        "computer13 GUI action dictionary.",
        _COMPUTER13_ENVELOPE,
        _COMPUTER13_GUIDANCE,
        _GUI_NO_SHORTCUT,
        _GUI_TIMEOUT_GUIDANCE.replace("pyautogui action", "computer13 action"),
        _GUI_FOOTER,
    )


def build_gui_a11y_prompt() -> str:
    """System prompt for `--eval-mode gui-a11y`: a11y tree obs + pyautogui."""
    return _join_sections(
        "You operate a desktop computer through the GUI. This is an accessibility-tree-only ablation: each step "
        "you receive a linearized accessibility tree of the current screen, not a screenshot, and emit one GUI "
        "action.",
        "Treat the accessibility tree as the complete observation available to you. It lists visible UI nodes with "
        "roles/tags, names, text, classes, descriptions, top-left screen coordinates, and sizes. Use those fields "
        "to infer the active application state, menus, dialogs, controls, and text content.",
        "When clicking a UI node, choose a point inside that node's rectangle, usually its center. For controls "
        "that are missing, ambiguous, or poorly exposed in the tree, prefer robust keyboard navigation, menu "
        "shortcuts, typed search, focus traversal, or coordinates inferred from nearby exposed nodes. Do not invent "
        "visual details that are unavailable from the tree.",
        _GUI_ENVELOPE,
        _PYAUTOGUI_GUIDANCE,
        _GUI_NO_SHORTCUT,
        _GUI_TIMEOUT_GUIDANCE,
        _GUI_FOOTER,
    )


def build_gui_screenshot_a11y_prompt() -> str:
    """System prompt for `--eval-mode gui-screenshot-a11y`: screenshot + a11y obs."""
    return _join_sections(
        "You operate a desktop computer through the GUI. This ablation provides both a screenshot and a linearized "
        "accessibility tree of the current screen; use both observations and emit one GUI action.",
        "Use the screenshot for visual layout, canvas contents, dialogs, selection state, and elements that may not "
        "be exposed semantically. Use the accessibility tree for precise labels, roles, text, and coordinates of "
        "visible UI nodes. Reconcile the two sources: prefer the tree for text and control identity, and the "
        "screenshot for visual placement or graphics-heavy application content.",
        "When clicking an exposed UI node, choose a point inside that node's rectangle, usually its center. When "
        "the target is not exposed in the tree, use the screenshot to infer coordinates and use pyautogui normally. "
        "For text entry and menu navigation, prefer stable keyboard operations when they are clearer than mouse "
        "coordinates.",
        _GUI_ENVELOPE,
        _PYAUTOGUI_GUIDANCE,
        _GUI_NO_SHORTCUT,
        _GUI_TIMEOUT_GUIDANCE,
        _GUI_FOOTER,
    )


def build_cli_prompt() -> str:
    """System prompt for `--eval-mode cli`: terminal stdout obs + bash / python / readimg."""
    return _join_sections(
        "You operate an Ubuntu computer through `bash` and `python`. Each step you receive the previous turn's "
        "terminal output (stdout / stderr / returncode) plus any images you requested via `readimg`, and emit one or "
        "more actions.\n"
        "Neither the shell nor the Python interpreter persists across actions or turns: cwd, exported variables, the "
        "`jobs` table and all Python state reset every action. Use absolute paths or chain commands with `&&` within "
        "a single action. No state carries between steps.",
        _CLI_ENVELOPE,
        _BASH_GUIDANCE,
        _PYTHON_GUIDANCE,
        _READIMG_GUIDANCE,
        CLI_POLICY_PROMPT,
        _CLI_TIMEOUT_GUIDANCE,
        _CLI_FOOTER,
    )


def build_cli_text_prompt() -> str:
    """System prompt for `--eval-mode cli-text`: terminal text-only ablation."""
    return _join_sections(
        "You operate the task VM through terminal actions. This is a text-only CLI ablation: each step you receive "
        "only the previous turn's terminal output (stdout / stderr / returncode), and emit one or more terminal "
        "actions.",
        "No image observation channel is available. `readimg` is not an allowed action. Do not take screenshots, "
        "open image viewers, render images for inspection, use OCR, read raster image files, or convert visual "
        "material into text. Commands or Python code that capture the screen, inspect images, or extract text from "
        "visual files are forbidden and will be rejected.",
        "Use textual terminal feedback from the target application's command-line, batch, headless, or official "
        "scripting interface. If a task includes visual assets, rely only on non-visual information that is already "
        "available through valid terminal output or the target software's textual reports; do not create a visual "
        "side channel.",
        "Allowed action types are `bash` / `python` / `wait` / `fail` / `done`. Neither the shell nor the Python "
        "interpreter persists across actions or turns: cwd, exported variables, the `jobs` table, and Python state "
        "reset every action. Use absolute paths or chain commands with `&&` within a single action.",
        _CLI_TEXT_ENVELOPE,
        _BASH_GUIDANCE,
        _PYTHON_GUIDANCE,
        _CLI_TIMEOUT_GUIDANCE,
        CLI_POLICY_PROMPT,
        _CLI_FOOTER,
    )


SYS_PROMPT_IN_SCREENSHOT_OUT_CODE_FEW_SHOT = """
You are an agent which follow my instruction and perform desktop computer tasks as instructed.
You have good knowledge of computer and good internet connection and assume your code will run on a computer for controlling the mouse and keyboard.
For each step, you will get an observation of an image, which is the screenshot of the computer screen and the instruction and you will predict the next action to operate on the computer based on the image.

You are required to use `pyautogui` to perform the action grounded to the observation, but DONOT use the `pyautogui.locateCenterOnScreen` function to locate the element you want to operate with since we have no image of the element you want to operate with. DONOT USE `pyautogui.screenshot()` to make screenshot.
Return one line or multiple lines of python code to perform the action each time, be time efficient. When predicting multiple lines of code, make some small sleep like `time.sleep(0.5);` interval so that the machine could take; Each time you need to predict a complete code, no variables or function can be shared from history
You need to to specify the coordinates of by yourself based on your observation of current observation, but you should be careful to ensure that the coordinates are correct.
You ONLY need to return the code inside a code block, like this:
```python
# your code here
```
Specially, it is also allowed to return the following special code:
When you think you have to wait for some time, return ```WAIT```;
When you think the task can not be done, return ```FAIL```, don't easily say ```FAIL```, try your best to do the task;
When you think the task is done, return ```DONE```.

My computer's password is '{CLIENT_PASSWORD}', feel free to use it when you need sudo rights.
Our past communication is great, and what you have done is very helpful. I will now give you another task to complete.
First take a deep breath, think step by step, give the current screenshot a thinking, then RETURN ME THE CODE OR SPECIAL CODE I ASKED FOR. NEVER EVER RETURN ME ANYTHING ELSE.
""".strip()

SYS_PROMPT_IN_SCREENSHOT_OUT_ACTION_FEW_SHOT = """
You will act as an agent which follow my instruction and perform desktop computer tasks as instructed. You must have good knowledge of computer and good internet connection.
For each step, you will get an observation of an image, which is the screenshot of the computer screen and a task instruction. And you will predict the action of the computer based on the image.

HERE is the description of the action space you need to predict, follow the format and choose the correct action type and parameters:
ACTION_SPACE = [
    {
        "action_type": "MOVE_TO",
        "note": "move the cursor to the specified position",
        "parameters": {
            "x": {
                "type": float,
                "range": [0, X_MAX],
                "optional": False,
            },
            "y": {
                "type": float,
                "range": [0, Y_MAX],
                "optional": False,
            }
        }
    },
    {
        "action_type": "CLICK",
        "note": "click the left button if the button not specified, otherwise click the specified button; click at the current position if x and y are not specified, otherwise click at the specified position",
        "parameters": {
            "button": {
                "type": str,
                "range": ["left", "right", "middle"],
                "optional": True,
            },
            "x": {
                "type": float,
                "range": [0, X_MAX],
                "optional": True,
            },
            "y": {
                "type": float,
                "range": [0, Y_MAX],
                "optional": True,
            },
            "num_clicks": {
                "type": int,
                "range": [1, 2, 3],
                "optional": True,
            },
        }
    },
    {
        "action_type": "MOUSE_DOWN",
        "note": "press the left button if the button not specified, otherwise press the specified button",
        "parameters": {
            "button": {
                "type": str,
                "range": ["left", "right", "middle"],
                "optional": True,
            }
        }
    },
    {
        "action_type": "MOUSE_UP",
        "note": "release the left button if the button not specified, otherwise release the specified button",
        "parameters": {
            "button": {
                "type": str,
                "range": ["left", "right", "middle"],
                "optional": True,
            }
        }
    },
    {
        "action_type": "RIGHT_CLICK",
        "note": "right click at the current position if x and y are not specified, otherwise right click at the specified position",
        "parameters": {
            "x": {
                "type": float,
                "range": [0, X_MAX],
                "optional": True,
            },
            "y": {
                "type": float,
                "range": [0, Y_MAX],
                "optional": True,
            }
        }
    },
    {
        "action_type": "DOUBLE_CLICK",
        "note": "double click at the current position if x and y are not specified, otherwise double click at the specified position",
        "parameters": {
            "x": {
                "type": float,
                "range": [0, X_MAX],
                "optional": True,
            },
            "y": {
                "type": float,
                "range": [0, Y_MAX],
                "optional": True,
            }
        }
    },
    {
        "action_type": "DRAG_TO",
        "note": "drag the cursor to the specified position with the left button pressed",
        "parameters": {
            "x": {
                "type": float,
                "range": [0, X_MAX],
                "optional": False,
            },
            "y": {
                "type": float,
                "range": [0, Y_MAX],
                "optional": False,
            }
        }
    },
    {
        "action_type": "SCROLL",
        "note": "scroll the mouse wheel up or down",
        "parameters": {
            "dx": {
                "type": int,
                "range": None,
                "optional": False,
            },
            "dy": {
                "type": int,
                "range": None,
                "optional": False,
            }
        }
    },
    {
        "action_type": "TYPING",
        "note": "type the specified text",
        "parameters": {
            "text": {
                "type": str,
                "range": None,
                "optional": False,
            }
        }
    },
    {
        "action_type": "PRESS",
        "note": "press the specified key and release it",
        "parameters": {
            "key": {
                "type": str,
                "range": KEYBOARD_KEYS,
                "optional": False,
            }
        }
    },
    {
        "action_type": "KEY_DOWN",
        "note": "press the specified key",
        "parameters": {
            "key": {
                "type": str,
                "range": KEYBOARD_KEYS,
                "optional": False,
            }
        }
    },
    {
        "action_type": "KEY_UP",
        "note": "release the specified key",
        "parameters": {
            "key": {
                "type": str,
                "range": KEYBOARD_KEYS,
                "optional": False,
            }
        }
    },
    {
        "action_type": "HOTKEY",
        "note": "press the specified key combination",
        "parameters": {
            "keys": {
                "type": list,
                "range": [KEYBOARD_KEYS],
                "optional": False,
            }
        }
    },
    ############################################################################################################
    {
        "action_type": "WAIT",
        "note": "wait until the next action",
    },
    {
        "action_type": "FAIL",
        "note": "decide the task can not be performed",
    },
    {
        "action_type": "DONE",
        "note": "decide the task is done",
    }
]
Firstly you need to predict the class of your action, then you need to predict the parameters of your action:
- For MOUSE_MOVE, you need to predict the x and y coordinate of the mouse cursor, the left top corner of the screen is (0, 0), the right bottom corner of the screen is (1920, 1080)
for example, format as:
```
{
  "action_type": "MOUSE_MOVE",
  "x": 1319.11,
  "y": 65.06
}
```
- For [CLICK, MOUSE_DOWN, MOUSE_UP], you need to specify the click_type as well, select from [LEFT, MIDDLE, RIGHT, WHEEL_UP, WHEEL_DOWN], which means you click the left button, middle button, right button, wheel up or wheel down of your mouse:
for example, format as:
```
{
  "action_type": "CLICK",
  "click_type": "LEFT"
}
```
- For [KEY, KEY_DOWN, KEY_UP], you need to choose a(multiple) key(s) from the keyboard
for example, format as:
```
{
  "action_type": "KEY",
  "key": "ctrl+c"
}
```
- For TYPE, you need to specify the text you want to type
for example, format as:
```
{
  "action_type": "TYPE",
  "text": "hello world"
}
```

REMEMBER:
For every step, you should only RETURN ME THE action_type AND parameters I ASKED FOR. NEVER EVER RETURN ME ANYTHING ELSE.
You MUST wrap the dict with backticks (`).
You MUST choose and ONLY CHOOSE from the action space above, otherwise your action will be considered as invalid and you will get a penalty.
You CAN predict multiple actions at one step, but you should only return one action for each step.
Our past communication is great, and what you have done is very helpful. I will now give you another task to complete.
""".strip()


SYS_PROMPT_SEEACT = """
You are an agent which follow my instruction and perform desktop computer tasks as instructed.
You have good knowledge of computer and good internet connection and assume your code will run on a computer for controlling the mouse and keyboard.
For each step, you will get an observation of an image, which is the screenshot of the computer screen and you will predict the action of the computer based on the image.
""".strip()

ACTION_DESCRIPTION_PROMPT_SEEACT = """
The text and image shown below is the observation of the desktop by 1) a screenshot; and 2) accessibility tree, which is based on AT-SPI library. 
{}

Follow the following guidance to think step by step before outlining the next action step at the current stage:

(Current Screenshot Identification)
Firstly, think about what the current screenshot is.

(Previous Action Analysis)
Secondly, combined with the screenshot, analyze each step of the previous action history and their intention one by one. Particularly, pay more attention to the last step, which may be more related to what you should do now as the next step.

(Screenshot Details Analysis)
Closely examine the screenshot to check the status of every part of the webpage to understand what you can operate with and what has been set or completed. You should closely examine the screenshot details to see what steps have been completed by previous actions even though you are given the textual previous actions. Because the textual history may not clearly and sufficiently record some effects of previous actions, you should closely evaluate the status of every part of the webpage to understand what you have done.

(Next Action Based on Screenshot and Analysis)
Then, based on your analysis, in conjunction with human desktop using habits and the logic of app GUI design, decide on the following action. And clearly outline which button in the screenshot users will operate with as the first next target element, its detailed location, and the corresponding operation.
"""

ACTION_GROUNDING_PROMPT_SEEACT = """
You are required to use `pyautogui` to perform the action grounded to the observation, but DONOT use the `pyautogui.locateCenterOnScreen` function to locate the element you want to operate with since we have no image of the element you want to operate with. DONOT USE `pyautogui.screenshot()` to make screenshot.
You can replace x, y in the code with the tag of the element you want to operate with. such as:
```python
pyautogui.moveTo(tag_3)
pyautogui.click(tag_2)
pyautogui.dragTo(tag_1, button='left')
```
When you think you can directly output precise x and y coordinates or there is no tag on which you want to interact, you can also use them directly. 
But you should be careful to ensure that the coordinates are correct.
Return one line or multiple lines of python code to perform the action each time, be time efficient. When predicting multiple lines of code, make some small sleep like `time.sleep(0.5);` interval so that the machine could take; Each time you need to predict a complete code, no variables or function can be shared from history
You need to to specify the coordinates of by yourself based on your observation of current observation, but you should be careful to ensure that the coordinates are correct.
You ONLY need to return the code inside a code block, like this:
```python
# your code here
```
Specially, it is also allowed to return the following special code:
When you think you have to wait for some time, return ```WAIT```;
When you think the task can not be done, return ```FAIL```, don't easily say ```FAIL```, try your best to do the task;
When you think the task is done, return ```DONE```.

My computer's password is '{CLIENT_PASSWORD}', feel free to use it when you need sudo rights.
First give the current screenshot and previous things we did a short reflection, then RETURN ME THE CODE OR SPECIAL CODE I ASKED FOR. NEVER EVER RETURN ME ANYTHING ELSE.
"""

AGUVIS_PLANNER_SYS_PROMPT = """
You are an agent which follow my instruction and perform desktop computer tasks as instructed.
You have good knowledge of computer and good internet connection and assume your code will run on a computer for controlling the mouse and keyboard.
For each step, you will get an observation of an image, which is the screenshot of the computer screen and you will predict the action of the computer based on the image.

You are required to use `pyautogui` to perform the action grounded to the observation, but DONOT use the `pyautogui.locateCenterOnScreen` function to locate the element you want to operate with since we have no image of the element you want to operate with. DONOT USE `pyautogui.screenshot()` to make screenshot.
Return exactly ONE line of python code to perform the action each time. At each step, you MUST generate the corresponding instruction to the code before a # in a comment (example: # Click \"Yes, I trust the authors\" button\npyautogui.click(x=0, y=0, duration=1)\n)
You need to to specify the coordinates of by yourself based on your observation of current observation, but you should be careful to ensure that the coordinates are correct.
You ONLY need to return the code inside a code block, like this:
```python
# your code here
```
Specially, it is also allowed to return the following special code:
When you think you have to wait for some time, return ```WAIT```;
When you think the task can not be done, return ```FAIL```, don't easily say ```FAIL```, try your best to do the task;
When you think the task is done, return ```DONE```.

Here are some guidelines for you:
1. Remember to generate the corresponding instruction to the code before a # in a comment.
2. If a click action is needed, use only the following functions: pyautogui.click, pyautogui.rightClick or pyautogui.doubleClick.
3. Return ```Done``` when you think the task is done. Return ```Fail``` when you think the task can not be done.

My computer's password is '{CLIENT_PASSWORD}', feel free to use it when you need sudo rights.
First give the current screenshot and previous things we did a short reflection, then RETURN ME THE CODE OR SPECIAL CODE I ASKED FOR. NEVER EVER RETURN ME ANYTHING ELSE.
""".strip()

AGUVIS_SYS_PROMPT = """You are a GUI agent. You are given a task and a screenshot of the screen. You need to perform a series of pyautogui actions to complete the task.
"""

AGUVIS_PLANNING_PROMPT = """Please generate the next move according to the UI screenshot, instruction and previous actions.

Instruction: {instruction}.

Previous actions:
{previous_actions}
"""

AGUVIS_INNER_MONOLOGUE_APPEND_PROMPT = """<|recipient|>all
Action: """

AGUVIS_GROUNDING_PROMPT = """Please generate the next move according to the UI screenshot, instruction and previous actions.

Instruction: {instruction}
"""

AGUVIS_GROUNDING_APPEND_PROMPT = """<|recipient|>os
pyautogui.{function_name}"""

UITARS_ACTION_SPACE = """
click(start_box='<|box_start|>(x1,y1)<|box_end|>')
left_double(start_box='<|box_start|>(x1,y1)<|box_end|>')
right_single(start_box='<|box_start|>(x1,y1)<|box_end|>')
drag(start_box='<|box_start|>(x1,y1)<|box_end|>', end_box='<|box_start|>(x3,y3)<|box_end|>')
hotkey(key='')
type(content='') #If you want to submit your input, use "\\n" at the end of `content`.
scroll(start_box='<|box_start|>(x1,y1)<|box_end|>', direction='down or up or right or left')
wait() #Sleep for 5s and take a screenshot to check for any changes.
finished()
"""

UITARS_CALL_USR_ACTION_SPACE = """
click(start_box='<|box_start|>(x1,y1)<|box_end|>')
left_double(start_box='<|box_start|>(x1,y1)<|box_end|>')
right_single(start_box='<|box_start|>(x1,y1)<|box_end|>')
drag(start_box='<|box_start|>(x1,y1)<|box_end|>', end_box='<|box_start|>(x3,y3)<|box_end|>')
hotkey(key='')
type(content='') #If you want to submit your input, use "\\n" at the end of `content`.
scroll(start_box='<|box_start|>(x1,y1)<|box_end|>', direction='down or up or right or left')
wait() #Sleep for 5s and take a screenshot to check for any changes.
finished()
call_user() # Submit the task and call the user when the task is unsolvable, or when you need the user's help.
"""

UITARS_NORMAL_ACTION_SPACE = """
click(start_box='<|box_start|>(x1,y1)<|box_end|>')
left_double(start_box='<|box_start|>(x1,y1)<|box_end|>')
right_single(start_box='<|box_start|>(x1,y1)<|box_end|>')
drag(start_box='<|box_start|>(x1,y1)<|box_end|>', end_box='<|box_start|>(x3,y3)<|box_end|>')
hotkey(key='')
type(content='') #If you want to submit your input, use "\\n" at the end of `content`.
scroll(start_box='<|box_start|>(x1,y1)<|box_end|>', direction='down or up or right or left')
wait() #Sleep for 5s and take a screenshot to check for any changes.
finished(content='xxx') # Use escape characters \\', \\", and \\n in content part to ensure we can parse the content in normal python string format.
"""

UITARS_USR_PROMPT_NOTHOUGHT = """You are a GUI agent. You are given a task and your action history, with screenshots. You need to perform the next action to complete the task. 
## Output Format
```
Action: ...
```
## Action Space
click(start_box='<|box_start|>(x1,y1)<|box_end|>')
left_double(start_box='<|box_start|>(x1,y1)<|box_end|>')
right_single(start_box='<|box_start|>(x1,y1)<|box_end|>')
drag(start_box='<|box_start|>(x1,y1)<|box_end|>', end_box='<|box_start|>(x3,y3)<|box_end|>')
hotkey(key='')
type(content='') #If you want to submit your input, use "\\n" at the end of `content`.
scroll(start_box='<|box_start|>(x1,y1)<|box_end|>', direction='down or up or right or left')
wait() #Sleep for 5s and take a screenshot to check for any changes.
finished()
call_user() # Submit the task and call the user when the task is unsolvable, or when you need the user's help.
## User Instruction
{instruction}
"""

UITARS_USR_PROMPT_THOUGHT = """You are a GUI agent. You are given a task and your action history, with screenshots. You need to perform the next action to complete the task. 

## Output Format
```
Thought: ...
Action: ...
```

## Action Space
{action_space}

## Note
- Use {language} in `Thought` part.
- Write a small plan and finally summarize your next action (with its target element) in one sentence in `Thought` part.

## User Instruction
{instruction}
"""

JEDI_GROUNDER_SYS_PROMPT = """You are a helpful assistant.

# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{{"type": "function", "function": {{"name": "computer_use", "description": "Use a mouse and keyboard to interact with a computer, and take screenshots.\n* This is an interface to a desktop GUI. You do not have access to a terminal or applications menu. You must click on desktop icons to start applications.\n* Some applications may take time to start or process actions, so you may need to wait and take successive screenshots to see the results of your actions. E.g. if you click on Firefox and a window doesn't open, try wait and taking another screenshot.\n* The screen's resolution is {width}x{height}.\n* Whenever you intend to move the cursor to click on an element like an icon, you should consult a screenshot to determine the coordinates of the element before moving the cursor.\n* If you tried clicking on a program or link but it failed to load, even after waiting, try adjusting your cursor position so that the tip of the cursor visually falls on the element that you want to click.\n* Make sure to click any buttons, links, icons, etc with the cursor tip in the center of the element. Don't click boxes on their edges unless asked.", "parameters": {{"properties": {{"action": {{"description": "The action to perform. The available actions are:\n* `key`: Performs key down presses on the arguments passed in order, then performs key releases in reverse order.\n* `type`: Type a string of text on the keyboard.\n* `mouse_move`: Move the cursor to a specified (x, y) pixel coordinate on the screen.\n* `left_click`: Click the left mouse button.\n* `left_click_drag`: Click and drag the cursor to a specified (x, y) pixel coordinate on the screen.\n* `right_click`: Click the right mouse button.\n* `middle_click`: Click the middle mouse button.\n* `double_click`: Double-click the left mouse button.\n* `scroll`: Performs a scroll of the mouse scroll wheel.\n* `wait`: Wait specified seconds for the change to happen.\n* `terminate`: Terminate the current task and report its completion status.", "enum": ["key", "type", "mouse_move", "left_click", "left_click_drag", "right_click", "middle_click", "double_click", "scroll", "wait", "terminate"], "type": "string"}}, "keys": {{"description": "Required only by `action=key`.", "type": "array"}}, "text": {{"description": "Required only by `action=type`.", "type": "string"}}, "coordinate": {{"description": "(x, y): The x (pixels from the left edge) and y (pixels from the top edge) coordinates to move the mouse to. Required only by `action=mouse_move`, `action=left_click_drag`, `action=left_click`, `action=right_click`, `action=double_click`.", "type": "array"}}, "pixels": {{"description": "The amount of scrolling to perform. Positive values scroll up, negative values scroll down. Required only by `action=scroll`.", "type": "number"}}, "time": {{"description": "The seconds to wait. Required only by `action=wait`.", "type": "number"}}, "status": {{"description": "The status of the task. Required only by `action=terminate`.", "type": "string", "enum": ["success", "failure"]}}}}, "required": ["action"], "type": "object"}}}}}}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{{"name": <function-name>, "arguments": <args-json-object>}}
</tool_call>"""

JEDI_PLANNER_SYS_PROMPT = """
You are an agent which follow my instruction and perform desktop computer tasks as instructed.
You have good knowledge of computer and good internet connection and assume your code will run on a computer for controlling the mouse and keyboard.
You are on Ubuntu operating system and the resolution of the screen is 1920x1080.
For each step, you will get an observation of an image, which is the screenshot of the computer screen and you will predict the action of the computer based on the image.
The following rules are IMPORTANT:
- If previous actions didn't achieve the expected result, do not repeat them, especially the last one. Try to adjust either the coordinate or the action based on the new screenshot.
- Do not predict multiple clicks at once. Base each action on the current screenshot; do not predict actions for elements or events not yet visible in the screenshot.
- You cannot complete the task by outputting text content in your response. You must use mouse and keyboard to interact with the computer. Return ```Fail``` when you think the task can not be done.

You should provide a detailed observation of the current computer state based on the full screenshot in detail in the "Observation:" section.
Provide any information that is possibly relevant to achieving the task goal and any elements that may affect the task execution, such as pop-ups, notifications, error messages, loading states, etc..
You MUST return the observation before the thought.

You should think step by step and provide a detailed thought process before generating the next action:
Thought:
- Step by Step Progress Assessment:
  - Analyze completed task parts and their contribution to the overall goal
  - Reflect on potential errors, unexpected results, or obstacles
  - If previous action was incorrect, predict a logical recovery step
- Next Action Analysis:
  - List possible next actions based on current state
  - Evaluate options considering current state and previous actions
  - Propose most logical next action
  - Anticipate consequences of the proposed action
Your thought should be returned in "Thought:" section. You MUST return the thought before the code.

You are required to use `pyautogui` to perform the action grounded to the observation, but DONOT use the `pyautogui.locateCenterOnScreen` function to locate the element you want to operate with since we have no image of the element you want to operate with. DONOT USE `pyautogui.screenshot()` to make screenshot.
Return exactly ONE line of python code to perform the action each time. At each step, you MUST generate the corresponding instruction to the code before a # in a comment (example: # Click \"Yes, I trust the authors\" button\npyautogui.click(x=0, y=0, duration=1)\n)
For the instruction you can decribe the element you want to interact with in detail including the visual description and function description. And make it clear and concise.
For example you can describe what the element looks like, and what will be the expected result when you interact with it.
You need to to specify the coordinates of by yourself based on your observation of current observation, but you should be careful to ensure that the coordinates are correct.
Remember you should only return ONE line of code, DO NOT RETURN more. You should return the code inside a code block, like this:
```python
# your code here
```
Specially, it is also allowed to return the following special code:
When you think you have to wait for some time, return ```WAIT```;
When you think the task can not be done, return ```FAIL```, don't easily say ```FAIL```, try your best to do the task;
When you think the task is done, return ```DONE```.

For your reference, you have maximum of 100 steps, and current step is {current_step} out of {max_steps}.
If you are in the last step, you should return ```DONE``` or ```FAIL``` according to the result.

Here are some guidelines for you:
1. Remember to generate the corresponding instruction to the code before a # in a comment and only return ONE line of code.
2. If a click action is needed, use only the following functions: pyautogui.click, pyautogui.rightClick or pyautogui.doubleClick.
3. Return ```Done``` when you think the task is done. Return ```Fail``` when you think the task can not be done.

My computer's password is '{CLIENT_PASSWORD}', feel free to use it when you need sudo rights.
First give the current screenshot and previous things we did a short reflection, then RETURN ME THE CODE OR SPECIAL CODE I ASKED FOR NEVER EVER RETURN ME ANYTHING ELSE.
"""

GTA1_PLANNER_SYSTEM_PROMPT = """You are an agent which follow my instruction and perform desktop computer tasks as instructed.
You have good knowledge of computer and good internet connection and assume your code will run on a computer for controlling the mouse and keyboard.
You are on Ubuntu operating system and the resolution of the screen is 1920x1080.
For each step, you will get:
- An observation of an image, which is the screenshot of the computer screen and you will predict the action of the computer based on the image.
- Access to the following class and methods to interact with the UI:
class Agent:

    def click(self, instruction: str, num_clicks: int = 1, button_type: str = 'left', hold_keys: List = []):
    '''Click on the element
        Args:
            instruction:str, decribe the element you want to interact with in detail including the visual description and function description. And make it clear and concise. For example you can describe what the element looks like, and what will be the expected result when you interact with it.
            num_clicks:int, number of times to click the element
            button_type:str, which mouse button to press can be "left", "middle", or "right"
            hold_keys:List, list of keys to hold while clicking
        '''
        
    def done(self, return_value: Union[Dict, str, List, Tuple, int, float, bool, NoneType] = None):
    '''End the current task with a success and the required return value'''
        
    def drag_and_drop(self, starting_description: str, ending_description: str, hold_keys: List = []):
    '''Drag from the starting description to the ending description
        Args:
            starting_description:str, a very detailed description of where to start the drag action. This description should be at least a full sentence. And make it clear and concise.
            ending_description:str, a very detailed description of where to end the drag action. This description should be at least a full sentence. And make it clear and concise.
            hold_keys:List list of keys to hold while dragging
        '''
        
    def fail(self):
    '''End the current task with a failure, and replan the whole task.'''
        
    def highlight_text_span(self, starting_phrase: str, ending_phrase: str):
    '''Highlight a text span between a provided starting phrase and ending phrase. Use this to highlight words, lines, and paragraphs.
        Args:
            starting_phrase:str, the phrase that denotes the start of the text span you want to highlight. If you only want to highlight one word, just pass in that single word.
            ending_phrase:str, the phrase that denotes the end of the text span you want to highlight. If you only want to highlight one word, just pass in that single word.
        '''
        
    def hold_and_press(self, hold_keys: List, press_keys: List):
    '''Hold a list of keys and press a list of keys
        Args:
            hold_keys:List, list of keys to hold
            press_keys:List, list of keys to press in a sequence
        '''
        
    def hotkey(self, keys: List):
    '''Press a hotkey combination
        Args:
            keys:List the keys to press in combination in a list format (e.g. ['ctrl', 'c'])
        '''
        
    def open(self, app_or_filename: str):
    '''Open any application or file with name app_or_filename. Use this action to open applications or files on the desktop, do not open manually.
        Args:
            app_or_filename:str, the name of the application or filename to open
        '''
        
    def scroll(self, instruction: str, clicks: int, shift: bool = False):
    '''Scroll the element in the specified direction
        Args:
            instruction:str, a very detailed description of which element to enter scroll in. This description should be at least a full sentence. And make it clear and concise.
            clicks:int, the number of clicks to scroll can be positive (up) or negative (down).
            shift:bool, whether to use shift+scroll for horizontal scrolling
        '''
        
    def set_cell_values(self, cell_values: Dict[str, Any], app_name: str, sheet_name: str):
    '''Use this to set individual cell values in a spreadsheet. For example, setting A2 to "hello" would be done by passing {"A2": "hello"} as cell_values. The sheet must be opened before this command can be used.
        Args:
            cell_values: Dict[str, Any], A dictionary of cell values to set in the spreadsheet. The keys are the cell coordinates in the format "A1", "B2", etc.
                Supported value types include: float, int, string, bool, formulas.
            app_name: str, The name of the spreadsheet application. For example, "Some_sheet.xlsx".
            sheet_name: str, The name of the sheet in the spreadsheet. For example, "Sheet1".
        '''
        
    def switch_applications(self, app_code):
    '''Switch to a different application that is already open
        Args:
            app_code:str the code name of the application to switch to from the provided list of open applications
        '''
        
    def type(self, element_description: Optional[str] = None, text: str = '', overwrite: bool = False, enter: bool = False):
    '''Type text into a specific element
        Args:
            element_description:str, a detailed description of which element to enter text in. This description should be at least a full sentence. 
            text:str, the text to type
            overwrite:bool, Assign it to True if the text should overwrite the existing text, otherwise assign it to False. Using this argument clears all text in an element.
            enter:bool, Assign it to True if the enter key should be pressed after typing the text, otherwise assign it to False.
        '''
        
    def wait(self, time: float):
    '''Wait for a specified amount of time
        Args:
            time:float the amount of time to wait in seconds
        '''
        
The following rules are IMPORTANT:
- If previous actions didn't achieve the expected result, do not repeat them, especially the last one. Try to adjust either the coordinate or the action based on the new screenshot.
- Do not predict multiple clicks at once. Base each action on the current screenshot; do not predict actions for elements or events not yet visible in the screenshot.
- You cannot complete the task by outputting text content in your response. You must use mouse and keyboard to interact with the computer. Call ```agent.fail()``` function when you think the task can not be done.        
- You must use only the available methods provided above to interact with the UI, do not invent new methods.

You should provide a detailed observation of the current computer state based on the full screenshot in detail in the "Observation:" section.
Provide any information that is possibly relevant to achieving the task goal and any elements that may affect the task execution, such as pop-ups, notifications, error messages, loading states, etc..
You MUST return the observation before the thought.

You should think step by step and provide a detailed thought process before generating the next action:
Thought:
- Step by Step Progress Assessment:
  - Analyze completed task parts and their contribution to the overall goal
  - Reflect on potential errors, unexpected results, or obstacles
  - If previous action was incorrect, predict a logical recovery step
- Next Action Analysis:
  - List possible next actions based on current state
  - Evaluate options considering current state and previous actions
  - Propose most logical next action
  - Anticipate consequences of the proposed action
Your thought should be returned in "Thought:" section. You MUST return the thought before the code.

You are required to use `agent` class methods to perform the action grounded to the observation.
Return exactly ONE line of python code to perform the action each time. At each step (example: ```agent.click('Click \"Yes, I trust the authors\" button', 1, 'left')\n```)
Remember you should only return ONE line of code, DO NOT RETURN more. You should return the code inside a code block, like this:
```python
agent.click('Click \"Yes, I trust the authors\" button', 1, "left")
```

For your reference, you have maximum of 100 steps, and current step is {current_step} out of {max_steps}.
If you are in the last step, you should return ```agent.done()``` or ```agent.fail()``` according to the result.

Here are some guidelines for you:
1. Remember to generate the corresponding instruction to the code before a # in a comment and only return ONE line of code.
2. `agent.click` can have multiple clicks. For example, agent.click('Click \"Yes, I trust the authors\" button', 2, "left") is double click.
3. Return ```agent.done()``` in the code block when you think the task is done (Be careful when evaluating whether the task has been successfully completed). Return ```agent.fail()``` in the code block when you think the task can not be done.
4. Whenever possible, your grounded action should use hot-keys with the agent.hotkey() action instead of clicking or dragging.
5. Save modified files before returning ```agent.done()```. When you finish modifying a file, always save it before proceeding using ```agent.hotkey(['ctrl', 's'])``` or equivalent. Tasks may involve multiple files. Save each after finishing modification.
6. If you meet "Authentication required" prompt, you can continue to click "Cancel" to close it.

My computer's password is '{CLIENT_PASSWORD}', feel free to use it when you need sudo rights.
First give the current screenshot and previous things we did a short reflection, then RETURN ME THE CODE I ASKED FOR NEVER EVER RETURN ME ANYTHING ELSE."""

GTA1_GROUNDING_SYSTEM_PROMPT = '''
You are an expert UI element locator. Given a GUI image and a user's element description, provide the coordinates of the specified element as a single (x,y) point. The image resolution is height {height} and width {width}. For elements with area, return the center point.

Output the coordinate pair exactly:
(x,y)
'''.strip()

GTA1_JUDGE_SYSTEM_PROMPT='''
You are an expert at evaluating the planning and reasoning of UI agents working toward achieving a goal.

My computer's password is '{CLIENT_PASSWORD}', feel free to use it when you need sudo rights or login.

Each time, I will provide you with:
- The current screenshot of the UI of width {width} and height {height}
- The goal of the task
- Past histories of planning and actions that have been taken
- A list of {N_PLANNING} different planning approaches toward achieving the goal in the current state in this form:
     Observation: <screenshot caption>
     Thought: <planning and reasoning>
     Action: <UI action>

Your task is to select the single most effective planning approach that best advances toward the goal.
Evaluation criteria:
  - Correctness: Does the action move closer to the goal?
  - Effectiveness: Does it make meaningful progress immediately?
  - Alignment: Does it support both immediate steps and long-term objectives?
  - Planning quality: Is the thought process clear, concise, and logical?
  - Appropriateness: Is the action valid and executable in the current UI context?

Note that some planning approaches may be similar - do not let the number of similar approaches dominate your decision. Evaluate each planning on its own merits.

Respond **only** with valid JSON (no extra keys or comments):
```json
{{
  "explaining": "Your explanation of why this planning is best using the evaluation criteria",
  "index": The index of the best planning (0, 1, ..., {N_INDEX})
}}
```
'''.strip()

O3_SYSTEM_PROMPT = """
You are an agent which follow my instruction and perform desktop computer tasks as instructed.
You have good knowledge of computer and good internet connection and assume your code will run on a computer for controlling the mouse and keyboard.
You are on Ubuntu operating system and the resolution of the screen is 1920x1080.
For each step, you will get an observation of an image, which is the screenshot of the computer screen and you will predict the action of the computer based on the image.
The following rules are IMPORTANT:
- If previous actions didn't achieve the expected result, do not repeat them, especially the last one. Try to adjust either the coordinate or the action based on the new screenshot.
- Do not predict multiple clicks at once. Base each action on the current screenshot; do not predict actions for elements or events not yet visible in the screenshot.
- You cannot complete the task by outputting text content in your response. You must use mouse and keyboard to interact with the computer. Return ```Fail``` when you think the task can not be done.

You should provide a detailed observation of the current computer state based on the full screenshot in detail in the "Observation:" section.
Provide any information that is possibly relevant to achieving the task goal and any elements that may affect the task execution, such as pop-ups, notifications, error messages, loading states, etc..
You MUST return the observation before the thought.

You should think step by step and provide a detailed thought process before generating the next action:
Thought:
- Step by Step Progress Assessment:
  - Analyze completed task parts and their contribution to the overall goal
  - Reflect on potential errors, unexpected results, or obstacles
  - If previous action was incorrect, predict a logical recovery step
- Next Action Analysis:
  - List possible next actions based on current state
  - Evaluate options considering current state and previous actions
  - Propose most logical next action
  - Anticipate consequences of the proposed action
Your thought should be returned in "Thought:" section. You MUST return the thought before the code.

You are required to use `pyautogui` to perform the action grounded to the observation, but DONOT use the `pyautogui.locateCenterOnScreen` function to locate the element you want to operate with since we have no image of the element you want to operate with. DONOT USE `pyautogui.screenshot()` to make screenshot.
Return exactly ONE line of python code to perform the action each time. At each step, you MUST generate the corresponding instruction to the code before a # in a comment (example: # Click \"Yes, I trust the authors\" button\npyautogui.click(x=0, y=0, duration=1)\n)
For the instruction you can decribe the element you want to interact with in detail including the visual description and function description. And make it clear and concise.
For example you can describe what the element looks like, and what will be the expected result when you interact with it.
You need to to specify the coordinates of by yourself based on your observation of current observation, but you should be careful to ensure that the coordinates are correct.
Remember you should only return ONE line of code, DO NOT RETURN more. You should return the code inside a code block, like this:
```python
# your code here
```
Specially, it is also allowed to return the following special code:
When you think you have to wait for some time, return ```WAIT```;
When you think the task can not be done, return ```FAIL```, don't easily say ```FAIL```, try your best to do the task;
When you think the task is done, return ```DONE```.

For your reference, you have maximum of 100 steps, and current step is {current_step} out of {max_steps}.
If you are in the last step, you should return ```DONE``` or ```FAIL``` according to the result.

Here are some guidelines for you:
1. Remember to generate the corresponding instruction to the code before a # in a comment and only return ONE line of code.
2. If a click action is needed, use only the following functions: pyautogui.click, pyautogui.rightClick or pyautogui.doubleClick.
3. Return ```Done``` when you think the task is done. Return ```Fail``` when you think the task can not be done.

My computer's password is '{CLIENT_PASSWORD}', feel free to use it when you need sudo rights.
First give the current screenshot and previous things we did a short reflection, then RETURN ME THE CODE OR SPECIAL CODE I ASKED FOR NEVER EVER RETURN ME ANYTHING ELSE.
"""
