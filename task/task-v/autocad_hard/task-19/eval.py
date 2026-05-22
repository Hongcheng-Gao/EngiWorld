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
 'segments': [{'start': [12.0, 0.0], 'end': [268.0, 0.0], 'layer': 'OUTLINE'},
              {'start': [280.0, 12.0], 'end': [280.0, 148.0], 'layer': 'OUTLINE'},
              {'start': [268.0, 160.0], 'end': [12.0, 160.0], 'layer': 'OUTLINE'},
              {'start': [0.0, 148.0], 'end': [0.0, 12.0], 'layer': 'OUTLINE'},
              {'start': [0.0, 0.0], 'end': [280.0, 160.0], 'layer': 'CENTER'},
              {'start': [0.0, 160.0], 'end': [280.0, 0.0], 'layer': 'CENTER'},
              {'start': [140.0, 0.0], 'end': [140.0, 160.0], 'layer': 'CENTER'},
              {'start': [0.0, 80.0], 'end': [280.0, 80.0], 'layer': 'CENTER'},
              {'start': [50.0, 59.0], 'end': [90.0, 59.0], 'layer': 'CUTOUT'},
              {'start': [50.0, 51.0], 'end': [90.0, 51.0], 'layer': 'CUTOUT'},
              {'start': [190.0, 109.0], 'end': [230.0, 109.0], 'layer': 'CUTOUT'},
              {'start': [190.0, 101.0], 'end': [230.0, 101.0], 'layer': 'CUTOUT'},
              {'start': [135.0, 55.0], 'end': [135.0, 105.0], 'layer': 'CUTOUT'},
              {'start': [145.0, 55.0], 'end': [145.0, 105.0], 'layer': 'CUTOUT'}],
 'circles': [{'center': [30.0, 30.0], 'radius': 3.0, 'layer': 'HOLE'},
             {'center': [70.0, 30.0], 'radius': 4.0, 'layer': 'HOLE'},
             {'center': [120.0, 30.0], 'radius': 5.0, 'layer': 'HOLE'},
             {'center': [180.0, 30.0], 'radius': 6.0, 'layer': 'HOLE'},
             {'center': [240.0, 30.0], 'radius': 7.0, 'layer': 'HOLE'},
             {'center': [45.0, 80.0], 'radius': 4.0, 'layer': 'HOLE'},
             {'center': [95.0, 80.0], 'radius': 5.0, 'layer': 'HOLE'},
             {'center': [145.0, 80.0], 'radius': 6.0, 'layer': 'HOLE'},
             {'center': [195.0, 80.0], 'radius': 5.0, 'layer': 'HOLE'},
             {'center': [245.0, 80.0], 'radius': 4.0, 'layer': 'HOLE'},
             {'center': [30.0, 130.0], 'radius': 7.0, 'layer': 'HOLE'},
             {'center': [85.0, 130.0], 'radius': 6.0, 'layer': 'HOLE'},
             {'center': [140.0, 130.0], 'radius': 5.0, 'layer': 'HOLE'},
             {'center': [195.0, 130.0], 'radius': 4.0, 'layer': 'HOLE'},
             {'center': [250.0, 130.0], 'radius': 3.0, 'layer': 'HOLE'}],
 'arcs': [{'center': [12.0, 12.0], 'radius': 12.0, 'start_angle': 180.0, 'end_angle': 270.0, 'layer': 'OUTLINE'},
          {'center': [268.0, 12.0], 'radius': 12.0, 'start_angle': 270.0, 'end_angle': 0.0, 'layer': 'OUTLINE'},
          {'center': [268.0, 148.0], 'radius': 12.0, 'start_angle': 0.0, 'end_angle': 90.0, 'layer': 'OUTLINE'},
          {'center': [12.0, 148.0], 'radius': 12.0, 'start_angle': 90.0, 'end_angle': 180.0, 'layer': 'OUTLINE'},
          {'center': [50.0, 55.0], 'radius': 4.0, 'start_angle': 90.0, 'end_angle': 270.0, 'layer': 'CUTOUT'},
          {'center': [90.0, 55.0], 'radius': 4.0, 'start_angle': 270.0, 'end_angle': 90.0, 'layer': 'CUTOUT'},
          {'center': [190.0, 105.0], 'radius': 4.0, 'start_angle': 90.0, 'end_angle': 270.0, 'layer': 'CUTOUT'},
          {'center': [230.0, 105.0], 'radius': 4.0, 'start_angle': 270.0, 'end_angle': 90.0, 'layer': 'CUTOUT'},
          {'center': [140.0, 105.0], 'radius': 5.0, 'start_angle': 0.0, 'end_angle': 180.0, 'layer': 'CUTOUT'},
          {'center': [140.0, 55.0], 'radius': 5.0, 'start_angle': 180.0, 'end_angle': 0.0, 'layer': 'CUTOUT'}],
 'texts': [{'text': 'ACAD-H19', 'layer': 'ANNOTATION'},
           {'text': 'CAL PLATE REV C', 'layer': 'ANNOTATION'},
           {'text': 'NONUNIFORM HOLES', 'layer': 'ANNOTATION'}]}
