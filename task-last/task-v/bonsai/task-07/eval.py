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

EXPECTED_WINDOW_NAMES = {
    "WINDOW N 2.6",
    "WINDOW N 5.2",
    "WINDOW N 7.8",
    "WINDOW W 10.8",
    "WINDOW W 13.4",
    "WINDOW W 16.0",
}


def emit(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def norm(value):
    text = str(value or "").replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text.strip()).upper()


def close(actual, expected, tol):
    return abs(float(actual) - float(expected)) <= float(tol)


def require_files(root):
    if not (root / "result.ifc").is_file() or (root / "result.ifc").stat().st_size < 100:
        return False
    return True


def product_bbox(product):
    import ifcopenshell.geom
    import numpy as np

    settings = ifcopenshell.geom.settings()
    try:
        settings.set(settings.USE_WORLD_COORDS, True)
    except Exception:
        pass
    shape = ifcopenshell.geom.create_shape(settings, product)
    verts = np.array(shape.geometry.verts, dtype=float).reshape(-1, 3)
    spans = verts.max(axis=0) - verts.min(axis=0)
    return [float(v) for v in spans]


def check_dimensions(elements, width, height, expected_count):
    count = 0
    for element in elements:
        if close(element.OverallWidth, width, 20) and close(element.OverallHeight, height, 20):
            count += 1
    return count == expected_count


def check_opening_relationships(model, facade_wall, filled_products):
    openings = model.by_type("IfcOpeningElement")
    voids = model.by_type("IfcRelVoidsElement")
    fills = model.by_type("IfcRelFillsElement")
    if len(openings) != 8 or len(voids) != 8 or len(fills) != 8:
        return False

    facade_openings = set()
    for rel in voids:
        if rel.RelatingBuildingElement != facade_wall:
            return False
        facade_openings.add(rel.RelatedOpeningElement)
    if facade_openings != set(openings):
        return False

    filled = set()
    for rel in fills:
        if rel.RelatingOpeningElement not in facade_openings:
            return False
        filled.add(rel.RelatedBuildingElement)
    return filled == set(filled_products)


def check_ifc(root):
    if not check_no_gui_bypass(root):
        return False
    import ifcopenshell

    model = ifcopenshell.open(str(root / "result.ifc"))
    if str(model.schema).upper() != "IFC4":
        return False
    if len(model.by_type("IfcProject")) != 1:
        return False
    storeys = model.by_type("IfcBuildingStorey")
    if len(storeys) != 1 or getattr(storeys[0], "Name", None) != "Level 00":
        return False
    if len(model.by_type("IfcBuildingElementProxy")) != 0:
        return False

    walls = model.by_type("IfcWall")
    if len(walls) != 1 or getattr(walls[0], "Name", None) != "Facade Wall":
        return False
    spans = product_bbox(walls[0])
    if not (close(spans[0], 18.0, 0.05) and close(spans[1], 0.25, 0.05) and close(spans[2], 3.6, 0.05)):
        return False

    doors = model.by_type("IfcDoor")
    if len(doors) != 2 or {norm(door.Name) for door in doors} != {"DOOR A", "DOOR B"}:
        return False
    for door in doors:
        if not (close(door.OverallWidth, 950, 20) and close(door.OverallHeight, 2200, 20)):
            return False

    windows = model.by_type("IfcWindow")
    if len(windows) != 6 or {norm(window.Name) for window in windows} != EXPECTED_WINDOW_NAMES:
        return False
    if not check_dimensions(windows, 1200, 1200, 3):
        return False
    if not check_dimensions(windows, 1800, 1400, 3):
        return False

    return check_opening_relationships(model, walls[0], list(doors) + list(windows))


def main():
    try:
        root = DESKTOP
        emit(root.is_dir() and require_files(root) and check_ifc(root))
    except SystemExit:
        raise
    except Exception:
        emit(False)


if __name__ == "__main__":
    main()
