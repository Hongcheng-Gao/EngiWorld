import ast
import base64
import json
import logging
import os
import re
import tempfile
import textwrap
import time
import xml.etree.ElementTree as ET
from http import HTTPStatus
from io import BytesIO
from typing import Any, Dict, FrozenSet, List, Optional, Tuple
from dotenv import load_dotenv

import backoff
import dashscope
import google.generativeai as genai
import openai
import requests
import tiktoken
from PIL import Image
from google.api_core.exceptions import InvalidArgument, ResourceExhausted, InternalServerError, BadRequest
from groq import Groq
from requests.exceptions import SSLError

from mm_agents._llm_retry import EmptyResponseError, make_llm_retry
from mm_agents._rate_limit import acquire_rpm_slot
from mm_agents.accessibility_tree_wrap.heuristic_retrieve import filter_nodes, draw_bounding_boxes
from mm_agents.prompts import (
    build_gui_prompt,
    build_computer13_prompt,
    build_gui_a11y_prompt,
    build_gui_screenshot_a11y_prompt,
    build_cli_prompt,
    build_cli_text_prompt,
)

try:
    from google.genai import errors as _genai_errors
    _GENAI_API_ERROR = _genai_errors.APIError
except Exception:
    class _GENAI_API_ERROR(Exception):  # type: ignore[no-redef]
        """Fallback when google-genai SDK is not installed."""

logger = logging.getLogger("desktopenv.agent")

attributes_ns_ubuntu = "https://accessibility.windows.example.org/ns/attributes"
attributes_ns_windows = "https://accessibility.windows.example.org/ns/attributes"
state_ns_ubuntu = "https://accessibility.ubuntu.example.org/ns/state"
state_ns_windows = "https://accessibility.windows.example.org/ns/state"
component_ns_ubuntu = "https://accessibility.ubuntu.example.org/ns/component"
component_ns_windows = "https://accessibility.windows.example.org/ns/component"
value_ns_ubuntu = "https://accessibility.ubuntu.example.org/ns/value"
value_ns_windows = "https://accessibility.windows.example.org/ns/value"
class_ns_windows = "https://accessibility.windows.example.org/ns/class"
# More namespaces defined in OSWorld, please check desktop_env/server/main.py


# Function to encode the image
def encode_image(image_content):
    return base64.b64encode(image_content).decode('utf-8')


_PIL_FMT_TO_MIME = {
    "png": "image/png",
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "bmp": "image/bmp",
}


def _detect_image_mime(data):
    try:
        with Image.open(BytesIO(data)) as im:
            fmt = (im.format or "").lower()
        return _PIL_FMT_TO_MIME.get(fmt)
    except Exception:
        return None