TOL = 0.75
ANGLE_TOL = 2.0


def _close(a, b, tol=TOL):
    return abs(float(a) - float(b)) <= tol


def _angle_close(a, b, tol=ANGLE_TOL):
    return abs(((float(a) - float(b) + 180.0) % 360.0) - 180.0) <= tol


def _point_close(a, b, tol=TOL):
    return _close(a[0], b[0], tol) and _close(a[1], b[1], tol)


def _layer_ok(actual, expected):
    return expected is None or str(actual).upper() == str(expected).upper()


def _segments(doc):
    out = []
    for entity in doc.modelspace():
        layer = getattr(entity.dxf, "layer", "")
        if entity.dxftype() == "LINE":
            s, e = entity.dxf.start, entity.dxf.end
            out.append(((float(s.x), float(s.y)), (float(e.x), float(e.y)), layer))
        elif entity.dxftype() == "LWPOLYLINE":
            pts = [(float(p[0]), float(p[1])) for p in entity.get_points("xy")]
            for start, end in zip(pts, pts[1:]):
                out.append((start, end, layer))
            if entity.closed and len(pts) > 2:
                out.append((pts[-1], pts[0], layer))
    return out


def _has_segment(segments, start, end, layer=None):
    start = tuple(start)
    end = tuple(end)
    for a, b, actual_layer in segments:
        if not _layer_ok(actual_layer, layer):
            continue
        if (_point_close(a, start) and _point_close(b, end)) or (_point_close(a, end) and _point_close(b, start)):
            return True
    return False


def _has_circle(doc, center, radius, layer=None):
    center = tuple(center)
    for entity in doc.modelspace():
        if entity.dxftype() != "CIRCLE":
            continue
        if not _layer_ok(getattr(entity.dxf, "layer", ""), layer):
            continue
        c = entity.dxf.center
        if _point_close((c.x, c.y), center) and _close(entity.dxf.radius, radius):
            return True
    return False


def _has_arc(doc, center, radius, start_angle, end_angle, layer=None):
    center = tuple(center)
    for entity in doc.modelspace():
        if entity.dxftype() != "ARC":
            continue
        if not _layer_ok(getattr(entity.dxf, "layer", ""), layer):
            continue
        c = entity.dxf.center
        if (_point_close((c.x, c.y), center)
                and _close(entity.dxf.radius, radius)
                and _angle_close(entity.dxf.start_angle, start_angle)
                and _angle_close(entity.dxf.end_angle, end_angle)):
            return True
    return False


def _has_text(doc, value, layer=None):
    for entity in doc.modelspace():
        if entity.dxftype() == "TEXT":
            txt = str(entity.dxf.text)
        elif entity.dxftype() == "MTEXT":
            txt = str(entity.text)
        else:
            continue
        if not _layer_ok(getattr(entity.dxf, "layer", ""), layer):
            continue
        if txt.strip() == str(value):
            return True
    return False


def evaluate() -> bool:
    if not check_no_gui_bypass(Path(os.environ.get("OUTPUT_ROOT", r"C:\Users\user\Desktop"))):
        return False
    path = OUTPUT_ROOT / SPEC["target"]
    if not path.exists() or path.stat().st_size <= 0:
        return False
    doc = ezdxf.readfile(path)
    segments = _segments(doc)
    for item in SPEC["segments"]:
        if not _has_segment(segments, item["start"], item["end"], item.get("layer")):
            return False
    for item in SPEC["circles"]:
        if not _has_circle(doc, item["center"], item["radius"], item.get("layer")):
            return False
    for item in SPEC["arcs"]:
        if not _has_arc(doc, item["center"], item["radius"], item["start_angle"], item["end_angle"], item.get("layer")):
            return False
    for item in SPEC["texts"]:
        if not _has_text(doc, item["text"], item.get("layer")):
            return False
    return True


if __name__ == "__main__":
    try:
        if not check_no_gui_bypass(OUTPUT_ROOT):
            ok = False
        else:
            ok = evaluate()
    except Exception:
        ok = False
    print("True" if ok else "False")
