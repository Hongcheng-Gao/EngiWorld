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

REQUIRED_OUTPUTS = ("result.ifc",)
STOREY_NAMES = ("Ground Floor", "First Floor")
SPACE_TO_STOREY = {
    "GF Living": "Ground Floor",
    "GF Kitchen": "Ground Floor",
    "FF Bed 1": "First Floor",
    "FF Bed 2": "First Floor",
}
WALL_NAMES = (
    "Ground Floor-S",
    "Ground Floor-N",
    "Ground Floor-W",
    "Ground Floor-E",
    "First Floor-S",
    "First Floor-N",
    "First Floor-W",
    "First Floor-E",
)
SLAB_NAMES = ("GF Slab", "FF Slab")
ROOF_NAMES = ("Main Roof", "Rear Roof")
WINDOW_NAMES = ("Upper North 1", "Upper North 2", "Upper East 1", "Upper East 2")
DOOR_NAMES = ("Main Entry",)
FORBIDDEN_CLASSES = ("IfcBuildingElementProxy", "IfcFurnishingElement")


def emit(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def norm(value):
    return re.sub(r"\s+", " ", str(value or "").replace("_", " ").replace("-", " ").strip()).upper()


def class_count(model, ifc_class):
    return len(model.by_type(ifc_class))


def name_set(entities):
    return {norm(getattr(entity, "Name", "")) for entity in entities}


def check_names(entities, expected):
    return name_set(entities) == {norm(name) for name in expected}


def space_storey_name(space):
    for rel in getattr(space, "Decomposes", []) or []:
        container = getattr(rel, "RelatingObject", None)
        if container is not None and container.is_a("IfcBuildingStorey"):
            return getattr(container, "Name", "")
    for rel in getattr(space, "ContainedInStructure", []) or []:
        container = getattr(rel, "RelatingStructure", None)
        if container is not None and container.is_a("IfcBuildingStorey"):
            return getattr(container, "Name", "")
    return ""


def filled_element_count(model):
    filled_ids = set()
    opening_ids = set()
    for rel in model.by_type("IfcRelFillsElement"):
        element = getattr(rel, "RelatedBuildingElement", None)
        opening = getattr(rel, "RelatingOpeningElement", None)
        if element is None or opening is None:
            return None
        if not (element.is_a("IfcDoor") or element.is_a("IfcWindow")):
            return None
        filled_ids.add(element.id())
        opening_ids.add(opening.id())

    void_opening_ids = set()
    for rel in model.by_type("IfcRelVoidsElement"):
        wall = getattr(rel, "RelatingBuildingElement", None)
        opening = getattr(rel, "RelatedOpeningElement", None)
        if wall is None or opening is None or not wall.is_a("IfcWall"):
            return None
        void_opening_ids.add(opening.id())
    if opening_ids != void_opening_ids:
        return None
    return len(filled_ids)


def check_ifc(path):
    import ifcopenshell

    model = ifcopenshell.open(str(path))
    if model.schema.upper() != "IFC4":
        return False
    expected_counts = {
        "IfcProject": 1,
        "IfcBuildingStorey": 2,
        "IfcSpace": 4,
        "IfcWall": 8,
        "IfcSlab": 2,
        "IfcRoof": 2,
        "IfcDoor": 1,
        "IfcWindow": 4,
        "IfcOpeningElement": 5,
        "IfcRelVoidsElement": 5,
        "IfcRelFillsElement": 5,
    }
    for ifc_class, expected in expected_counts.items():
        if class_count(model, ifc_class) != expected:
            return False
    for ifc_class in FORBIDDEN_CLASSES:
        if class_count(model, ifc_class) != 0:
            return False
    if filled_element_count(model) != 5:
        return False
    checks = (
        check_names(model.by_type("IfcBuildingStorey"), STOREY_NAMES),
        check_names(model.by_type("IfcWall"), WALL_NAMES),
        check_names(model.by_type("IfcSlab"), SLAB_NAMES),
        check_names(model.by_type("IfcRoof"), ROOF_NAMES),
        check_names(model.by_type("IfcDoor"), DOOR_NAMES),
        check_names(model.by_type("IfcWindow"), WINDOW_NAMES),
    )
    if not all(checks):
        return False
    spaces = {norm(getattr(space, "Name", "")): space for space in model.by_type("IfcSpace")}
    if set(spaces) != {norm(name) for name in SPACE_TO_STOREY}:
        return False
    for space_name, storey_name in SPACE_TO_STOREY.items():
        if norm(space_storey_name(spaces[norm(space_name)])) != norm(storey_name):
            return False
    return True


def main():
    try:
        root = DESKTOP
        if not check_no_gui_bypass(root):
            emit(False)
        if not root.is_dir():
            emit(False)
        for name in REQUIRED_OUTPUTS:
            path = root / name
            if not path.is_file() or path.stat().st_size == 0:
                emit(False)
        emit(check_ifc(root / "result.ifc"))
    except SystemExit:
        raise
    except Exception:
        emit(False)


if __name__ == "__main__":
    main()
