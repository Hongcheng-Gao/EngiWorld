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

EXPECTED_COLUMN_POINTS = {(0.0, 0.0), (6.0, 0.0), (6.0, 4.0), (0.0, 4.0)}


def emit(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def close(actual, expected, tol=0.05):
    return abs(float(actual) - float(expected)) <= tol


def rounded_point(x, y):
    return (round(float(x), 2), round(float(y), 2))


def product_box(product):
    import ifcopenshell.geom
    import numpy as np

    settings = ifcopenshell.geom.settings()
    try:
        settings.set(settings.USE_WORLD_COORDS, True)
    except Exception:
        pass
    shape = ifcopenshell.geom.create_shape(settings, product)
    verts = np.array(shape.geometry.verts, dtype=float).reshape(-1, 3)
    mins = verts.min(axis=0)
    maxs = verts.max(axis=0)
    center = (mins + maxs) / 2.0
    spans = maxs - mins
    return [float(v) for v in spans], [float(v) for v in center]


def spans_match(spans, expected):
    return all(close(actual, target) for actual, target in zip(spans, expected))


def check_analysis_model(model, expected_products):
    analysis_models = model.by_type("IfcStructuralAnalysisModel")
    if len(analysis_models) != 1:
        return False
    analysis = analysis_models[0]
    if analysis.Name != "Section Frame" or analysis.PredefinedType != "LOADING_3D":
        return False
    related = set()
    for rel in model.by_type("IfcRelAssignsToGroup"):
        if rel.RelatingGroup == analysis:
            related.update(rel.RelatedObjects)
    return related == set(expected_products)


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
    if len(model.by_type("IfcProject")) != 1:
        return False
    storeys = model.by_type("IfcBuildingStorey")
    if len(storeys) != 1 or storeys[0].Name != "Level 00":
        return False
    if len(model.by_type("IfcBuildingElementProxy")) != 0:
        return False

    columns = model.by_type("IfcColumn")
    if len(columns) != 4 or {column.Name for column in columns} != {"C1", "C2", "C3", "C4"}:
        return False
    column_points = set()
    for column in columns:
        spans, center = product_box(column)
        if not spans_match(spans, (0.30, 0.30, 3.60)):
            return False
        column_points.add(rounded_point(center[0], center[1]))
    if column_points != EXPECTED_COLUMN_POINTS:
        return False

    beams = model.by_type("IfcBeam")
    if len(beams) != 2 or {beam.Name for beam in beams} != {"Front Beam", "Rear Beam"}:
        return False
    for beam in beams:
        spans, center = product_box(beam)
        if not spans_match(spans, (6.00, 0.30, 0.45)):
            return False
        expected_y = 0.0 if beam.Name == "Front Beam" else 4.0
        if not close(center[1], expected_y) or not close(center[2], 3.10):
            return False

    slabs = model.by_type("IfcSlab")
    if len(slabs) != 1 or slabs[0].Name != "Deck Slab":
        return False
    slab_spans, slab_center = product_box(slabs[0])
    if not spans_match(slab_spans, (6.00, 4.00, 0.16)) or not close(slab_center[2], 3.63):
        return False

    return check_analysis_model(model, list(columns) + list(beams))


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
