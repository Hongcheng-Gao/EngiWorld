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
 'segments': [{'start': [0.0, 0.0], 'end': [360.0, 0.0], 'layer': 'OUTLINE'},
              {'start': [360.0, 0.0], 'end': [360.0, 45.0], 'layer': 'OUTLINE'},
              {'start': [360.0, 45.0], 'end': [0.0, 45.0], 'layer': 'OUTLINE'},
              {'start': [0.0, 45.0], 'end': [0.0, 0.0], 'layer': 'OUTLINE'},
              {'start': [20.0, 45.0], 'end': [27.5, 65.0], 'layer': 'TOOTH'},
              {'start': [27.5, 65.0], 'end': [35.0, 45.0], 'layer': 'TOOTH'},
              {'start': [35.0, 45.0], 'end': [47.5, 65.0], 'layer': 'TOOTH'},
              {'start': [47.5, 65.0], 'end': [55.0, 45.0], 'layer': 'TOOTH'},
              {'start': [55.0, 45.0], 'end': [67.5, 65.0], 'layer': 'TOOTH'},
              {'start': [67.5, 65.0], 'end': [75.0, 45.0], 'layer': 'TOOTH'},
              {'start': [75.0, 45.0], 'end': [87.5, 65.0], 'layer': 'TOOTH'},
              {'start': [87.5, 65.0], 'end': [95.0, 45.0], 'layer': 'TOOTH'},
              {'start': [95.0, 45.0], 'end': [107.5, 65.0], 'layer': 'TOOTH'},
              {'start': [107.5, 65.0], 'end': [115.0, 45.0], 'layer': 'TOOTH'},
              {'start': [115.0, 45.0], 'end': [127.5, 65.0], 'layer': 'TOOTH'},
              {'start': [127.5, 65.0], 'end': [135.0, 45.0], 'layer': 'TOOTH'},
              {'start': [135.0, 45.0], 'end': [147.5, 65.0], 'layer': 'TOOTH'},
              {'start': [147.5, 65.0], 'end': [155.0, 45.0], 'layer': 'TOOTH'},
              {'start': [155.0, 45.0], 'end': [167.5, 65.0], 'layer': 'TOOTH'},
              {'start': [167.5, 65.0], 'end': [175.0, 45.0], 'layer': 'TOOTH'},
              {'start': [175.0, 45.0], 'end': [187.5, 65.0], 'layer': 'TOOTH'},
              {'start': [187.5, 65.0], 'end': [195.0, 45.0], 'layer': 'TOOTH'},
              {'start': [195.0, 45.0], 'end': [207.5, 65.0], 'layer': 'TOOTH'},
              {'start': [207.5, 65.0], 'end': [215.0, 45.0], 'layer': 'TOOTH'},
              {'start': [215.0, 45.0], 'end': [227.5, 65.0], 'layer': 'TOOTH'},
              {'start': [227.5, 65.0], 'end': [235.0, 45.0], 'layer': 'TOOTH'},
              {'start': [235.0, 45.0], 'end': [247.5, 65.0], 'layer': 'TOOTH'},
              {'start': [247.5, 65.0], 'end': [255.0, 45.0], 'layer': 'TOOTH'},
              {'start': [255.0, 45.0], 'end': [267.5, 65.0], 'layer': 'TOOTH'},
              {'start': [267.5, 65.0], 'end': [275.0, 45.0], 'layer': 'TOOTH'},
              {'start': [275.0, 45.0], 'end': [287.5, 65.0], 'layer': 'TOOTH'},
              {'start': [287.5, 65.0], 'end': [295.0, 45.0], 'layer': 'TOOTH'},
              {'start': [295.0, 45.0], 'end': [307.5, 65.0], 'layer': 'TOOTH'},
              {'start': [307.5, 65.0], 'end': [315.0, 45.0], 'layer': 'TOOTH'},
              {'start': [315.0, 45.0], 'end': [327.5, 65.0], 'layer': 'TOOTH'},
              {'start': [327.5, 65.0], 'end': [335.0, 45.0], 'layer': 'TOOTH'},
              {'start': [68.0, 27.5], 'end': [112.0, 27.5], 'layer': 'CUTOUT'},
              {'start': [68.0, 17.5], 'end': [112.0, 17.5], 'layer': 'CUTOUT'},
              {'start': [248.0, 27.5], 'end': [292.0, 27.5], 'layer': 'CUTOUT'},
              {'start': [248.0, 17.5], 'end': [292.0, 17.5], 'layer': 'CUTOUT'},
              {'start': [0.0, 22.5], 'end': [360.0, 22.5], 'layer': 'CENTER'},
              {'start': [20.0, 45.0], 'end': [340.0, 45.0], 'layer': 'CENTER'}],
 'circles': [{'center': [35.0, 22.5], 'radius': 4.5, 'layer': 'HOLE'},
             {'center': [85.0, 22.5], 'radius': 4.5, 'layer': 'HOLE'},
             {'center': [135.0, 22.5], 'radius': 4.5, 'layer': 'HOLE'},
             {'center': [185.0, 22.5], 'radius': 4.5, 'layer': 'HOLE'},
             {'center': [235.0, 22.5], 'radius': 4.5, 'layer': 'HOLE'},
             {'center': [285.0, 22.5], 'radius': 4.5, 'layer': 'HOLE'},
             {'center': [335.0, 22.5], 'radius': 4.5, 'layer': 'HOLE'}],
 'arcs': [{'center': [68.0, 22.5], 'radius': 5.0, 'start_angle': 90.0, 'end_angle': 270.0, 'layer': 'CUTOUT'},
          {'center': [112.0, 22.5], 'radius': 5.0, 'start_angle': 270.0, 'end_angle': 90.0, 'layer': 'CUTOUT'},
          {'center': [248.0, 22.5], 'radius': 5.0, 'start_angle': 90.0, 'end_angle': 270.0, 'layer': 'CUTOUT'},
          {'center': [292.0, 22.5], 'radius': 5.0, 'start_angle': 270.0, 'end_angle': 90.0, 'layer': 'CUTOUT'}],
 'texts': [{'text': 'ACAD-H17', 'layer': 'ANNOTATION'}, {'text': 'RACK STRIP 16T', 'layer': 'ANNOTATION'}]}
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
