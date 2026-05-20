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

EXPECTED_NAMES = {
    "IfcDuctSegment": {"Supply Segment 1", "Supply Segment 2"},
    "IfcDuctFitting": {"Branch Fitting"},
    "IfcAirTerminal": {"Terminal South", "Terminal East"},
}
EXPECTED_COUNTS = {
    "IfcProject": 1,
    "IfcBuildingStorey": 1,
    "IfcBuildingElementProxy": 0,
    "IfcDuctSegment": 2,
    "IfcDuctFitting": 1,
    "IfcAirTerminal": 2,
    "IfcDistributionSystem": 1,
}
EXPECTED_SPANS = {
    "Supply Segment 1": (1.80, 0.35, 0.25),
    "Supply Segment 2": (1.40, 0.30, 0.25),
    "Branch Fitting": (0.45, 0.40, 0.30),
    "Terminal South": (0.40, 0.40, 0.20),
    "Terminal East": (0.40, 0.40, 0.20),
}


def emit(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def close(actual, expected, tol=0.05):
    return abs(float(actual) - float(expected)) <= tol


def product_spans(product):
    import ifcopenshell.geom
    import numpy as np

    settings = ifcopenshell.geom.settings()
    try:
        settings.set(settings.USE_WORLD_COORDS, True)
    except Exception:
        pass
    shape = ifcopenshell.geom.create_shape(settings, product)
    verts = np.array(shape.geometry.verts, dtype=float).reshape(-1, 3)
    return [float(v) for v in (verts.max(axis=0) - verts.min(axis=0))]


def contained_in_storey(product, storey):
    return any(rel.RelatingStructure == storey for rel in (getattr(product, "ContainedInStructure", []) or []))


def check_geometry(products_by_name):
    for name, expected in EXPECTED_SPANS.items():
        spans = product_spans(products_by_name[name])
        if any(not close(actual, target) for actual, target in zip(spans, expected)):
            return False
    return True


def check_system(model, products_by_name):
    systems = model.by_type("IfcDistributionSystem")
    if len(systems) != 1 or systems[0].Name != "Supply Air":
        return False
    related = set()
    for rel in model.by_type("IfcRelAssignsToGroup"):
        if rel.RelatingGroup == systems[0]:
            related.update(rel.RelatedObjects)
    return related == set(products_by_name.values())


def check_ifc(root):
    if not check_no_gui_bypass(root):
        return False
    import ifcopenshell

    path = root / "result.ifc"
    if not path.is_file() or path.stat().st_size < 100:
        return False
    model = ifcopenshell.open(str(path))
    if str(model.schema).upper() != "IFC4":
        return False
    for cls, expected in EXPECTED_COUNTS.items():
        if len(model.by_type(cls)) != expected:
            return False

    storey = model.by_type("IfcBuildingStorey")[0]
    if storey.Name != "Level 00":
        return False

    products_by_name = {}
    for cls, names in EXPECTED_NAMES.items():
        elements = model.by_type(cls)
        if {element.Name for element in elements} != names:
            return False
        for element in elements:
            if not contained_in_storey(element, storey):
                return False
            products_by_name[element.Name] = element

    return check_system(model, products_by_name) and check_geometry(products_by_name)


def main():
    try:
        root = DESKTOP
        emit(root.is_dir() and check_ifc(root))
    except SystemExit:
        raise
    except Exception:
        emit(False)


if __name__ == "__main__":
    main()
