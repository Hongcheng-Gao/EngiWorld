#!/usr/bin/env python3
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

EXPECTED_OPENINGS = 4
EXPECTED_WINDOWS = 3
EXPECTED_DOORS = 1
MIN_WALLS = 4


def emit(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def check_outputs(root):
    path = root / "result.ifc"
    return path.is_file() and path.stat().st_size >= 100


def check_ifc(root):
    if not check_no_gui_bypass(root):
        return False
    import ifcopenshell

    model = ifcopenshell.open(str(root / "result.ifc"))
    if model.schema.upper() != "IFC4":
        return False
    if len(model.by_type("IfcProject")) != 1 or len(model.by_type("IfcSite")) != 1:
        return False
    if len(model.by_type("IfcBuilding")) != 1 or len(model.by_type("IfcBuildingStorey")) != 1:
        return False
    if len(model.by_type("IfcWall")) < MIN_WALLS:
        return False
    if len(model.by_type("IfcDoor")) != EXPECTED_DOORS:
        return False
    if len(model.by_type("IfcWindow")) != EXPECTED_WINDOWS:
        return False
    openings = model.by_type("IfcOpeningElement")
    if len(openings) != EXPECTED_OPENINGS:
        return False
    voids_by_opening = {}
    for rel in model.by_type("IfcRelVoidsElement"):
        opening = getattr(rel, "RelatedOpeningElement", None)
        host = getattr(rel, "RelatingBuildingElement", None)
        if opening is None or host is None or not host.is_a("IfcWall"):
            return False
        voids_by_opening.setdefault(opening.id(), 0)
        voids_by_opening[opening.id()] += 1
    fills_by_opening = {}
    filled_classes = []
    filled_ids = []
    for rel in model.by_type("IfcRelFillsElement"):
        opening = getattr(rel, "RelatingOpeningElement", None)
        element = getattr(rel, "RelatedBuildingElement", None)
        if opening is None or element is None or not (element.is_a("IfcDoor") or element.is_a("IfcWindow")):
            return False
        fills_by_opening.setdefault(opening.id(), 0)
        fills_by_opening[opening.id()] += 1
        filled_classes.append(element.is_a())
        filled_ids.append(element.id())
    if sorted(filled_classes) != sorted(["IfcDoor"] * EXPECTED_DOORS + ["IfcWindow"] * EXPECTED_WINDOWS):
        return False
    expected_filled_ids = {element.id() for element in model.by_type("IfcDoor") + model.by_type("IfcWindow")}
    if set(filled_ids) != expected_filled_ids or len(filled_ids) != len(expected_filled_ids):
        return False
    for opening in openings:
        if voids_by_opening.get(opening.id()) != 1:
            return False
        if fills_by_opening.get(opening.id()) != 1:
            return False
    if model.by_type("IfcBuildingElementProxy") or model.by_type("IfcFurniture"):
        return False
    return True


def main():
    try:
        root = DESKTOP
        emit(root.is_dir() and check_outputs(root) and check_ifc(root))
    except SystemExit:
        raise
    except Exception:
        emit(False)


if __name__ == "__main__":
    main()
