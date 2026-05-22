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
 'segments': [{'start': [25.0, 0.0], 'end': [395.0, 0.0], 'layer': 'OUTLINE'},
              {'start': [420.0, 25.0], 'end': [420.0, 195.0], 'layer': 'OUTLINE'},
              {'start': [395.0, 220.0], 'end': [25.0, 220.0], 'layer': 'OUTLINE'},
              {'start': [0.0, 195.0], 'end': [0.0, 25.0], 'layer': 'OUTLINE'},
              {'start': [55.0, 35.0], 'end': [365.0, 35.0], 'layer': 'RAIL'},
              {'start': [365.0, 35.0], 'end': [365.0, 60.0], 'layer': 'RAIL'},
              {'start': [365.0, 60.0], 'end': [55.0, 60.0], 'layer': 'RAIL'},
              {'start': [55.0, 60.0], 'end': [55.0, 35.0], 'layer': 'RAIL'},
              {'start': [55.0, 160.0], 'end': [365.0, 160.0], 'layer': 'RAIL'},
              {'start': [365.0, 160.0], 'end': [365.0, 185.0], 'layer': 'RAIL'},
              {'start': [365.0, 185.0], 'end': [55.0, 185.0], 'layer': 'RAIL'},
              {'start': [55.0, 185.0], 'end': [55.0, 160.0], 'layer': 'RAIL'},
              {'start': [120.0, 80.0], 'end': [300.0, 80.0], 'layer': 'CUTOUT'},
              {'start': [300.0, 80.0], 'end': [300.0, 140.0], 'layer': 'CUTOUT'},
              {'start': [300.0, 140.0], 'end': [120.0, 140.0], 'layer': 'CUTOUT'},
              {'start': [120.0, 140.0], 'end': [120.0, 80.0], 'layer': 'CUTOUT'},
              {'start': [62.0, 116.0], 'end': [118.0, 116.0], 'layer': 'CUTOUT'},
              {'start': [62.0, 104.0], 'end': [118.0, 104.0], 'layer': 'CUTOUT'},
              {'start': [302.0, 116.0], 'end': [358.0, 116.0], 'layer': 'CUTOUT'},
              {'start': [302.0, 104.0], 'end': [358.0, 104.0], 'layer': 'CUTOUT'},
              {'start': [205.0, 17.0], 'end': [205.0, 53.0], 'layer': 'CUTOUT'},
              {'start': [215.0, 17.0], 'end': [215.0, 53.0], 'layer': 'CUTOUT'},
              {'start': [205.0, 167.0], 'end': [205.0, 203.0], 'layer': 'CUTOUT'},
              {'start': [215.0, 167.0], 'end': [215.0, 203.0], 'layer': 'CUTOUT'},
              {'start': [0.0, 110.0], 'end': [420.0, 110.0], 'layer': 'CENTER'},
              {'start': [210.0, 0.0], 'end': [210.0, 220.0], 'layer': 'CENTER'},
              {'start': [55.0, 35.0], 'end': [365.0, 185.0], 'layer': 'CENTER'},
              {'start': [55.0, 185.0], 'end': [365.0, 35.0], 'layer': 'CENTER'}],
 'circles': [{'center': [70.0, 47.5], 'radius': 4.0, 'layer': 'HOLE'},
             {'center': [70.0, 172.5], 'radius': 4.0, 'layer': 'HOLE'},
             {'center': [115.0, 47.5], 'radius': 4.0, 'layer': 'HOLE'},
             {'center': [115.0, 172.5], 'radius': 4.0, 'layer': 'HOLE'},
             {'center': [160.0, 47.5], 'radius': 4.0, 'layer': 'HOLE'},
             {'center': [160.0, 172.5], 'radius': 4.0, 'layer': 'HOLE'},
             {'center': [205.0, 47.5], 'radius': 4.0, 'layer': 'HOLE'},
             {'center': [205.0, 172.5], 'radius': 4.0, 'layer': 'HOLE'},
             {'center': [250.0, 47.5], 'radius': 4.0, 'layer': 'HOLE'},
             {'center': [250.0, 172.5], 'radius': 4.0, 'layer': 'HOLE'},
             {'center': [295.0, 47.5], 'radius': 4.0, 'layer': 'HOLE'},
             {'center': [295.0, 172.5], 'radius': 4.0, 'layer': 'HOLE'},
             {'center': [340.0, 47.5], 'radius': 4.0, 'layer': 'HOLE'},
             {'center': [340.0, 172.5], 'radius': 4.0, 'layer': 'HOLE'},
             {'center': [40.0, 40.0], 'radius': 8.0, 'layer': 'HOLE'},
             {'center': [380.0, 40.0], 'radius': 8.0, 'layer': 'HOLE'},
             {'center': [40.0, 180.0], 'radius': 8.0, 'layer': 'HOLE'},
             {'center': [380.0, 180.0], 'radius': 8.0, 'layer': 'HOLE'},
             {'center': [210.0, 110.0], 'radius': 18.0, 'layer': 'HOLE'}],
 'arcs': [{'center': [25.0, 25.0], 'radius': 25.0, 'start_angle': 180.0, 'end_angle': 270.0, 'layer': 'OUTLINE'},
          {'center': [395.0, 25.0], 'radius': 25.0, 'start_angle': 270.0, 'end_angle': 0.0, 'layer': 'OUTLINE'},
          {'center': [395.0, 195.0], 'radius': 25.0, 'start_angle': 0.0, 'end_angle': 90.0, 'layer': 'OUTLINE'},
          {'center': [25.0, 195.0], 'radius': 25.0, 'start_angle': 90.0, 'end_angle': 180.0, 'layer': 'OUTLINE'},
          {'center': [62.0, 110.0], 'radius': 6.0, 'start_angle': 90.0, 'end_angle': 270.0, 'layer': 'CUTOUT'},
          {'center': [118.0, 110.0], 'radius': 6.0, 'start_angle': 270.0, 'end_angle': 90.0, 'layer': 'CUTOUT'},
          {'center': [302.0, 110.0], 'radius': 6.0, 'start_angle': 90.0, 'end_angle': 270.0, 'layer': 'CUTOUT'},
          {'center': [358.0, 110.0], 'radius': 6.0, 'start_angle': 270.0, 'end_angle': 90.0, 'layer': 'CUTOUT'},
          {'center': [210.0, 53.0], 'radius': 5.0, 'start_angle': 0.0, 'end_angle': 180.0, 'layer': 'CUTOUT'},
          {'center': [210.0, 17.0], 'radius': 5.0, 'start_angle': 180.0, 'end_angle': 0.0, 'layer': 'CUTOUT'},
          {'center': [210.0, 203.0], 'radius': 5.0, 'start_angle': 0.0, 'end_angle': 180.0, 'layer': 'CUTOUT'},
          {'center': [210.0, 167.0], 'radius': 5.0, 'start_angle': 180.0, 'end_angle': 0.0, 'layer': 'CUTOUT'},
          {'center': [210.0, 110.0], 'radius': 70.0, 'start_angle': 30.0, 'end_angle': 70.0, 'layer': 'RIB'},
          {'center': [210.0, 110.0], 'radius': 70.0, 'start_angle': 110.0, 'end_angle': 150.0, 'layer': 'RIB'},
          {'center': [210.0, 110.0], 'radius': 70.0, 'start_angle': 210.0, 'end_angle': 250.0, 'layer': 'RIB'},
          {'center': [210.0, 110.0], 'radius': 70.0, 'start_angle': 290.0, 'end_angle': 330.0, 'layer': 'RIB'}],
 'texts': [{'text': 'ACAD-H20', 'layer': 'ANNOTATION'}, {'text': 'MACHINE BED MASTER', 'layer': 'ANNOTATION'}]}
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