def _sanitize_for_log(messages):
    """Return a copy of `messages` with base64 image payloads replaced.

    Handles both shapes:
      * OpenAI-style content part: {"type": "image_url", "image_url": {"url": "data:image/...;base64,..."}, "_step": N}
      * Anthropic-style content part: {"type": "image", "source": {"type": "base64", "data": "...", "_step": N}}

    Each image is replaced with the string ``<image step_N>`` (or ``<image>`` if
    the ``_step`` metadata is absent). Non-image fields and structure are
    preserved. The input is not mutated.
    """
    def _tag(step):
        return f"<image step_{step}>" if step is not None else "<image>"

    def _walk(node):
        if isinstance(node, dict):
            ptype = node.get("type")
            if ptype == "image_url" and isinstance(node.get("image_url"), dict):
                return _tag(node.get("_step"))
            if ptype == "image" and isinstance(node.get("source"), dict):
                src = node["source"]
                step = node.get("_step")
                if step is None:
                    step = src.get("_step")
                return _tag(step)
            return {k: _walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [_walk(v) for v in node]
        return node

    return _walk(messages)


def _strip_log_metadata(messages):
    """Remove ``_step`` keys from message content parts in-place.

    Called before sending payloads to vendor APIs so that our log-only
    metadata doesn't leak into the wire format. Most vendors silently ignore
    unknown keys, but we strip explicitly to be safe.
    """
    if not isinstance(messages, list):
        return
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            part.pop("_step", None)
            src = part.get("source")
            if isinstance(src, dict):
                src.pop("_step", None)


def _format_terminal_text(bash_runs, image_paths):
    if not bash_runs and not image_paths:
        return "Terminal observation: no commands have been executed yet."
    parts = []
    for r in bash_runs:
        parts.append("$ " + (r.get("command") or "").rstrip())
        out = (r.get("stdout") or "").rstrip()
        err = (r.get("stderr") or "").rstrip()
        if out:
            parts.append(out)
        if err:
            parts.append("[stderr]\n" + err)
        parts.append("[returncode=%s]" % r.get("returncode"))
    if image_paths:
        parts.append("[readimg attached: %s]" % ", ".join(image_paths))
    return "\n".join(parts)


def encoded_img_to_pil_img(data_str):
    base64_str = data_str.replace("data:image/png;base64,", "")
    image_data = base64.b64decode(base64_str)
    image = Image.open(BytesIO(image_data))

    return image


def save_to_tmp_img_file(data_str):
    base64_str = data_str.replace("data:image/png;base64,", "")
    image_data = base64.b64decode(base64_str)
    image = Image.open(BytesIO(image_data))

    tmp_img_path = os.path.join(tempfile.mkdtemp(), "tmp_img.png")
    image.save(tmp_img_path)

    return tmp_img_path


def linearize_accessibility_tree(accessibility_tree, platform="ubuntu"):

    if platform == "ubuntu":
        _attributes_ns = attributes_ns_ubuntu
        _state_ns = state_ns_ubuntu
        _component_ns = component_ns_ubuntu
        _value_ns = value_ns_ubuntu
    elif platform == "windows":
        _attributes_ns = attributes_ns_windows
        _state_ns = state_ns_windows
        _component_ns = component_ns_windows
        _value_ns = value_ns_windows
    else:
        raise ValueError("Invalid platform, must be 'ubuntu' or 'windows'")

    filtered_nodes = filter_nodes(ET.fromstring(accessibility_tree), platform)
    linearized_accessibility_tree = ["tag\tname\ttext\tclass\tdescription\tposition (top-left x&y)\tsize (w&h)"]

    # Linearize the accessibility tree nodes into a table format
    for node in filtered_nodes:
        if node.text:
            text = (
                node.text if '"' not in node.text \
                    else '"{:}"'.format(node.text.replace('"', '""'))
            )

        elif node.get("{{{:}}}class".format(class_ns_windows), "").endswith("EditWrapper") \
                and node.get("{{{:}}}value".format(_value_ns)):
            node_text = node.get("{{{:}}}value".format(_value_ns), "")
            text = (node_text if '"' not in node_text \
                        else '"{:}"'.format(node_text.replace('"', '""'))
                    )
        else:
            text = '""'

        linearized_accessibility_tree.append(
            "{:}\t{:}\t{:}\t{:}\t{:}\t{:}\t{:}".format(
                node.tag, node.get("name", ""),
                text,
                node.get("{{{:}}}class".format(_attributes_ns), "") if platform == "ubuntu" else node.get("{{{:}}}class".format(class_ns_windows), ""),
                node.get("{{{:}}}description".format(_attributes_ns), ""),
                node.get('{{{:}}}screencoord'.format(_component_ns), ""),
                node.get('{{{:}}}size'.format(_component_ns), "")
            )
        )

    return "\n".join(linearized_accessibility_tree)


def tag_screenshot(screenshot, accessibility_tree, platform="ubuntu"):
    nodes = filter_nodes(ET.fromstring(accessibility_tree), platform=platform, check_image=True)
    # Make tag screenshot
    marks, drew_nodes, element_list, tagged_screenshot = draw_bounding_boxes(nodes, screenshot)

    return marks, drew_nodes, tagged_screenshot, element_list


_PYAUTOGUI_FORBIDDEN_IMPORTS = frozenset({
    "subprocess",
    "pyperclip",
    "tkinter",
})

_PYAUTOGUI_FORBIDDEN_ATTR_CALLS = frozenset({
    ("os", "system"),
    ("os", "popen"), ("os", "popen2"), ("os", "popen3"), ("os", "popen4"),
    ("os", "startfile"),
    ("os", "execl"), ("os", "execle"), ("os", "execlp"), ("os", "execlpe"),
    ("os", "execv"), ("os", "execve"), ("os", "execvp"), ("os", "execvpe"),
    ("os", "spawnl"), ("os", "spawnle"), ("os", "spawnlp"), ("os", "spawnlpe"),
    ("os", "spawnv"), ("os", "spawnve"), ("os", "spawnvp"), ("os", "spawnvpe"),
    ("subprocess", "run"),
    ("subprocess", "Popen"),
    ("subprocess", "call"),
    ("subprocess", "check_call"),
    ("subprocess", "check_output"),
    ("subprocess", "getoutput"),
    ("subprocess", "getstatusoutput"),
    ("webbrowser", "open"),
    ("webbrowser", "open_new"),
    ("webbrowser", "open_new_tab"),
    ("shutil", "copy"), ("shutil", "copyfile"), ("shutil", "copy2"),
    ("shutil", "copytree"),
    ("shutil", "move"),
    ("shutil", "rmtree"),
})

_PYAUTOGUI_FORBIDDEN_BUILTIN_CALLS = frozenset({
    "eval",
    "exec",
    "compile",
    "__import__",
})

_HOTKEY_ALIAS = {
    "winleft": "win", "winright": "win", "super": "win", "meta": "win",
    "command": "win", "cmd": "win",
    "ctrlleft": "ctrl", "ctrlright": "ctrl", "control": "ctrl",
    "altleft": "alt", "altright": "alt", "option": "alt", "optionleft": "alt", "optionright": "alt",
    "shiftleft": "shift", "shiftright": "shift",
    "return": "enter",
    "esc": "escape",
}

# Key combos that open a shell / Run dialog and would let the model bypass GUI-only.
_PYAUTOGUI_FORBIDDEN_HOTKEY_COMBOS = frozenset({
    frozenset({"win", "r"}),            # Windows Run dialog
    frozenset({"ctrl", "alt", "t"}),    # GNOME / Ubuntu terminal
    frozenset({"win", "t"}),            # Super+T on some Linux WMs
    frozenset({"win", "x"}),            # Windows quick-access menu (PowerShell entry)
    frozenset({"ctrl", "alt", "f1"}),   # TTY switch
    frozenset({"ctrl", "alt", "f2"}),
    frozenset({"ctrl", "alt", "f3"}),
    frozenset({"ctrl", "alt", "f4"}),
    frozenset({"ctrl", "alt", "f5"}),
    frozenset({"ctrl", "alt", "f6"}),
})

_PYAUTOGUI_REJECT_MSG = (
    "<action type='pyautogui'> only accepts GUI-control operations "
    "(mouse / keyboard via pyautogui). Non-GUI capabilities are not "
    "allowed in this action type. If you need to pause, emit "
    "`<action type=\"wait\"/>`."
)

_WAIT_DEFAULT_SECONDS = 120.0
_WAIT_MIN_SECONDS = 0.0
_WAIT_MAX_SECONDS = 1800.0


def _parse_wait_seconds(action: ET.Element, *, context: str) -> str:
    raw = (action.get("seconds") or "").strip()
    if not raw:
        return str(int(_WAIT_DEFAULT_SECONDS))
    try:
        seconds = float(raw)
    except ValueError as exc:
        raise ValueError(f"{context} wait seconds must be numeric") from exc
    if not (_WAIT_MIN_SECONDS <= seconds <= _WAIT_MAX_SECONDS):
        raise ValueError(
            f"{context} wait seconds must be between "
            f"{_WAIT_MIN_SECONDS:g} and {_WAIT_MAX_SECONDS:g}"
        )
    return f"{seconds:g}"


def _normalize_hotkey_arg(node: ast.AST) -> Optional[str]:
    """Return the normalized lowercase key name for a literal string arg, else None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        k = node.value.strip().lower()
        return _HOTKEY_ALIAS.get(k, k)
    return None


def _hotkey_combo_forbidden(call: ast.Call) -> bool:
    """Check whether a `pyautogui.hotkey(...)` call statically matches a forbidden combo.

    Handles both positional (``hotkey('ctrl','alt','t')``) and iterable-literal
    (``hotkey(['ctrl','alt','t'])``) shapes. If any argument isn't a string
    literal we conservatively return False — the runtime can't tell statically.
    """
    args = list(call.args)
    if len(args) == 1 and isinstance(args[0], (ast.List, ast.Tuple)):
        args = list(args[0].elts)
    keys = set()
    for a in args:
        norm = _normalize_hotkey_arg(a)
        if norm is None:
            return False
        keys.add(norm)
    if not keys:
        return False
    return frozenset(keys) in _PYAUTOGUI_FORBIDDEN_HOTKEY_COMBOS


def _validate_pyautogui_cdata(code: str) -> None:
    """Reject pyautogui CDATA that uses non-GUI capabilities.

    Walks the AST and raises ValueError if any of these are present:
      * import / from-import of a forbidden top-level module
      * call of ``<base>.<attr>(...)`` matching the forbidden list
      * call of a bare builtin name (eval / exec / compile / __import__)
      * ``pyautogui.hotkey(...)`` whose normalized key set matches a forbidden
        terminal / Run-dialog combo (e.g. Win+R, Ctrl+Alt+T)
      * absence of any ``pyautogui.<attr>`` access at all — i.e. plain
        ``import pyautogui`` without actually driving the GUI in this turn

    All rejection paths surface the same stealth message so the model
    cannot enumerate the rules by probing.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        raise ValueError(_PYAUTOGUI_REJECT_MSG)

    saw_pyautogui_use = False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".", 1)[0]
                if top in _PYAUTOGUI_FORBIDDEN_IMPORTS:
                    raise ValueError(_PYAUTOGUI_REJECT_MSG)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            top = module.split(".", 1)[0]
            if top in _PYAUTOGUI_FORBIDDEN_IMPORTS:
                raise ValueError(_PYAUTOGUI_REJECT_MSG)

        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "pyautogui":
                saw_pyautogui_use = True

        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                if (func.value.id, func.attr) in _PYAUTOGUI_FORBIDDEN_ATTR_CALLS:
                    raise ValueError(_PYAUTOGUI_REJECT_MSG)
                if func.value.id == "pyautogui" and func.attr == "hotkey":
                    if _hotkey_combo_forbidden(node):
                        raise ValueError(_PYAUTOGUI_REJECT_MSG)
            elif isinstance(func, ast.Name):
                if func.id in _PYAUTOGUI_FORBIDDEN_BUILTIN_CALLS:
                    raise ValueError(_PYAUTOGUI_REJECT_MSG)

    if not saw_pyautogui_use:
        raise ValueError(_PYAUTOGUI_REJECT_MSG)


def parse_gui_actions(input_string: str) -> List[Tuple[str, str]]:
    """Parse one `<action type="...">` block from a GUI-mode response.

    Allowed types: `pyautogui` (CDATA must pass `_validate_pyautogui_cdata`) and
    the special signals `wait` / `done` / `fail`. Anything else raises ValueError,
    which the runner forwards back to the model via `_pending_parse_error`.

    Returns a single-element list `[(kind, payload)]` where `kind` is
    `"pyautogui"` / `"WAIT"` / `"DONE"` / `"FAIL"`.
    """
    try:
        root = ET.fromstring(input_string.strip())
    except ET.ParseError as exc:
        raise ValueError(f"Invalid response XML: {exc}") from exc

    if root.tag != "response":
        raise ValueError(f"Invalid response XML root: {root.tag!r}")

    reflections = root.findall("reflection")
    if len(reflections) != 1 or not "".join(reflections[0].itertext()).strip():
        raise ValueError("Response must contain exactly one non-empty <reflection>")

    actions = root.findall("action")
    if len(actions) != 1:
        raise ValueError("Response must contain exactly one <action>")

    action = actions[0]
    action_type = (action.get("type") or "").strip().lower()

    if action_type in ("wait", "done", "fail"):
        if "".join(action.itertext()).strip():
            raise ValueError(f"<action type={action_type!r}> must not contain text")
        if action_type == "wait":
            return [("WAIT", _parse_wait_seconds(action, context="GUI"))]
        if action.get("seconds") is not None:
            raise ValueError(f"<action type={action_type!r}> must not have a seconds attribute")
        return [(action_type.upper(), "")]

    if action_type != "pyautogui":
        raise ValueError(
            f"<action type={action_type!r}> is not allowed in gui mode "
            "(allowed: ['pyautogui', 'wait', 'done', 'fail']). Re-emit with one of those."
        )

    code = textwrap.dedent(action.text or "").strip()
    if not code:
        raise ValueError("<action type='pyautogui'> must contain non-empty CDATA")
    _validate_pyautogui_cdata(code)
    return [("pyautogui", code)]


_COMPUTER13_FORBIDDEN_HOTKEY_COMBOS = _PYAUTOGUI_FORBIDDEN_HOTKEY_COMBOS


