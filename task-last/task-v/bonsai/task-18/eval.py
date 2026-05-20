#!/usr/bin/env python3
import re
from pathlib import Path


DESKTOP = Path("/home/user/Desktop")


GUI_BYPASS_FORBIDDEN_EXTENSIONS = {
    ".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".ps1", ".psm1", ".psd1", ".vbs", ".js", ".mjs", ".ts", ".rb",
    ".lua", ".tcl", ".ahk", ".scr"
}
GUI_BYPASS_ALLOWED_FILENAMES = {"eval.py"}
GUI_BYPASS_OUTPUT_TOKENS = (
    "result.ifc", "result.pdf", "result.osm", "workflow.osw", "summary.txt",
    "report.csv", "result.csv"
)
GUI_BYPASS_COMMAND_TOKENS = (
    "python", "python3", "py ", "powershell", "pwsh", "cmd.exe", "cmd /c",
    "bash", " sh ", "zsh", "node", "ruby", "perl", "ifcopenshell",
    "openstudio", "energyplus", "blender --background", "revitbatchprocessor"
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
    paths = [
        home / ".bash_history",
        home / ".zsh_history",
        home / ".python_history",
        home / ".local/share/fish/fish_history",
        home / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt",
        home / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/Visual Studio Code Host_history.txt",
        root / ".bash_history",
        root / ".zsh_history",
    ]
    return paths


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
            writes_file = any(token in line for token in (">", "tee ", "cat ", "set-content", "out-file", "new-item"))
            if touches_output and (runs_command or writes_file):
                return True
            if ("/desktop/" in line or "\\desktop\\" in line) and any(ext in line for ext in GUI_BYPASS_FORBIDDEN_EXTENSIONS) and runs_command:
                return True
    return False


def check_no_gui_bypass(root):
    root = Path(root)
    if _desktop_script_artifacts(root):
        return False
    if _history_contains_bypass(root):
        return False
    return True

REQUIRED_OUTPUT = "result.ifc"
SPACE_NAMES = ("Unit A", "Unit B", "Unit C")
WALL_NAMES = ("Shell-S", "Shell-N", "Shell-W", "Shell-E", "Party-AB", "Party-BC")
FORBIDDEN_CLASSES = (
    "IfcBuildingElementProxy",
    "IfcFurnishingElement",
    "IfcDoor",
    "IfcWindow",
    "IfcOpeningElement",
    "IfcRelVoidsElement",
    "IfcRelFillsElement",
)


def emit(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def norm(value):
    return re.sub(r"\s+", " ", str(value or "").replace("_", " ").replace("-", " ").strip()).upper()


def class_count(model, ifc_class):
    return len(model.by_type(ifc_class))


def check_names(entities, expected):
    return {norm(getattr(entity, "Name", "")) for entity in entities} == {norm(name) for name in expected}


def check_ifc(path):
    import ifcopenshell

    model = ifcopenshell.open(str(path))
    if model.schema.upper() != "IFC4":
        return False
    expected_counts = {
        "IfcProject": 1,
        "IfcBuildingStorey": 1,
        "IfcSpace": 3,
        "IfcWall": 6,
        "IfcSlab": 1,
    }
    for ifc_class, expected in expected_counts.items():
        if class_count(model, ifc_class) != expected:
            return False
    for ifc_class in FORBIDDEN_CLASSES:
        if class_count(model, ifc_class) != 0:
            return False
    if not check_names(model.by_type("IfcSpace"), SPACE_NAMES):
        return False
    if not check_names(model.by_type("IfcWall"), WALL_NAMES):
        return False
    party_walls = [wall for wall in model.by_type("IfcWall") if norm(getattr(wall, "Name", "")).startswith("PARTY")]
    return len(party_walls) == 2


def main():
    try:
        root = DESKTOP
        if not check_no_gui_bypass(root):
            emit(False)
        path = root / REQUIRED_OUTPUT
        emit(root.is_dir() and path.is_file() and path.stat().st_size > 0 and check_ifc(path))
    except SystemExit:
        raise
    except Exception:
        emit(False)


if __name__ == "__main__":
    main()
