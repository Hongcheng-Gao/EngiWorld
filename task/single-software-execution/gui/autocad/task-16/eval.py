from __future__ import annotations

import os
from pathlib import Path

import ezdxf

OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", r"C:\Users\user\Desktop"))

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

SPEC = {'target': 'autocad_result.dxf',
 'segments': [{'start': [0.0, 0.0], 'end': [220.0, 0.0], 'layer': 'OUTLINE'},
              {'start': [220.0, 0.0], 'end': [240.0, 40.0], 'layer': 'OUTLINE'},
              {'start': [240.0, 40.0], 'end': [210.0, 125.0], 'layer': 'OUTLINE'},
              {'start': [210.0, 125.0], 'end': [145.0, 155.0], 'layer': 'OUTLINE'},
              {'start': [145.0, 155.0], 'end': [80.0, 135.0], 'layer': 'OUTLINE'},
              {'start': [80.0, 135.0], 'end': [35.0, 90.0], 'layer': 'OUTLINE'},
              {'start': [35.0, 90.0], 'end': [0.0, 0.0], 'layer': 'OUTLINE'},
              {'start': [35.0, 90.0], 'end': [220.0, 0.0], 'layer': 'RIB'},
              {'start': [80.0, 135.0], 'end': [145.0, 0.0], 'layer': 'RIB'},
              {'start': [145.0, 155.0], 'end': [210.0, 0.0], 'layer': 'RIB'},
              {'start': [0.0, 0.0], 'end': [145.0, 155.0], 'layer': 'RIB'},
              {'start': [95.0, 130.0], 'end': [145.0, 130.0], 'layer': 'CUTOUT'},
              {'start': [95.0, 120.0], 'end': [145.0, 120.0], 'layer': 'CUTOUT'},
              {'start': [200.0, 47.0], 'end': [200.0, 83.0], 'layer': 'CUTOUT'},
              {'start': [210.0, 47.0], 'end': [210.0, 83.0], 'layer': 'CUTOUT'},
              {'start': [0.0, 77.5], 'end': [240.0, 77.5], 'layer': 'CENTER'},
              {'start': [120.0, 0.0], 'end': [120.0, 155.0], 'layer': 'CENTER'}],
 'circles': [{'center': [35.0, 30.0], 'radius': 8.0, 'layer': 'HOLE'},
             {'center': [190.0, 30.0], 'radius': 8.0, 'layer': 'HOLE'},
             {'center': [95.0, 95.0], 'radius': 12.0, 'layer': 'HOLE'},
             {'center': [165.0, 105.0], 'radius': 10.0, 'layer': 'HOLE'},
             {'center': [120.0, 55.0], 'radius': 6.0, 'layer': 'HOLE'}],
 'arcs': [{'center': [95.0, 125.0], 'radius': 5.0, 'start_angle': 90.0, 'end_angle': 270.0, 'layer': 'CUTOUT'},
          {'center': [145.0, 125.0], 'radius': 5.0, 'start_angle': 270.0, 'end_angle': 90.0, 'layer': 'CUTOUT'},
          {'center': [205.0, 83.0], 'radius': 5.0, 'start_angle': 0.0, 'end_angle': 180.0, 'layer': 'CUTOUT'},
          {'center': [205.0, 47.0], 'radius': 5.0, 'start_angle': 180.0, 'end_angle': 0.0, 'layer': 'CUTOUT'},
          {'center': [35.0, 90.0], 'radius': 20.0, 'start_angle': 180.0, 'end_angle': 300.0, 'layer': 'OUTLINE'},
          {'center': [210.0, 125.0], 'radius': 24.0, 'start_angle': 300.0, 'end_angle': 60.0, 'layer': 'OUTLINE'}],
 'texts': [{'text': 'ACAD-H18', 'layer': 'ANNOTATION'}, {'text': 'ASYM ENGINE MOUNT', 'layer': 'ANNOTATION'}]}
TOL = 0.75
ANGLE_TOL = 2.0
REQUIRED_INSUNITS = 4
REQUIRED_LAYERS = ('ANNOTATION', 'CENTER', 'CUTOUT', 'HOLE', 'OUTLINE', 'REFERENCE', 'RIB')


def _close(a, b, tol=TOL):
    return abs(float(a) - float(b)) <= tol


def _angle_close(a, b, tol=ANGLE_TOL):
    return abs(((float(a) - float(b) + 180.0) % 360.0) - 180.0) <= tol


def _point_close(a, b, tol=TOL):
    return _close(a[0], b[0], tol) and _close(a[1], b[1], tol)


def _layer_ok(actual, expected):
    return expected is None or str(actual).upper() == str(expected).upper()


