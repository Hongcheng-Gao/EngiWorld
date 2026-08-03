from __future__ import annotations

import re
from pathlib import Path

REQUIRED = ['task-12.nc']
TOOL_SPECS = {
    1: {
        "type": "ENDMILL",
        "dimensions": {
            "DIAMETER": (12.0, "MM"),
            "CUTTING_EDGE_HEIGHT": (25.0, "MM"),
            "LENGTH": (75.0, "MM"),
            "SHANK_DIAMETER": (12.0, "MM"),
        },
        "operation": "FACE",
        "spindle": 6000.0,
        "horizontal_feed": 600.0,
        "vertical_feed": 180.0,
    },
    2: {
        "type": "DRILL",
        "dimensions": {
            "DIAMETER": (6.0, "MM"),
            "LENGTH": (80.0, "MM"),
            "TIP_ANGLE": (118.0, "DEG"),
        },
        "operation": "DRILLING",
        "spindle": 5000.0,
        "horizontal_feed": 180.0,
        "vertical_feed": 180.0,
    },
    3: {
        "type": "ENDMILL",
        "dimensions": {
            "DIAMETER": (8.0, "MM"),
            "CUTTING_EDGE_HEIGHT": (20.0, "MM"),
            "LENGTH": (65.0, "MM"),
            "SHANK_DIAMETER": (8.0, "MM"),
        },
        "operation": "PROFILE_ROUGH",
        "spindle": 7000.0,
        "horizontal_feed": 500.0,
        "vertical_feed": 150.0,
    },
    4: {
        "type": "ENDMILL",
        "dimensions": {
            "DIAMETER": (6.0, "MM"),
            "CUTTING_EDGE_HEIGHT": (18.0, "MM"),
            "LENGTH": (60.0, "MM"),
            "SHANK_DIAMETER": (6.0, "MM"),
        },
        "operation": "PROFILE_FINISH",
        "spindle": 8000.0,
        "horizontal_feed": 300.0,
        "vertical_feed": 100.0,
    },
}
ROOT = Path(__file__).resolve().parent
TARGET = Path("/home/user/Desktop")



GUI_BYPASS_FORBIDDEN_EXTENSIONS = {
    ".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".ps1", ".psm1", ".psd1", ".vbs", ".js", ".mjs", ".ts", ".rb",
    ".lua", ".tcl", ".ahk", ".scr",
}
GUI_BYPASS_ALLOWED_FILENAMES = {"eval.py"}
GUI_BYPASS_OUTPUT_TOKENS = (
    "result.ifc", "result.pdf", "result.osm", "workflow.osw", "summary.txt",
    "report.csv", "result.csv",
    ".dxf", ".dwg", ".step", ".stp", ".fcstd", ".scad", ".stl", ".obj",
    ".db", ".rst", ".rth", ".wbpj", ".odb", ".cae", ".inp",
    ".nc", ".gcode", ".slb", ".ipt", ".sldprt", ".sldasm",
    "autocad_result", "apdl_", "wb_",
)
GUI_BYPASS_COMMAND_TOKENS = (
    "python", "python3", "py ", "powershell", "pwsh", "cmd.exe", "cmd /c",
    "bash", " sh ", "zsh", "node", "ruby", "perl",
    "ifcopenshell", "openstudio", "energyplus",
    "blender --background", "revitbatchprocessor",
    "ansys", "mapdl", "fluent", "abaqus", "cae noGUI",
    "freecad", "freecadcmd", "openscad", "librecad",
    "ezdxf", "cadquery", "accoreconsole", "autolisp",
    "solidworks", "solvespace",
)


