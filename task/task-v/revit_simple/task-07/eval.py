#!/usr/bin/env python3
import re
from pathlib import Path

DESKTOP = Path("C:/Users/user/Desktop")

GUI_BYPASS_FORBIDDEN_EXTENSIONS = {
    ".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".ps1", ".psm1", ".psd1", ".vbs", ".js", ".mjs", ".ts", ".rb",
    ".lua", ".tcl", ".ahk", ".scr"
}
GUI_BYPASS_ALLOWED_FILENAMES = {"eval.py"}
GUI_BYPASS_OUTPUT_TOKENS = ("result.ifc", "result.pdf", "result.csv", "summary.txt")
GUI_BYPASS_COMMAND_TOKENS = (
    "python", "python3", "py ", "powershell", "pwsh", "cmd.exe", "cmd /c",
    "bash", " sh ", "zsh", "node", "ruby", "perl", "ifcopenshell",
    "revitbatchprocessor", "dynamo"
)

SPEC = {'min_bytes': 500, 'space_names': ['Lobby', 'Office'], 'min_counts': {'projects': 1, 'storeys': 1, 'spaces': 2, 'walls': 5, 'slabs': 1, 'doors': 2, 'windows': 2}, 'forbidden': ['IfcBuildingElementProxy']}


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
        home / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt",
        root / ".bash_history",
        root / ".zsh_history",
    ]


def _history_contains_bypass(root):
    for path in _history_paths(root):
        if not path.is_file():
            continue
        text = _read_text_safe(path).lower()
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
    return not _desktop_script_artifacts(root) and not _history_contains_bypass(root)


def finish(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def norm(value):
    return re.sub(r"\s+", " ", str(value or "").replace("_", " ").replace("-", " ").strip()).lower()


def entity_count(model, classes):
    if isinstance(classes, str):
        classes = [classes]
    return sum(len(model.by_type(name)) for name in classes)


def unique_global_ids(model):
    gids = [e.GlobalId for e in model.by_type("IfcRoot") if getattr(e, "GlobalId", None)]
    return bool(gids) and len(gids) == len(set(gids))


def check_min_counts(model):
    class_map = {
        "projects": "IfcProject",
        "storeys": "IfcBuildingStorey",
        "spaces": "IfcSpace",
        "walls": ["IfcWall", "IfcWallStandardCase"],
        "slabs": "IfcSlab",
        "roofs": "IfcRoof",
        "doors": "IfcDoor",
        "windows": "IfcWindow",
        "stairs": "IfcStair",
        "columns": "IfcColumn",
        "beams": "IfcBeam",
        "curtain_walls": "IfcCurtainWall",
    }
    for key, minimum in SPEC.get("min_counts", {}).items():
        if entity_count(model, class_map[key]) < minimum:
            return False
    return True


def check_forbidden(model):
    for ifc_class in SPEC.get("forbidden", []):
        if entity_count(model, ifc_class) > 0:
            return False
    return True


def check_space_names(model):
    names = []
    for space in model.by_type("IfcSpace"):
        names.append(norm(getattr(space, "Name", "")))
        names.append(norm(getattr(space, "LongName", "")))
    for required in SPEC.get("space_names", []):
        token = norm(required)
        if not any(token in name for name in names):
            return False
    return True


def evaluate(root):
    root = Path(root)
    if not check_no_gui_bypass(root):
        return False
    path = root / "result.ifc"
    if not path.is_file() or path.stat().st_size < SPEC.get("min_bytes", 500):
        return False
    import ifcopenshell
    model = ifcopenshell.open(str(path))
    schema = str(getattr(model, "schema", "")).upper()
    return (
        schema.startswith("IFC")
        and unique_global_ids(model)
        and check_min_counts(model)
        and check_forbidden(model)
        and check_space_names(model)
    )


def main():
    try:
        finish(evaluate(DESKTOP))
    except SystemExit:
        raise
    except Exception:
        finish(False)


if __name__ == "__main__":
    main()