def _actual_primitives(doc):
    relevant_layers = {name.upper() for name in REQUIRED_LAYERS}
    actual = {"segments": [], "circles": [], "arcs": [], "texts": []}
    for entity in doc.modelspace():
        layer = str(getattr(entity.dxf, "layer", ""))
        if layer.upper() not in relevant_layers:
            continue
        entity_type = entity.dxftype()
        if entity_type == "LINE":
            start, end = entity.dxf.start, entity.dxf.end
            actual["segments"].append(
                ((float(start.x), float(start.y)), (float(end.x), float(end.y)), layer)
            )
        elif entity_type == "LWPOLYLINE":
            points = list(entity.get_points("xyb"))
            edge_count = len(points) if entity.closed else max(0, len(points) - 1)
            for index in range(edge_count):
                start = points[index]
                end = points[(index + 1) % len(points)]
                if abs(float(start[2] or 0.0)) > 1e-12:
                    return None
                actual["segments"].append(
                    ((float(start[0]), float(start[1])), (float(end[0]), float(end[1])), layer)
                )
        elif entity_type == "CIRCLE":
            center = entity.dxf.center
            actual["circles"].append(
                ((float(center.x), float(center.y)), float(entity.dxf.radius), layer)
            )
        elif entity_type == "ARC":
            center = entity.dxf.center
            actual["arcs"].append(
                (
                    (float(center.x), float(center.y)),
                    float(entity.dxf.radius),
                    float(entity.dxf.start_angle),
                    float(entity.dxf.end_angle),
                    layer,
                )
            )
        elif entity_type == "TEXT":
            actual["texts"].append((str(entity.dxf.text).strip(), layer))
        elif entity_type == "MTEXT":
            text = entity.plain_text() if hasattr(entity, "plain_text") else str(entity.text)
            actual["texts"].append((str(text).strip(), layer))
        else:
            return None
    return actual


def _perfect_match(expected, actual, predicate):
    if len(expected) != len(actual):
        return False
    assigned = [-1] * len(actual)

    def assign(expected_index, seen):
        for actual_index, candidate in enumerate(actual):
            if actual_index in seen or not predicate(expected[expected_index], candidate):
                continue
            seen.add(actual_index)
            if assigned[actual_index] < 0 or assign(assigned[actual_index], seen):
                assigned[actual_index] = expected_index
                return True
        return False

    return all(assign(index, set()) for index in range(len(expected)))


def _segment_matches(item, candidate):
    start, end, layer = candidate
    required_start, required_end = tuple(item["start"]), tuple(item["end"])
    return _layer_ok(layer, item.get("layer")) and (
        (_point_close(start, required_start) and _point_close(end, required_end))
        or (_point_close(start, required_end) and _point_close(end, required_start))
    )


def _circle_matches(item, candidate):
    center, radius, layer = candidate
    return (
        _layer_ok(layer, item.get("layer"))
        and _point_close(center, tuple(item["center"]))
        and _close(radius, item["radius"])
    )


def _arc_matches(item, candidate):
    center, radius, start_angle, end_angle, layer = candidate
    return (
        _layer_ok(layer, item.get("layer"))
        and _point_close(center, tuple(item["center"]))
        and _close(radius, item["radius"])
        and _angle_close(start_angle, item["start_angle"])
        and _angle_close(end_angle, item["end_angle"])
    )


def _text_matches(item, candidate):
    value, layer = candidate
    return _layer_ok(layer, item.get("layer")) and value == str(item["text"])



def evaluate() -> bool:
    if not check_no_gui_bypass(Path(os.environ.get("OUTPUT_ROOT", r"C:\Users\user\Desktop"))):
        return False
    path = OUTPUT_ROOT / SPEC["target"]
    if not path.exists() or path.stat().st_size <= 0:
        return False
    doc = ezdxf.readfile(path)
    if int(doc.header.get("$INSUNITS", 0)) != REQUIRED_INSUNITS:
        return False
    document_layers = {str(layer.dxf.name).upper() for layer in doc.layers}
    if not {name.upper() for name in REQUIRED_LAYERS}.issubset(document_layers):
        return False
    actual = _actual_primitives(doc)
    if actual is None:
        return False
    return (
        _perfect_match(SPEC["segments"], actual["segments"], _segment_matches)
        and _perfect_match(SPEC["circles"], actual["circles"], _circle_matches)
        and _perfect_match(SPEC["arcs"], actual["arcs"], _arc_matches)
        and _perfect_match(SPEC["texts"], actual["texts"], _text_matches)
    )


if __name__ == "__main__":
    try:
        if not check_no_gui_bypass(OUTPUT_ROOT):
            ok = False
        else:
            ok = evaluate()
    except Exception:
        ok = False
    print("True" if ok else "False")