def _read_text_safe(path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _desktop_script_artifacts(root):
    if not root.exists() or not root.is_dir():
        return True
    try:
        candidates = list(root.iterdir())
        for directory in list(candidates):
            if directory.is_dir() and directory.name not in {"__pycache__", "_runtime"}:
                try:
                    candidates.extend(directory.iterdir())
                except Exception:
                    pass
        for path in candidates:
            if not path.is_file():
                continue
            if path.name in GUI_BYPASS_ALLOWED_FILENAMES:
                continue
            if path.suffix.lower() in GUI_BYPASS_FORBIDDEN_EXTENSIONS:
                return True
    except Exception:
        return True
    return False


def _history_paths(root):
    home = Path.home()
    return [
        home / ".bash_history",
        home / ".zsh_history",
        home / ".python_history",
        home / ".local/share/fish/fish_history",
        home / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt",
        home / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/Visual Studio Code Host_history.txt",
        root / ".bash_history",
        root / ".zsh_history",
    ]


def _history_contains_bypass(root):
    for path in _history_paths(root):
        if not path.is_file():
            continue
        text = _read_text_safe(path).lower()
        if not text:
            continue
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or "eval.py" in line:
                continue
            touches_output = any(token in line for token in GUI_BYPASS_OUTPUT_TOKENS)
            runs_command = any(token in line for token in GUI_BYPASS_COMMAND_TOKENS)
            writes_file = any(
                token in line for token in (">", "tee ", "cat ", "set-content", "out-file", "new-item")
            )
            if touches_output and (runs_command or writes_file):
                return True
            if ("/desktop/" in line or "\\desktop\\" in line) and any(
                ext in line for ext in GUI_BYPASS_FORBIDDEN_EXTENSIONS
            ) and runs_command:
                return True
    return False


def check_no_gui_bypass(root):
    root = Path(root)
    if _desktop_script_artifacts(root):
        return False
    if _history_contains_bypass(root):
        return False
    return True

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


NUMBER_RE = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
TOOL_CHANGE_RE = re.compile(
    r"^[ \t]*(?:T[ \t]*(\d+)[ \t]+M0?6|M0?6[ \t]+T[ \t]*(\d+))\b[^\r\n]*",
    re.MULTILINE,
)


def _comment_payloads(text: str, kind: str, tool: int) -> list[str]:
    pattern = re.compile(rf"\(\s*{re.escape(kind)}\s+T\s*{tool}\b([^)]*)\)")
    return [match.group(1).strip() for match in pattern.finditer(text)]


def _has_text_value(payload: str, key: str, expected: str) -> bool:
    pattern = rf"(?:^|\s){re.escape(key)}\s*=\s*{re.escape(expected)}(?=\s|$)"
    return re.search(pattern, payload) is not None


def _has_number_value(payload: str, key: str, expected: float, unit: str) -> bool:
    pattern = rf"(?:^|\s){re.escape(key)}\s*=\s*({NUMBER_RE})\s*{re.escape(unit)}(?=\s|$)"
    match = re.search(pattern, payload)
    return match is not None and abs(float(match.group(1)) - expected) <= 1e-6


def _check_spec_comments(text: str) -> bool:
    for tool, spec in TOOL_SPECS.items():
        tool_comments = _comment_payloads(text, "TOOL_SPEC", tool)
        controller_comments = _comment_payloads(text, "TOOL_CONTROLLER", tool)
        if len(tool_comments) != 1 or len(controller_comments) != 1:
            return False

        tool_comment = tool_comments[0]
        if not _has_text_value(tool_comment, "TYPE", str(spec["type"])):
            return False
        for key, (expected, unit) in spec["dimensions"].items():
            if not _has_number_value(tool_comment, key, float(expected), str(unit)):
                return False

        controller_comment = controller_comments[0]
        if not _has_text_value(controller_comment, "OPERATION", str(spec["operation"])):
            return False
        if not _has_number_value(controller_comment, "SPINDLE", float(spec["spindle"]), "RPM"):
            return False
        if not _has_number_value(
            controller_comment, "HORIZONTAL_FEED", float(spec["horizontal_feed"]), "MM/MIN"
        ):
            return False
        if not _has_number_value(
            controller_comment, "VERTICAL_FEED", float(spec["vertical_feed"]), "MM/MIN"
        ):
            return False
    return True


def _tool_blocks(text: str) -> dict[int, str] | None:
    matches = list(TOOL_CHANGE_RE.finditer(text))
    tools = [int(match.group(1) or match.group(2)) for match in matches]
    if tools != list(TOOL_SPECS):
        return None
    return {
        tool: text[match.start(): matches[index + 1].start() if index + 1 < len(matches) else len(text)]
        for index, (tool, match) in enumerate(zip(tools, matches))
    }


def _word_values(text: str, letter: str) -> list[float]:
    return [
        float(match.group(1))
        for match in re.finditer(rf"\b{re.escape(letter)}\s*({NUMBER_RE})\b", text)
    ]


def _operation_precedes_tool_change(text: str, operation: str, tool: int) -> bool:
    operation_matches = list(
        re.finditer(rf"\(\s*OPERATION\s+{re.escape(operation)}\s+T{tool}\s*\)", text)
    )
    tool_change_matches = list(
        re.finditer(
            rf"^[ \t]*(?:T[ \t]*{tool}[ \t]+M0?6|M0?6[ \t]+T[ \t]*{tool})\b[^\r\n]*",
            text,
            re.MULTILINE,
        )
    )
    if len(operation_matches) != 1 or len(tool_change_matches) != 1:
        return False
    if operation_matches[0].end() > tool_change_matches[0].start():
        return False
    between = text[operation_matches[0].end():tool_change_matches[0].start()]
    return not between.strip()


def _check_tool_blocks(text: str) -> bool:
    blocks = _tool_blocks(text)
    if blocks is None:
        return False
    for tool, spec in TOOL_SPECS.items():
        block = blocks[tool]
        expected_spindles = [float(spec["spindle"])]
        expected_feeds = {float(spec["horizontal_feed"]), float(spec["vertical_feed"])}
        if _word_values(block, "S") != expected_spindles:
            return False
        if set(_word_values(block, "F")) != expected_feeds:
            return False
        if len(re.findall(r"\bM0?3\b", block)) != 1:
            return False
        if not _operation_precedes_tool_change(text, str(spec["operation"]), tool):
            return False
    return True


def check_nc(path: Path) -> bool:
    text = read_text(path).upper()
    if "G21" not in text or "G90" not in text or "M30" not in text:
        return False
    if not _check_spec_comments(text) or not _check_tool_blocks(text):
        return False
    if path.suffix.lower() == ".gcode" and path.stat().st_size < 3000:
        return False
    return True






def main() -> bool:
    if not check_no_gui_bypass(TARGET):
        return False
    for rel in REQUIRED:
        path = TARGET / rel
        if not path.exists() or path.stat().st_size == 0:
            return False
        ext = path.suffix.lower()
        if ext in {".nc", ".gcode"} and not check_nc(path):
            return False
    return True

if __name__ == "__main__":
    try:
        if not check_no_gui_bypass(TARGET):
            ok = False
        else:
            ok = main()
    except Exception:
        ok = False
    print("True" if ok else "False")