def _computer13_hotkey_forbidden(keys: List[Any]) -> bool:
    normalized = set()
    for key in keys:
        if not isinstance(key, str):
            return False
        normalized_key = _HOTKEY_ALIAS.get(key.strip().lower(), key.strip().lower())
        normalized.add(normalized_key)
    if not normalized:
        return False
    return frozenset(normalized) in _COMPUTER13_FORBIDDEN_HOTKEY_COMBOS


def _normalize_computer13_action(payload: Dict[str, Any]) -> Tuple[str, str] | Tuple[str, Dict[str, Any]]:
    action_type = payload.get("action_type")
    if not isinstance(action_type, str) or not action_type.strip():
        raise ValueError("computer13 action must contain a non-empty action_type")
    action_type = action_type.strip().upper()

    if action_type in ("WAIT", "DONE", "FAIL"):
        seconds = ""
        params = payload.get("parameters")
        if isinstance(params, dict):
            raw_seconds = params.get("seconds")
        else:
            raw_seconds = payload.get("seconds")
        if action_type == "WAIT":
            if raw_seconds in (None, ""):
                seconds = str(int(_WAIT_DEFAULT_SECONDS))
            else:
                try:
                    seconds_value = float(raw_seconds)
                except (TypeError, ValueError) as exc:
                    raise ValueError("computer13 wait seconds must be numeric") from exc
                if not (_WAIT_MIN_SECONDS <= seconds_value <= _WAIT_MAX_SECONDS):
                    raise ValueError(
                        f"computer13 wait seconds must be between {_WAIT_MIN_SECONDS:g} and {_WAIT_MAX_SECONDS:g}"
                    )
                seconds = f"{seconds_value:g}"
            return ("WAIT", seconds)
        return (action_type, "")

    params = payload.get("parameters")
    if params is None:
        params = {k: v for k, v in payload.items() if k != "action_type"}
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise ValueError("computer13 action parameters must be an object")

    params = dict(params)
    if isinstance(params.get("button"), str):
        params["button"] = params["button"].strip().lower()
    if isinstance(params.get("key"), str):
        params["key"] = params["key"].strip().lower()
    if isinstance(params.get("keys"), list):
        normalized_keys = []
        for key in params["keys"]:
            if not isinstance(key, str):
                raise ValueError("computer13 HOTKEY keys must all be strings")
            normalized_keys.append(_HOTKEY_ALIAS.get(key.strip().lower(), key.strip().lower()))
        params["keys"] = normalized_keys

    if action_type == "HOTKEY":
        keys = params.get("keys")
        if not isinstance(keys, list) or not keys:
            raise ValueError("computer13 HOTKEY requires a non-empty keys list")
        if _computer13_hotkey_forbidden(keys):
            raise ValueError(_PYAUTOGUI_REJECT_MSG)

    normalized = {"action_type": action_type, "parameters": params}
    return ("computer13", normalized)


def parse_computer13_actions(input_string: str) -> List[Tuple[str, Any]]:
    """Parse one `<action type=\"computer13\">` block from a GUI-mode response."""
    try:
        root = ET.fromstring(input_string.strip())
    except ET.ParseError as exc:
        raise ValueError(f"Invalid response XML: {exc}") from exc

    if root.tag != "response":
        raise ValueError(f"Invalid response XML root: {root.tag!r}")

    reflections = root.findall("reflection")
    if len(reflections) != 1 or not "".join(reflections[0].itertext()).strip():
        raise ValueError("Response must contain exactly one non-empty <reflection>")

    actions = root.findall("action")
    if len(actions) != 1:
        raise ValueError("Response must contain exactly one <action>")

    action = actions[0]
    action_type = (action.get("type") or "").strip().lower()

    if action_type in ("wait", "done", "fail"):
        if "".join(action.itertext()).strip():
            raise ValueError(f"<action type={action_type!r}> must not contain text")
        if action_type == "wait":
            return [("WAIT", _parse_wait_seconds(action, context="computer13"))]
        if action.get("seconds") is not None:
            raise ValueError(f"<action type={action_type!r}> must not have a seconds attribute")
        return [(action_type.upper(), "")]

    if action_type != "computer13":
        raise ValueError(
            f"<action type={action_type!r}> is not allowed in computer13 mode "
            "(allowed: ['computer13', 'wait', 'done', 'fail']). Re-emit with one of those."
        )

    code = textwrap.dedent(action.text or "").strip()
    if not code:
        raise ValueError("<action type='computer13'> must contain a JSON object in CDATA")
    try:
        payload = json.loads(code)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid computer13 JSON payload: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("computer13 payload must be a JSON object")
    return [_normalize_computer13_action(payload)]


def parse_cli_actions(input_string, *, allow_readimg=True):
    """Parse one or more `<action>` blocks from a CLI-mode response.

    Allowed types: `bash` (CDATA), `python` (CDATA), optionally `readimg`
    (path= attribute, self-closing), and special signals `wait` / `done` /
    `fail` (each must be the sole action in the response).

    Returns ordered (kind, payload) tuples where kind is one of
    'bash' / 'python' / 'readimg' / 'WAIT' / 'DONE' / 'FAIL'. Payload is the
    code body, the readimg path, or '' for signals.
    """
    try:
        root = ET.fromstring(input_string.strip())
    except ET.ParseError as exc:
        raise ValueError(f"Invalid terminal XML response: {exc}") from exc

    if root.tag != "response":
        raise ValueError(f"Invalid terminal XML response root: {root.tag!r}")

    reflections = root.findall("reflection")
    if len(reflections) != 1 or not "".join(reflections[0].itertext()).strip():
        raise ValueError("Terminal XML response must contain exactly one non-empty <reflection>")

    action_elems = root.findall("action")
    if not action_elems:
        raise ValueError("Terminal XML response must contain at least one <action>")

    blocks = []
    saw_signal = False
    for action in action_elems:
        action_type = (action.get("type") or "").strip().lower()
        if action_type in ("bash", "python"):
            if action.get("path") is not None:
                raise ValueError(f"Terminal XML {action_type!r} action must not have a path attribute")
            script = textwrap.dedent(action.text or "").strip()
            if not script:
                raise ValueError(f"Terminal XML {action_type!r} action must contain non-empty CDATA script")
            blocks.append((action_type, script))
        elif action_type == "readimg":
            if not allow_readimg:
                raise ValueError(
                    "Terminal XML readimg action is not allowed in cli-text mode "
                    "(allowed: bash, python, wait, done, fail)."
                )
            path = (action.get("path") or "").strip()
            if not path:
                raise ValueError("Terminal XML readimg action must have a non-empty path attribute")
            if "".join(action.itertext()).strip():
                raise ValueError("Terminal XML readimg action must be empty (path goes on the attribute)")
            blocks.append(("readimg", path))
        elif action_type in ("wait", "done", "fail"):
            if action.get("path") is not None:
                raise ValueError(f"Terminal XML {action_type!r} action must not have a path attribute")
            if "".join(action.itertext()).strip():
                raise ValueError(f"Terminal XML {action_type!r} action must not contain text")
            saw_signal = True
            if action_type == "wait":
                blocks.append(("WAIT", _parse_wait_seconds(action, context="Terminal XML")))
            else:
                if action.get("seconds") is not None:
                    raise ValueError(
                        f"Terminal XML {action_type!r} action must not have a seconds attribute"
                    )
                blocks.append((action_type.upper(), ""))
        else:
            allowed = "bash, python, readimg, wait, done, fail" if allow_readimg else "bash, python, wait, done, fail"
            raise ValueError(
                f"Terminal XML action type must be one of: {allowed}; "
                f"got {action_type!r}"
            )

    if saw_signal and len(blocks) > 1:
        raise ValueError(
            "Terminal XML wait/done/fail action must be the only action in the response"
        )

    return blocks


def trim_accessibility_tree(linearized_accessibility_tree, max_tokens):
    enc = tiktoken.encoding_for_model("gpt-4")
    tokens = enc.encode(linearized_accessibility_tree)
    if len(tokens) > max_tokens:
        linearized_accessibility_tree = enc.decode(tokens[:max_tokens])
        linearized_accessibility_tree += "[...]\n"
    return linearized_accessibility_tree


