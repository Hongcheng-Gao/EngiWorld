from __future__ import annotations

import csv
import json
import re
from pathlib import Path

REQUIRED = ['task-17.nc']
CFG = {'tools': [1], 'z': [4.0], 'ops': ['Job', 'Vcarve', 'Engrave'], 'text': 'OPEN'}
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

def check_nc(path: Path) -> bool:
    text = read_text(path).upper()
    if "G21" not in text or "G90" not in text or "M30" not in text:
        return False
    for tool in CFG.get("tools", []):
        if f"T{tool}" not in text:
            return False
    for spindle in CFG.get("spindles", []):
        if f"S{int(spindle)}" not in text:
            return False
    for feed in CFG.get("feeds", []):
        if f"F{int(feed)}" not in text:
            return False
    for wcs in CFG.get("wcs", []):
        if str(wcs).upper() not in text:
            return False
    if CFG.get("sequence"):
        nums = [int(m.group(1)) for m in re.finditer(r"\bN(\d+)\b", text)]
        if len(nums) < 20 or nums[0] != 10 or any((b - a) != 5 for a, b in zip(nums, nums[1:])):
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