class PromptAgent:
    def __init__(
            self,
            *,
            eval_mode: str,
            platform="ubuntu",
            model="gpt-4-vision-preview",
            max_tokens=1500,
            top_p=None,
            temperature=0.5,
            max_trajectory_length=3,
            client_password="password",
            max_retries=10,
            request_timeout=1800,
            reasoning_effort="high",
    ):
        if eval_mode not in ("gui", "computer13", "gui-a11y", "gui-screenshot-a11y", "cli", "cli-text"):
            raise ValueError(
                "eval_mode must be 'gui', 'computer13', 'gui-a11y', 'gui-screenshot-a11y', "
                f"'cli', or 'cli-text', got {eval_mode!r}"
            )
        self.eval_mode = eval_mode
        self.platform = platform
        self.model = model
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.temperature = temperature
        self.max_trajectory_length = max_trajectory_length
        self.client_password = client_password
        self.max_retries = max_retries
        # OpenAI reasoning_effort ('low'|'medium'|'high'); default 'high'.
        # Only injected into the payload for gpt* models — sibling openai-compat
        # gateways (kimi/glm/qwen3.6/doubao/openrouter) typically reject or
        # silently ignore the field, so we gate on the gpt prefix to avoid
        # surprising 400s.
        self.reasoning_effort = reasoning_effort
        # Per-call HTTP read timeout (seconds) for the LLM request; connect
        # timeout is fixed at 10s. Without an explicit timeout, requests waits
        # forever when the upstream gateway silently drops the request — the
        # heartbeat thread keeps the sandbox alive while the worker thread
        # deadlocks on socket recv. Configured per run via --llm_request_timeout.
        self.request_timeout = (10, request_timeout)

        self.thoughts = []
        self.actions = []
        self.observations = []
        # Snapshot of the system prompt and first user-turn text used on the
        # very first predict() after reset(), so callers can dump them to disk
        # for inspection. Populated lazily inside predict().
        self._first_system_text = None
        self._first_user_text = None
        # When parse_actions fails on a turn, we don't crash the run — instead
        # we stash the parser's error message here, and on the next predict()
        # we prepend a feedback line to the user message so the model knows its
        # previous output was rejected and can re-emit the correct format.
        # Cleared as soon as it's been consumed by the next prompt.
        self._pending_parse_error: Optional[str] = None
        # Same channel, but for runtime feedback the runner wants the model
        # to see on the next turn — currently used for sandbox-side hard
        # timeouts (120s per-action budget exceeded). The runner sets this
        # after catching SandboxExecuteHardTimeoutError; we prepend it to the
        # next user message so the model can self-correct (e.g. by detaching
        # long-running work via nohup/Popen). Cleared once consumed. If both
        # _pending_runtime_error and _pending_parse_error are set on the same
        # turn (timeout happened earlier, parse failed in between), runtime
        # feedback goes in first because it's the older fact.
        self._pending_runtime_error: Optional[str] = None
        # Per-predict() LLM call telemetry. Reset at the start of every
        # call_llm(); each attempt appends one dict (status, provider, model,
        # raw_finish_reason, http_status, usage, latency_ms, error). The runner
        # in lib_run_single.py reads this after agent.predict() and flushes it
        # to <example_result_dir>/llm_calls.jsonl. Using a side-channel keeps
        # predict()'s (response, actions) signature unchanged.
        self._llm_attempts: List[Dict] = []

        if eval_mode == "gui":
            self.system_message = build_gui_prompt()
        elif eval_mode == "computer13":
            self.system_message = build_computer13_prompt()
        elif eval_mode == "gui-a11y":
            self.system_message = build_gui_a11y_prompt()
        elif eval_mode == "gui-screenshot-a11y":
            self.system_message = build_gui_screenshot_a11y_prompt()
        elif eval_mode == "cli":
            self.system_message = build_cli_prompt()
        else:
            self.system_message = build_cli_text_prompt()
        self.system_message = self.system_message.format(
            CLIENT_PASSWORD=self.client_password
        )

    def _format_a11y_observation(self, obs: Dict) -> str:
        accessibility_tree = obs.get("accessibility_tree") if isinstance(obs, dict) else None
        if not accessibility_tree:
            return "Accessibility tree observation: unavailable."
        try:
            linearized = linearize_accessibility_tree(accessibility_tree, self.platform)
        except Exception as exc:
            return f"Accessibility tree observation could not be parsed: {type(exc).__name__}: {exc}"
        return trim_accessibility_tree(linearized, 12000)

    def _format_gui_observation(self, obs: Dict) -> Dict[str, Optional[str]]:
        formatted: Dict[str, Optional[str]] = {
            "screenshot": encode_image(obs["screenshot"]),
            "accessibility_tree": None,
        }
        if self.eval_mode == "gui-a11y":
            formatted["screenshot"] = None
            formatted["accessibility_tree"] = self._format_a11y_observation(obs)
        elif self.eval_mode == "gui-screenshot-a11y":
            formatted["accessibility_tree"] = self._format_a11y_observation(obs)
        return formatted

    def predict(self, instruction: str, obs: Dict) -> List:
        """
        Predict the next action(s) based on the current observation.
        """
        system_message = self.system_message + "\nYou are asked to complete the following task: {}".format(instruction)
        if self._first_system_text is None:
            self._first_system_text = system_message

        # Prepare the payload for the API call
        messages = []
        masks = None

        messages.append({
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": system_message
                },
            ]
        })

        # Append trajectory
        assert len(self.observations) == len(self.actions) and len(self.actions) == len(self.thoughts) \
            , "The number of observations and actions should be the same."

        if len(self.observations) > self.max_trajectory_length:
            if self.max_trajectory_length == 0:
                _observations = []
                _actions = []
                _thoughts = []
            else:
                _observations = self.observations[-self.max_trajectory_length:]
                _actions = self.actions[-self.max_trajectory_length:]
                _thoughts = self.thoughts[-self.max_trajectory_length:]
        else:
            _observations = self.observations
            _actions = self.actions
            _thoughts = self.thoughts

        # Step number of the first replayed history obs (1-indexed). Used to
        # tag each image content part with `_step` so logs can reference the
        # corresponding `step_N_*.png` saved by lib_run_single.py.
        history_start_step = len(self.observations) - len(_observations) + 1

        for _hist_idx, (previous_obs, previous_action, previous_thought) in enumerate(zip(_observations, _actions, _thoughts)):
            _hist_step = history_start_step + _hist_idx

            # {{{1
            if self.eval_mode in ("gui", "computer13"):
                _screenshot = previous_obs["screenshot"]

                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Given the screenshot as below. What's the next computer13 action that you will do "
                                "to help with the task?"
                                if self.eval_mode == "computer13"
                                else "Given the screenshot as below. What's the next step that you will do to help with the task?"
                            )
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{_screenshot}",
                                "detail": "high"
                            },
                            "_step": _hist_step,
                        }
                    ]
                })
            elif self.eval_mode == "gui-a11y":
                _accessibility_tree = previous_obs.get("accessibility_tree", "")

                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Given the accessibility tree below. What's the next step that you will do "
                                "to help with the task?\n\n"
                                f"{_accessibility_tree}"
                            )
                        }
                    ]
                })
            elif self.eval_mode == "gui-screenshot-a11y":
                _screenshot = previous_obs["screenshot"]
                _accessibility_tree = previous_obs.get("accessibility_tree", "")

                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Given the screenshot and accessibility tree below. What's the next step that you "
                                "will do to help with the task?\n\n"
                                f"{_accessibility_tree}"
                            )
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{_screenshot}",
                                "detail": "high"
                            },
                            "_step": _hist_step,
                        }
                    ]
                })
            elif self.eval_mode in ("cli", "cli-text"):
                image_paths = previous_obs.get("images_paths", []) if self.eval_mode == "cli" else []
                text = _format_terminal_text(
                    previous_obs.get("bash_runs", []),
                    image_paths,
                )
                messages.append({
                    "role": "user",
                    "content": [{"type": "text", "text": text}],
                })
            else:
                raise ValueError("Invalid eval_mode: " + self.eval_mode)  # 1}}}

            messages.append({
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": previous_thought.strip() if len(previous_thought) > 0 else "No valid action"
                    },
                ]
            })

        # {{{1
        if self.eval_mode in ("gui", "computer13"):
            base64_image = encode_image(obs["screenshot"])
            self.observations.append({
                "screenshot": base64_image,
            })

            _current_step = len(self.observations)
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Given the screenshot as below. What's the next computer13 action that you will do "
                            "to help with the task?"
                            if self.eval_mode == "computer13"
                            else "Given the screenshot as below. What's the next step that you will do to help with the task?"
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}",
                            "detail": "high"
                        },
                        "_step": _current_step,
                    }
                ]
            })
        elif self.eval_mode == "gui-a11y":
            a11y_obs = self._format_gui_observation(obs)
            self.observations.append(a11y_obs)

            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Given the accessibility tree below. What's the next step that you will do "
                            "to help with the task?\n\n"
                            f"{a11y_obs['accessibility_tree']}"
                        )
                    }
                ]
            })
        elif self.eval_mode == "gui-screenshot-a11y":
            gui_obs = self._format_gui_observation(obs)
            self.observations.append(gui_obs)

            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Given the screenshot and accessibility tree below. What's the next step that you "
                            "will do to help with the task?\n\n"
                            f"{gui_obs['accessibility_tree']}"
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{gui_obs['screenshot']}",
                            "detail": "high"
                        },
                        "_step": len(self.observations),
                    }
                ]
            })
        elif self.eval_mode in ("cli", "cli-text"):
            bash_runs = obs.get("bash_runs") or []
            images = (obs.get("images") or []) if self.eval_mode == "cli" else []
            self.observations.append({
                "bash_runs": bash_runs,
                # store paths only; image bytes are one-shot (model already saw them this turn)
                "images_paths": [p for (p, _data) in images],
            })

            _current_step = len(self.observations)
            content = [{
                "type": "text",
                "text": _format_terminal_text(bash_runs, [p for (p, _) in images]),
            }]
            if self.eval_mode == "cli":
                for path, data in images:
                    if not isinstance(data, (bytes, bytearray)) or not data:
                        # Failure already announced in the text part; do NOT ship an
                        # empty/invalid image_url — the API will 400 the whole call.
                        continue
                    mime = _detect_image_mime(bytes(data))
                    if not mime:
                        # Bytes aren't a recognisable image; skip rather than mislabel.
                        continue
                    b64 = base64.b64encode(data).decode("utf-8")
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"},
                        "_step": _current_step,
                    })
            messages.append({"role": "user", "content": content})
        else:
            raise ValueError("Invalid eval_mode: " + self.eval_mode)  # 1}}}

        # If the previous turn produced runtime feedback (e.g. a sandbox-side
        # hard timeout caught by the runner), or the response failed to parse,
        # prepend explicit notices to this turn's user message. Both are
        # consumed once and cleared. When both are present, runtime feedback
        # goes first (it's the older fact: the timeout happened during action
        # execution, the parse failure happened on the subsequent turn's
        # response). Each block joins with \n\n to keep them visually distinct
        # and avoid one running into the other.
        def _prepend_to_last_user_text(messages_list, text_block: str) -> None:
            if not messages_list:
                return
            last = messages_list[-1]
            if last.get("role") != "user":
                return
            for c in last.get("content", []):
                if c.get("type") == "text":
                    c["text"] = text_block + c.get("text", "")
                    return

        if self._pending_runtime_error:
            feedback = f"[runtime_feedback] {self._pending_runtime_error}\n\n"
            _prepend_to_last_user_text(messages, feedback)
            self._pending_runtime_error = None

        if self._pending_parse_error:
            feedback = (
                "[parse_error] Your previous response could not be parsed "
                f"and was discarded. Reason: {self._pending_parse_error}\n"
                "Please re-output your response strictly following the "
                "format specified in the system prompt.\n\n"
            )
            _prepend_to_last_user_text(messages, feedback)
            self._pending_parse_error = None

        if self._first_user_text is None and messages:
            last_msg = messages[-1]
            if last_msg.get("role") == "user":
                text_parts = [
                    c.get("text", "")
                    for c in last_msg.get("content", [])
                    if c.get("type") == "text"
                ]
                self._first_user_text = "\n".join(t for t in text_parts if t)

        llm_payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        # max_tokens 鐣?None 鏃朵笉鍐欏叆 payload锛汷penAI/Gemini 鍒嗘敮浼?鎸夊巶鍟嗛粯璁?銆?
        # Claude 鍒嗘敮鍥?Anthropic API 寮哄埗瑕佹眰璇ュ瓧娈碉紝鑷繁鍏滃簳锛堣涓嬫柟锛夈€?
        if self.max_tokens is not None:
            llm_payload["max_tokens"] = self.max_tokens
        if self.top_p is not None:
            llm_payload["top_p"] = self.top_p
        # reasoning_effort is OpenAI-only. Other openai-compat gateways
        # (kimi/glm/qwen3.6/doubao/openrouter) sharing the same HTTP branch
        # don't accept it, so gate strictly on the gpt prefix here.
        if self.reasoning_effort is not None and self.model.startswith("gpt"):
            llm_payload["reasoning_effort"] = self.reasoning_effort
        try:
            response = self.call_llm(llm_payload)
        except Exception as e:
            logger.error("Failed to call" + self.model + ", Error: " + str(e))
            response = ""

        logger.info("RESPONSE: %s", response)

        # Catch parse failures here instead of letting them crash the whole
        # task. The model's malformed output is its own mistake — feed the
        # error back next turn (via self._pending_parse_error) so it gets a
        # chance to self-correct, rather than burning the entire step budget.
        # Only parser exceptions are caught; LLM/network errors above are
        # already handled separately and produce response="".
        try:
            actions = self.parse_actions(response, masks)
        except (ValueError, ET.ParseError) as exc:
            err_text = str(exc)
            logger.warning("Failed to parse model response: %s", err_text)
            actions = []
            self._pending_parse_error = err_text
            # parse_actions only appends to self.actions on the success path,
            # so on failure we must append manually to keep the
            # observations / actions / thoughts length invariant (the assert
            # at the top of predict() depends on it).
            self.actions.append(actions)
        self.thoughts.append(response)

        return response, actions

    # Exceptions treated as transient by the LLM call retry. Empty/whitespace
    # responses (often a swallowed 429 or content-filter at a proxy) are
    # converted to ``EmptyResponseError`` so they retry through the same path.
    _RETRYABLE_LLM_EXCEPTIONS = (
        # General
        SSLError,
        # OpenAI / OpenAI-compatible proxies
        openai.RateLimitError,
        openai.BadRequestError,
        openai.InternalServerError,
        # google.api_core (legacy google-generativeai SDK)
        InvalidArgument,
        ResourceExhausted,
        InternalServerError,
        BadRequest,
        # google-genai (new SDK, used by gemini-3-* path)
        _GENAI_API_ERROR,
        # Empty / soft-refusal
        EmptyResponseError,
        # HTTP timeout / connection-level failures from the requests-based
        # providers (openai-compat / anthropic / azure). Capped independently
        # by _TIMEOUT_RETRY_BUDGET below — each attempt can burn the full
        # --llm_request_timeout (default 30min), so we don't want max_retries
        # (typically sized for cheap soft failures) governing this path too.
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
    )

    # Hard cap on retries for HTTP timeout / connection failures. Sized so the
    # worst-case wall-clock spent on a single LLM call stays bounded:
    # (1 + budget) 脳 --llm_request_timeout, i.e. ~2h at default 30min/4 attempts.
    _TIMEOUT_RETRY_BUDGET = 3

    def call_llm(self, payload):
        # Reset per-call attempt log; lib_run_single.py reads this back after
        # predict() and flushes to llm_calls.jsonl. Cleared here (not in
        # predict) so callers that drive call_llm directly still get fresh
        # data per call.
        self._llm_attempts = []
        timeout_attempts = 0
        for attempt in make_llm_retry(
            exceptions=self._RETRYABLE_LLM_EXCEPTIONS,
            max_attempts=self.max_retries,
            max_wait=60.0,
        ):
            with attempt:
                t0 = time.monotonic()
                try:
                    content, meta = self._call_llm_once(payload)
                except Exception as exc:
                    self._llm_attempts.append({
                        "status": "exception",
                        "provider": None,
                        "model": payload.get("model"),
                        "raw_finish_reason": None,
                        "http_status": None,
                        "usage": None,
                        "latency_ms": int((time.monotonic() - t0) * 1000),
                        "error": f"{type(exc).__name__}: {str(exc)[:500]}",
                    })
                    if isinstance(exc, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
                        timeout_attempts += 1
                        if timeout_attempts > self._TIMEOUT_RETRY_BUDGET:
                            # Convert to a non-retryable type so tenacity stops
                            # — max_retries is for cheap soft failures, not for
                            # 30-min-per-attempt network hangs.
                            raise RuntimeError(
                                f"LLM HTTP {type(exc).__name__} budget exhausted "
                                f"({self._TIMEOUT_RETRY_BUDGET} retries): {exc}"
                            ) from exc
                    raise
                meta["latency_ms"] = int((time.monotonic() - t0) * 1000)
                self._llm_attempts.append(meta)
                if not isinstance(content, str) or not content.strip():
                    # Mark this attempt as empty before tenacity retries.
                    meta["status"] = "empty"
                    raise EmptyResponseError(
                        f"Empty response from model {payload.get('model')}"
                    )
                return content

    def _make_meta(self, *, provider: str, status: str = "ok",
                    raw_finish_reason: Optional[str] = None,
                    http_status: Optional[int] = None,
                    usage: Optional[Dict] = None,
                    error: Optional[str] = None) -> Dict:
        """Build the per-attempt meta dict written to llm_calls.jsonl.

        Centralised so cold provider branches that don't extract finish_reason
        or token usage still produce schema-consistent rows.
        """
        return {
            "status": status,
            "provider": provider,
            "model": self.model,
            "raw_finish_reason": raw_finish_reason,
            "http_status": http_status,
            "usage": usage,
            "error": error,
        }

    def _call_llm_once(self, payload):
        # Account-level RPM gate: blocks when the shared 60s window is full.
        # Sits inside tenacity's `with attempt:` block, so each retry counts.
        acquire_rpm_slot()

        # Sanitised request log: replaces base64 image payloads with
        # `<image step_N>` tags so runtime.log stays readable instead of
        # ballooning to hundreds of MB. The corresponding `step_N_*.png` is
        # saved on disk by lib_run_single.py.
        logger.debug("LLM REQUEST: %s", _sanitize_for_log(payload.get("messages", [])))
        # Strip our log-only `_step` metadata before any vendor API sees it.
        _strip_log_metadata(payload.get("messages", []))

        if payload['model'].startswith("azure-gpt-4o"):


            #.env config example :
            # AZURE_OPENAI_API_BASE=YOUR_API_BASE
            # AZURE_OPENAI_DEPLOYMENT=YOUR_DEPLOYMENT
            # AZURE_OPENAI_API_VERSION=YOUR_API_VERSION
            # AZURE_OPENAI_MODEL=gpt-4o-mini
            # AZURE_OPENAI_API_KEY={{YOUR_API_KEY}}
            # AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_API_BASE}/openai/deployments/${AZURE_OPENAI_DEPLOYMENT}/chat/completions?api-version=${AZURE_OPENAI_API_VERSION}


            # Load environment variables
            load_dotenv()
            api_key = os.getenv('AZURE_OPENAI_API_KEY')
            openai_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
            #logger.info("Openai endpoint: %s", openai_endpoint)

            headers = {
                "Content-Type": "application/json",
                "api-key": api_key
            }
            logger.info("Generating content with GPT model: %s", payload['model'])
            response = requests.post(
                openai_endpoint,
                headers=headers,
                json=payload,
                timeout=self.request_timeout,
            )

            if response.status_code != 200:
                if response.json()['error']['code'] == "context_length_exceeded":
                    logger.error("Context length exceeded. Retrying with a smaller context.")
                    payload["messages"] = [payload["messages"][0]] + payload["messages"][-1:]
                    retry_response = requests.post(
                        openai_endpoint,
                        headers=headers,
                        json=payload,
                        timeout=self.request_timeout,
                    )
                    if retry_response.status_code != 200:
                         logger.error(
                            "Failed to call LLM even after attempt on shortening the history: " + retry_response.text)
                         return "", self._make_meta(
                             provider="azure_openai", status="http_error",
                             http_status=retry_response.status_code,
                             error=retry_response.text[:500],
                         )

                logger.error("Failed to call LLM: " + response.text)
                time.sleep(5)
                return "", self._make_meta(
                    provider="azure_openai", status="http_error",
                    http_status=response.status_code, error=response.text[:500],
                )
            else:
                body = response.json()
                content = body['choices'][0]['message']['content']
                finish = body['choices'][0].get('finish_reason')
                status = {"stop": "ok", "length": "truncated",
                           "content_filter": "content_filter"}.get(finish, "ok")
                usage = body.get("usage") or {}
                meta = self._make_meta(
                    provider="azure_openai", status=status,
                    raw_finish_reason=finish, http_status=response.status_code,
                    usage={
                        "input_tokens": usage.get("prompt_tokens"),
                        "output_tokens": usage.get("completion_tokens"),
                        "thinking_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                        "total_tokens": usage.get("total_tokens"),
                    },
                )
                return content, meta
        elif self.model.startswith(("gpt", "kimi", "glm", "qwen3.6", "doubao", "openrouter/")):
            # OpenAI-compatible chat/completions: msh 缃戝叧鎶?kimi/glm/qwen3.6/doubao
            # 浠ュ強 openrouter/* 閮借蛋杩欐潯鍗忚锛屾墍浠ヨ繖浜涘墠缂€閮藉叡鐢?gpt 鍒嗘敮鐨?HTTP 璺緞銆?
            base_url = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com')
            # Smart handling: avoid duplicate /v1 if base_url already ends with /v1
            api_url = f"{base_url}/chat/completions" if base_url.endswith('/v1') else f"{base_url}/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"
            }
            logger.info("Generating content with OpenAI-compatible model: %s", self.model)
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=self.request_timeout,
            )

            if response.status_code != 200:
                body_text = response.text
                logger.error(
                    "Failed to call LLM (status=%s, model=%s): %s",
                    response.status_code, self.model, body_text,
                )
                err_code = None
                try:
                    err_obj = response.json().get("error")
                    if isinstance(err_obj, dict):
                        err_code = err_obj.get("code")
                except Exception:
                    pass
                if err_code == "context_length_exceeded":
                    logger.error("Context length exceeded. Retrying with a smaller context.")
                    payload["messages"] = [payload["messages"][0]] + payload["messages"][-1:]
                    retry_response = requests.post(
                        api_url,
                        headers=headers,
                        json=payload,
                        timeout=self.request_timeout,
                    )
                    if retry_response.status_code != 200:
                        logger.error(
                            "Failed to call LLM even after attempt on shortening the history: " + retry_response.text)
                        return "", self._make_meta(
                            provider="openai_compat", status="http_error",
                            http_status=retry_response.status_code,
                            error=retry_response.text[:500],
                        )
                    rbody = retry_response.json()
                    rcontent = rbody['choices'][0]['message']['content']
                    rfinish = rbody['choices'][0].get('finish_reason')
                    rstatus = {"stop": "ok", "length": "truncated",
                                "content_filter": "content_filter"}.get(rfinish, "ok")
                    rusage = rbody.get("usage") or {}
                    return rcontent, self._make_meta(
                        provider="openai_compat", status=rstatus,
                        raw_finish_reason=rfinish,
                        http_status=retry_response.status_code,
                        usage={
                            "input_tokens": rusage.get("prompt_tokens"),
                            "output_tokens": rusage.get("completion_tokens"),
                            "thinking_tokens": (rusage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                            "total_tokens": rusage.get("total_tokens"),
                        },
                        error="context_length_exceeded; retried with shortened history",
                    )
                time.sleep(5)
                return "", self._make_meta(
                    provider="openai_compat", status="http_error",
                    http_status=response.status_code, error=body_text[:500],
                )
            else:
                body = response.json()
                content = body['choices'][0]['message']['content']
                finish = body['choices'][0].get('finish_reason')
                status = {"stop": "ok", "length": "truncated",
                           "content_filter": "content_filter"}.get(finish, "ok")
                usage = body.get("usage") or {}
                meta = self._make_meta(
                    provider="openai_compat", status=status,
                    raw_finish_reason=finish, http_status=response.status_code,
                    usage={
                        "input_tokens": usage.get("prompt_tokens"),
                        "output_tokens": usage.get("completion_tokens"),
                        "thinking_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                        "total_tokens": usage.get("total_tokens"),
                    },
                )
                return content, meta

        elif self.model.startswith("claude"):
            messages = payload["messages"]
            # Anthropic Messages API 鎶?max_tokens 鍒椾负蹇呭～锛屾墍浠ユ湭鎸囧畾鏃跺厹搴曞埌
            # Claude 4 绯诲垪鐨勫崟娆¤緭鍑轰笂闄?64000锛涘叾瀹冨垎鏀墠鍏佽"鐣欑┖ = 鍘傚晢榛樿"銆?
            max_tokens = payload.get("max_tokens", 64000) or 64000
            top_p = payload.get("top_p")
            temperature = payload["temperature"]

            claude_messages = []

            for i, message in enumerate(messages):
                claude_message = {
                    "role": message["role"],
                    "content": []
                }
                assert len(message["content"]) >= 1, "Each message must have at least one content part"
                for part in message["content"]:

                    if part['type'] == "image_url":
                        image_source = {}
                        image_source["type"] = "base64"
                        image_source["media_type"] = "image/png"
                        image_source["data"] = part['image_url']['url'].replace("data:image/png;base64,", "")
                        claude_message['content'].append({"type": "image", "source": image_source})

                    if part['type'] == "text":
                        claude_message['content'].append({"type": "text", "text": part['text']})

                claude_messages.append(claude_message)

            # the claude not support system message in our endpoint, so we concatenate it at the first user message
            if claude_messages[0]['role'] == "system":
                claude_system_message_item = claude_messages[0]['content'][0]
                claude_messages[1]['content'].insert(0, claude_system_message_item)
                claude_messages.pop(0)

            headers = {
                "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }

            payload = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": claude_messages,
                "temperature": temperature,
            }
            if top_p is not None:
                payload["top_p"] = top_p

            anthropic_base = os.environ.get(
                "ANTHROPIC_BASE_URL", "https://api.anthropic.com"
            ).rstrip("/")
            response = requests.post(
                f"{anthropic_base}/v1/messages",
                headers=headers,
                json=payload,
                timeout=self.request_timeout,
            )

            if response.status_code != 200:

                logger.error("Failed to call LLM: " + response.text)
                time.sleep(5)
                return "", self._make_meta(
                    provider="anthropic", status="http_error",
                    http_status=response.status_code, error=response.text[:500],
                )
            else:
                body = response.json()
                # Pick the first text block rather than assuming content[0] is
                # text — that assumption breaks the moment we ever turn on
                # extended thinking (which prepends a "thinking" block).
                text_blocks = [b for b in body.get("content", []) if b.get("type") == "text"]
                content = text_blocks[0]["text"] if text_blocks else ""
                stop = body.get("stop_reason")
                status = {"end_turn": "ok", "max_tokens": "truncated",
                           "stop_sequence": "ok"}.get(stop, "ok")
                usage = body.get("usage") or {}
                in_tok = usage.get("input_tokens")
                out_tok = usage.get("output_tokens")
                total = (in_tok or 0) + (out_tok or 0) if usage else None
                meta = self._make_meta(
                    provider="anthropic", status=status,
                    raw_finish_reason=stop, http_status=response.status_code,
                    usage={
                        "input_tokens": in_tok,
                        "output_tokens": out_tok,
                        "thinking_tokens": None,
                        "total_tokens": total,
                    },
                )
                return content, meta

        elif self.model.startswith("mistral"):
            messages = payload["messages"]
            max_tokens = payload.get("max_tokens")
            top_p = payload.get("top_p")
            temperature = payload["temperature"]

            mistral_messages = []

            for i, message in enumerate(messages):
                mistral_message = {
                    "role": message["role"],
                    "content": ""
                }

                for part in message["content"]:
                    mistral_message['content'] = part['text'] if part['type'] == "text" else ""

                mistral_messages.append(mistral_message)

            from openai import OpenAI

            client = OpenAI(api_key=os.environ["TOGETHER_API_KEY"],
                            base_url='https://api.together.xyz',
                            )

            flag = 0
            while True:
                try:
                    if flag > 20:
                        break
                    logger.info("Generating content with model: %s", self.model)
                    response = client.chat.completions.create(
                        messages=mistral_messages,
                        model=self.model,
                        max_tokens=max_tokens,
                        top_p=top_p,
                        temperature=temperature
                    )
                    break
                except:
                    if flag == 0:
                        mistral_messages = [mistral_messages[0]] + mistral_messages[-1:]
                    else:
                        mistral_messages[-1]["content"] = ' '.join(mistral_messages[-1]["content"].split()[:-500])
                    flag = flag + 1

            try:
                return response.choices[0].message.content, self._make_meta(provider="mistral")
            except Exception as e:
                print("Failed to call LLM: " + str(e))
                return "", self._make_meta(provider="mistral", status="exception", error=str(e)[:500])

        elif self.model.startswith("THUDM"):
            # THUDM/cogagent-chat-hf
            messages = payload["messages"]
            max_tokens = payload.get("max_tokens")
            top_p = payload.get("top_p")
            temperature = payload["temperature"]

            cog_messages = []

            for i, message in enumerate(messages):
                cog_message = {
                    "role": message["role"],
                    "content": []
                }

                for part in message["content"]:
                    if part['type'] == "image_url":
                        cog_message['content'].append(
                            {"type": "image_url", "image_url": {"url": part['image_url']['url']}})

                    if part['type'] == "text":
                        cog_message['content'].append({"type": "text", "text": part['text']})

                cog_messages.append(cog_message)

            # the cogagent not support system message in our endpoint, so we concatenate it at the first user message
            if cog_messages[0]['role'] == "system":
                cog_system_message_item = cog_messages[0]['content'][0]
                cog_messages[1]['content'].insert(0, cog_system_message_item)
                cog_messages.pop(0)

            payload = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": cog_messages,
                "temperature": temperature,
                "top_p": top_p
            }

            base_url = "http://127.0.0.1:8000"

            response = requests.post(f"{base_url}/v1/chat/completions", json=payload, stream=False)
            if response.status_code == 200:
                decoded_line = response.json()
                content = decoded_line.get("choices", [{}])[0].get("message", "").get("content", "")
                return content, self._make_meta(provider="thudm", http_status=response.status_code)
            else:
                print("Failed to call LLM: ", response.status_code)
                return "", self._make_meta(
                    provider="thudm", status="http_error",
                    http_status=response.status_code, error=response.text[:500],
                )

        elif self.model in ["gemini-pro", "gemini-pro-vision"]:
            messages = payload["messages"]
            max_tokens = payload.get("max_tokens")
            top_p = payload.get("top_p")
            temperature = payload["temperature"]

            gemini_messages = []
            for i, message in enumerate(messages):
                role_mapping = {
                    "assistant": "model",
                    "user": "user",
                    "system": "system"
                }
                gemini_message = {
                    "role": role_mapping[message["role"]],
                    "parts": []
                }
                assert len(message["content"]) >= 1, "Each message must have at least one content part"

                # The gemini only support the last image as single image input
                if i == len(messages) - 1:
                    for part in message["content"]:
                        gemini_message['parts'].append(part['text']) if part['type'] == "text" \
                            else gemini_message['parts'].append(encoded_img_to_pil_img(part['image_url']['url']))
                else:
                    for part in message["content"]:
                        gemini_message['parts'].append(part['text']) if part['type'] == "text" else None

                gemini_messages.append(gemini_message)

            # the gemini not support system message in our endpoint, so we concatenate it at the first user message
            if gemini_messages[0]['role'] == "system":
                gemini_messages[1]['parts'][0] = gemini_messages[0]['parts'][0] + "\n" + gemini_messages[1]['parts'][0]
                gemini_messages.pop(0)

            # since the gemini-pro-vision donnot support multi-turn message
            if self.model == "gemini-pro-vision":
                message_history_str = ""
                for message in gemini_messages:
                    message_history_str += "<|" + message['role'] + "|>\n" + message['parts'][0] + "\n"
                gemini_messages = [{"role": "user", "parts": [message_history_str, gemini_messages[-1]['parts'][1]]}]
                # gemini_messages[-1]['parts'][1].save("output.png", "PNG")

            # print(gemini_messages)
            api_key = os.environ.get("GENAI_API_KEY")
            assert api_key is not None, "Please set the GENAI_API_KEY environment variable"
            genai.configure(api_key=api_key)
            logger.info("Generating content with Gemini model: %s", self.model)
            request_options = {"timeout": 120}
            gemini_model = genai.GenerativeModel(self.model)

            response = gemini_model.generate_content(
                gemini_messages,
                generation_config={
                    "candidate_count": 1,
                    # "max_output_tokens": max_tokens,
                    "top_p": top_p,
                    "temperature": temperature
                },
                safety_settings={
                    "harassment": "block_none",
                    "hate": "block_none",
                    "sex": "block_none",
                    "danger": "block_none"
                },
                request_options=request_options
            )
            try:
                content = response.text or ""
            except Exception:
                content = ""
            return content, self._make_meta(provider="genai_legacy")

        elif self.model.startswith("gemini"):
            from io import BytesIO
            from google import genai as google_genai
            from google.genai import types as genai_types

            messages = payload["messages"]
            # 鏈寚瀹氭椂璁?Gemini 鐢ㄦā鍨嬭嚜瀹堕粯璁わ紙Gemini 3 鍗曟杈撳嚭 ~65K锛夛紝涓嶄笅鍙?max_output_tokens銆?
            max_tokens = payload.get("max_tokens")
            top_p = payload.get("top_p")
            temperature = payload["temperature"]

            role_mapping = {"assistant": "model", "user": "user", "system": "system"}
            system_instruction = None
            contents = []
            messages_to_save = []
            for message in messages:
                role = role_mapping[message["role"]]
                assert len(message["content"]) >= 1, "Each message must have at least one content part"
                parts = []
                for part in message["content"]:
                    if part["type"] == "image_url":
                        pil_img = encoded_img_to_pil_img(part["image_url"]["url"])
                        buf = BytesIO()
                        pil_img.save(buf, format="PNG")
                        parts.insert(0, genai_types.Part.from_bytes(
                            data=buf.getvalue(), mime_type="image/png"
                        ))
                    elif part["type"] == "text":
                        parts.append(genai_types.Part.from_text(text=part["text"]))
                    else:
                        raise ValueError("Invalid content type: " + part["type"])

                if role == "system":
                    text_only = [p.text for p in parts if getattr(p, "text", None)]
                    if text_only:
                        system_instruction = "\n".join(text_only)
                    continue

                contents.append(genai_types.Content(role=role, parts=parts))
                messages_to_save.append({
                    "role": role,
                    "content": [p.text if getattr(p, "text", None) else "image" for p in parts],
                })

            api_key = os.environ.get("GENAI_API_KEY")
            assert api_key is not None, "Please set the GENAI_API_KEY environment variable"
            base_url = os.environ.get("GENAI_BASE_URL")
            api_version = os.environ.get("GENAI_API_VERSION", "v1beta")
            http_options_kwargs = {"timeout": 120000}
            if base_url:
                http_options_kwargs["base_url"] = base_url
                http_options_kwargs["api_version"] = api_version
            client = google_genai.Client(
                api_key=api_key,
                http_options=genai_types.HttpOptions(**http_options_kwargs),
            )

            logger.info("Generating content with Gemini model: %s", self.model)
            with open("response.json", "w") as f:
                json.dump(messages_to_save, f, indent=4)

            config_kwargs = dict(
                system_instruction=system_instruction,
                candidate_count=1,
                temperature=temperature,
            )
            if max_tokens is not None:
                config_kwargs["max_output_tokens"] = max_tokens
            if top_p is not None:
                config_kwargs["top_p"] = top_p
            config = genai_types.GenerateContentConfig(
                **config_kwargs,
                safety_settings=[
                    genai_types.SafetySetting(
                        category=genai_types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                        threshold=genai_types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    genai_types.SafetySetting(
                        category=genai_types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        threshold=genai_types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    genai_types.SafetySetting(
                        category=genai_types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        threshold=genai_types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    genai_types.SafetySetting(
                        category=genai_types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        threshold=genai_types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                ],
            )

            response = client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )

            cand = response.candidates[0] if getattr(response, "candidates", None) else None
            finish_enum = getattr(cand, "finish_reason", None) if cand else None
            finish = getattr(finish_enum, "name", None) if finish_enum else None
            status_map = {"STOP": "ok", "MAX_TOKENS": "truncated",
                          "SAFETY": "content_filter", "RECITATION": "content_filter"}
            status = status_map.get(finish, "ok")
            # response.text raises ValueError when no text part is present
            # (Gemini 2.5+ commonly hits this when thinking eats the whole
            # max_output_tokens budget).
            try:
                content = response.text or ""
            except Exception:
                content = ""
            if not content.strip():
                status = "empty"
            um = getattr(response, "usage_metadata", None)
            usage = {
                "input_tokens": getattr(um, "prompt_token_count", None) if um else None,
                "output_tokens": getattr(um, "candidates_token_count", None) if um else None,
                "thinking_tokens": getattr(um, "thoughts_token_count", None) if um else None,
                "total_tokens": getattr(um, "total_token_count", None) if um else None,
            }
            meta = self._make_meta(
                provider="genai", status=status, raw_finish_reason=finish,
                http_status=None, usage=usage,
            )
            return content, meta

        elif self.model == "llama3-70b":
            messages = payload["messages"]
            max_tokens = payload.get("max_tokens")
            top_p = payload.get("top_p")
            temperature = payload["temperature"]

            groq_messages = []

            for i, message in enumerate(messages):
                groq_message = {
                    "role": message["role"],
                    "content": ""
                }

                for part in message["content"]:
                    groq_message['content'] = part['text'] if part['type'] == "text" else ""

                groq_messages.append(groq_message)

            # The implementation based on Groq API
            client = Groq(
                api_key=os.environ.get("GROQ_API_KEY"),
            )

            flag = 0
            while True:
                try:
                    if flag > 20:
                        break
                    logger.info("Generating content with model: %s", self.model)
                    response = client.chat.completions.create(
                        messages=groq_messages,
                        model="llama3-70b-8192",
                        max_tokens=max_tokens,
                        top_p=top_p,
                        temperature=temperature
                    )
                    break
                except:
                    if flag == 0:
                        groq_messages = [groq_messages[0]] + groq_messages[-1:]
                    else:
                        groq_messages[-1]["content"] = ' '.join(groq_messages[-1]["content"].split()[:-500])
                    flag = flag + 1

            try:
                return response.choices[0].message.content, self._make_meta(provider="groq")
            except Exception as e:
                print("Failed to call LLM: " + str(e))
                return "", self._make_meta(provider="groq", status="exception", error=str(e)[:500])

        elif self.model.startswith("qwen"):
            messages = payload["messages"]
            max_tokens = payload.get("max_tokens")
            top_p = payload.get("top_p")
            temperature = payload["temperature"]

            qwen_messages = []

            for i, message in enumerate(messages):
                qwen_message = {
                    "role": message["role"],
                    "content": []
                }
                assert len(message["content"]) >= 1, "Each message must have at least one content part"
                for part in message["content"]:
                    qwen_message['content'].append(
                        {"image": "file://" + save_to_tmp_img_file(part['image_url']['url'])}) if part[
                                                                                                      'type'] == "image_url" else None
                    qwen_message['content'].append({"text": part['text']}) if part['type'] == "text" else None

                qwen_messages.append(qwen_message)

            flag = 0
            while True:
                try:
                    if flag > 20:
                        break
                    logger.info("Generating content with model: %s", self.model)

                    if self.model in ["qwen-vl-plus", "qwen-vl-max"]:
                        response = dashscope.MultiModalConversation.call(
                            model=self.model,
                            messages=qwen_messages,
                            result_format="message",
                            max_length=max_tokens,
                            top_p=top_p,
                            temperature=temperature
                        )

                    elif self.model in ["qwen-turbo", "qwen-plus", "qwen-max", "qwen-max-0428", "qwen-max-0403",
                                        "qwen-max-0107", "qwen-max-longcontext"]:
                        response = dashscope.Generation.call(
                            model=self.model,
                            messages=qwen_messages,
                            result_format="message",
                            max_length=max_tokens,
                            top_p=top_p,
                            temperature=temperature
                        )

                    else:
                        raise ValueError("Invalid model: " + self.model)

                    if response.status_code == HTTPStatus.OK:
                        break
                    else:
                        logger.error('Request id: %s, Status code: %s, error code: %s, error message: %s' % (
                            response.request_id, response.status_code,
                            response.code, response.message
                        ))
                        raise Exception("Failed to call LLM: " + response.message)
                except:
                    if flag == 0:
                        qwen_messages = [qwen_messages[0]] + qwen_messages[-1:]
                    else:
                        for i in range(len(qwen_messages[-1]["content"])):
                            if "text" in qwen_messages[-1]["content"][i]:
                                qwen_messages[-1]["content"][i]["text"] = ' '.join(
                                    qwen_messages[-1]["content"][i]["text"].split()[:-500])
                    flag = flag + 1

            try:
                if self.model in ["qwen-vl-plus", "qwen-vl-max"]:
                    return (
                        response['output']['choices'][0]['message']['content'][0]['text'],
                        self._make_meta(provider="dashscope"),
                    )
                else:
                    return (
                        response['output']['choices'][0]['message']['content'],
                        self._make_meta(provider="dashscope"),
                    )

            except Exception as e:
                print("Failed to call LLM: " + str(e))
                return "", self._make_meta(provider="dashscope", status="exception", error=str(e)[:500])

        else:
            raise ValueError("Invalid model: " + self.model)

    def parse_actions(self, response: str, masks=None):
        if self.eval_mode == "gui":
            actions = parse_gui_actions(response)
        elif self.eval_mode == "computer13":
            actions = parse_computer13_actions(response)
        elif self.eval_mode in ("gui-a11y", "gui-screenshot-a11y"):
            actions = parse_gui_actions(response)
        elif self.eval_mode in ("cli", "cli-text"):
            actions = parse_cli_actions(response, allow_readimg=(self.eval_mode == "cli"))
        else:
            raise ValueError("Invalid eval_mode: " + self.eval_mode)
        self.actions.append(actions)
        return actions

    def reset(self, _logger=None, vm_ip=None, **kwargs):
        global logger
        logger = _logger if _logger is not None else logging.getLogger("desktopenv.agent")

        self.vm_ip = vm_ip

        self.thoughts = []
        self.actions = []
        self.observations = []
        self._first_system_text = None
        self._first_user_text = None
        self._pending_parse_error = None
        self._pending_runtime_error = None
        self._llm_attempts = []
