from __future__ import annotations
OUTPUT_FILE = 'guih09_pipe_spool_completed.dxf'
SPEC = {'segments': [{'layer': 'PIPE', 'start': (0, 80), 'end': (90, 80)}, {'layer': 'PIPE', 'start': (130, 120), 'end': (230, 120)}, {'layer': 'PIPE', 'start': (270, 80), 'end': (340, 80)}], 'arcs': [{'layer': 'PIPE', 'center': (110, 100), 'radius': 28.284, 'start': 225, 'end': 45}, {'layer': 'PIPE', 'center': (250, 100), 'radius': 28.284, 'start': 135, 'end': 315}], 'circles': [{'layer': 'FLANGE', 'center': (0, 80), 'radius': 18}, {'layer': 'FLANGE', 'center': (340, 80), 'radius': 18}, {'layer': 'PIPE', 'center': (0, 80), 'radius': 10}, {'layer': 'PIPE', 'center': (340, 80), 'radius': 10}, {'layer': 'NOTE', 'center': (20, 115), 'radius': 8}, {'layer': 'NOTE', 'center': (315, 115), 'radius': 8}], 'polylines': [{'layer': 'SUPPORT', 'points': [(70, 30), (96, 30), (96, 62), (70, 62)]}, {'layer': 'SUPPORT', 'points': [(180, 30), (206, 30), (206, 62), (180, 62)]}, {'layer': 'SUPPORT', 'points': [(290, 30), (316, 30), (316, 62), (290, 62)]}], 'texts': [{'layer': 'TEXT', 'text': 'SPOOL P-17'}, {'layer': 'TEXT', 'text': 'DN80 SCH40'}, {'layer': 'NOTE', 'text': '3X SUPPORTS'}, {'layer': 'NOTE', 'text': '1'}, {'layer': 'NOTE', 'text': '2'}]}


from pathlib import Path
import math
import os

import ezdxf

OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "/home/user/Desktop/result"))

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
    "ansys", "mapdl", "fluent", "abaqus", "cae nogui",
    "freecadcmd", "openscad",
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

TOL = 0.85


def close(a, b, tol=TOL):
    return abs(float(a) - float(b)) <= tol


def xy(value):
    if hasattr(value, "x"):
        return (float(value.x), float(value.y))
    return (float(value[0]), float(value[1]))


def pt_close(a, b, tol=TOL):
    ax, ay = xy(a)
    bx, by = xy(b)
    return close(ax, bx, tol) and close(ay, by, tol)


def layer_of(entity):
    return str(getattr(entity.dxf, "layer", "0")).upper()


def ents(doc, dxftype=None, layer=None):
    wanted = layer.upper() if layer else None
    for entity in doc.modelspace():
        if dxftype and entity.dxftype() != dxftype:
            continue
        if wanted and layer_of(entity) != wanted:
            continue
        yield entity


def poly_points(entity):
    pts = [(float(p[0]), float(p[1])) for p in entity.get_points("xy")]
    if getattr(entity, "closed", False) and pts and not pt_close(pts[0], pts[-1], 1e-6):
        pts.append(pts[0])
    return pts


def iter_segments(doc, layer=None):
    for entity in ents(doc, "LINE", layer):
        yield xy(entity.dxf.start), xy(entity.dxf.end)
    for entity in ents(doc, "LWPOLYLINE", layer):
        pts = poly_points(entity)
        for start, end in zip(pts, pts[1:]):
            yield start, end


def same_segment(seg, start, end, tol=TOL):
    a, b = seg
    return (pt_close(a, start, tol) and pt_close(b, end, tol)) or (pt_close(a, end, tol) and pt_close(b, start, tol))


def has_segment(doc, layer, start, end, tol=TOL):
    return any(same_segment(seg, start, end, tol) for seg in iter_segments(doc, layer))


def has_circle(doc, layer, center, radius, tol=TOL):
    return any(pt_close(entity.dxf.center, center, tol) and close(entity.dxf.radius, radius, tol) for entity in ents(doc, "CIRCLE", layer))


def count_circles(doc, layer):
    return sum(1 for _ in ents(doc, "CIRCLE", layer))


def angle_close(a, b, tol=4.0):
    a = float(a) % 360
    b = float(b) % 360
    d = abs(a - b) % 360
    return min(d, 360 - d) <= tol


def has_arc(doc, layer, center, radius, start_angle=None, end_angle=None, tol=TOL):
    for entity in ents(doc, "ARC", layer):
        if not pt_close(entity.dxf.center, center, tol) or not close(entity.dxf.radius, radius, tol):
            continue
        if start_angle is None or end_angle is None:
            return True
        s = float(entity.dxf.start_angle)
        e = float(entity.dxf.end_angle)
        if angle_close(s, start_angle) and angle_close(e, end_angle):
            return True
        if angle_close(s, end_angle) and angle_close(e, start_angle):
            return True
    return False


def norm_text(value):
    return str(value).upper().replace("Ø", "DIA").replace("⌀", "DIA").replace(" ", "").replace("\\P", "")


def entity_text(entity):
    if entity.dxftype() == "TEXT":
        return str(entity.dxf.text)
    if entity.dxftype() == "MTEXT":
        try:
            return entity.plain_text()
        except Exception:
            return str(entity.text)
    if entity.dxftype() == "DIMENSION":
        return str(getattr(entity.dxf, "text", ""))
    return ""


def text_entities(doc, layer=None):
    for entity in doc.modelspace():
        if entity.dxftype() not in {"TEXT", "MTEXT", "DIMENSION"}:
            continue
        if layer and layer_of(entity) != layer.upper():
            continue
        yield entity


def has_text(doc, layer, value, insert=None, height=None, tol=4.0):
    wanted = norm_text(value)
    for entity in text_entities(doc, layer):
        content = entity_text(entity)
        if wanted and wanted not in norm_text(content):
            continue
        if insert is not None:
            pos = getattr(entity.dxf, "insert", None)
            if pos is None or not pt_close(pos, insert, tol):
                continue
        if height is not None and hasattr(entity.dxf, "height") and not close(entity.dxf.height, height, 0.5):
            continue
        return True
    return False


def text_count(doc, layer, value):
    wanted = norm_text(value)
    return sum(1 for entity in text_entities(doc, layer) if wanted in norm_text(entity_text(entity)))


def cycle_match(points, expected, tol=TOL):
    got = list(points)
    exp = list(expected)
    if got and pt_close(got[0], got[-1], 1e-6):
        got = got[:-1]
    if exp and pt_close(exp[0], exp[-1], 1e-6):
        exp = exp[:-1]
    if len(got) != len(exp):
        return False
    n = len(exp)
    for candidate in (got, list(reversed(got))):
        for offset in range(n):
            if all(pt_close(candidate[(i + offset) % n], exp[i], tol) for i in range(n)):
                return True
    return False


def has_polyline(doc, layer, points, tol=TOL):
    return any(cycle_match(poly_points(entity), points, tol) for entity in ents(doc, "LWPOLYLINE", layer))


def has_closed_edges(doc, layer, points, tol=TOL):
    pts = list(points)
    if not pt_close(pts[0], pts[-1], 1e-6):
        pts.append(pts[0])
    return all(has_segment(doc, layer, pts[i], pts[i + 1], tol) for i in range(len(pts) - 1))


def has_polyline_or_edges(doc, layer, points, tol=TOL):
    return has_polyline(doc, layer, points, tol) or has_closed_edges(doc, layer, points, tol)


def has_insert(doc, name, insert, layer=None, rotation=None, tol=TOL):
    for entity in ents(doc, "INSERT", layer):
        if str(entity.dxf.name).upper() != name.upper():
            continue
        if not pt_close(entity.dxf.insert, insert, tol):
            continue
        if rotation is not None and not angle_close(float(getattr(entity.dxf, "rotation", 0.0)), rotation):
            continue
        return True
    return False


def entity_count(doc, dxftype, layer=None):
    return sum(1 for _ in ents(doc, dxftype, layer))


def no_entities_on_layer(doc, layer):
    return not any(layer_of(entity) == layer.upper() for entity in doc.modelspace())


def has_text_exact(doc, layer, value):
    wanted = norm_text(value)
    for entity in text_entities(doc, layer):
        if norm_text(entity_text(entity)) == wanted:
            return True
    return False


def hatch_path_points(path):
    vertices = getattr(path, "vertices", None)
    if vertices:
        pts = []
        for vertex in vertices:
            try:
                pts.append((float(vertex[0]), float(vertex[1])))
            except Exception:
                pass
        return pts
    edges = getattr(path, "edges", None)
    pts = []
    if edges:
        for edge in edges:
            start = getattr(edge, "start", None)
            if start is not None:
                pts.append(xy(start))
        last = getattr(edges[-1], "end", None)
        if last is not None:
            pts.append(xy(last))
    return pts


def has_hatch_poly(doc, layer, points, tol=TOL):
    for entity in ents(doc, "HATCH", layer):
        for path in getattr(entity, "paths", []):
            pts = hatch_path_points(path)
            if pts and cycle_match(pts, points, tol):
                return True
    return False


def has_lwpolyline_slot(doc, layer, cx, cy, length, width, tol=TOL):
    radius = float(width) / 2.0
    left = float(cx) - float(length) / 2.0 + radius
    right = float(cx) + float(length) / 2.0 - radius
    top = float(cy) + radius
    bottom = float(cy) - radius
    expected = [(left, top), (right, top), (right, bottom), (left, bottom)]
    for entity in ents(doc, "LWPOLYLINE", layer):
        try:
            pts_with_bulge = list(entity.get_points("xyb"))
        except Exception:
            pts_with_bulge = []
        if not pts_with_bulge:
            continue
        pts = [(float(p[0]), float(p[1])) for p in pts_with_bulge]
        if getattr(entity, "closed", False) and pts and not pt_close(pts[0], pts[-1], 1e-6):
            pts.append(pts[0])
        bulge_count = sum(1 for p in pts_with_bulge if len(p) >= 3 and abs(float(p[2])) > 1e-3)
        if bulge_count >= 2 and cycle_match(pts, expected, tol):
            return True
    return False


def has_slot(doc, layer, center, length, width, tol=TOL):
    cx, cy = xy(center)
    radius = float(width) / 2.0
    left = cx - float(length) / 2.0 + radius
    right = cx + float(length) / 2.0 - radius
    top = cy + radius
    bottom = cy - radius
    line_arc_slot = (
        has_segment(doc, layer, (left, top), (right, top), tol) and
        has_segment(doc, layer, (left, bottom), (right, bottom), tol) and
        has_arc(doc, layer, (left, cy), radius, 90, 270, tol) and
        has_arc(doc, layer, (right, cy), radius, 270, 90, tol)
    )
    return line_arc_slot or has_lwpolyline_slot(doc, layer, cx, cy, length, width, tol)


def check_spec(doc):
    for layer in SPEC.get("no_layers", []):
        if not no_entities_on_layer(doc, layer):
            return False
    for item in SPEC.get("polylines", []):
        if not has_polyline_or_edges(doc, item["layer"], item["points"]):
            return False
    for item in SPEC.get("segments", []):
        if not has_segment(doc, item["layer"], item["start"], item["end"]):
            return False
    for item in SPEC.get("slots", []):
        if not has_slot(doc, item["layer"], item["center"], item["length"], item["width"]):
            return False
    for item in SPEC.get("circles", []):
        if not has_circle(doc, item["layer"], item["center"], item["radius"]):
            return False
    for item in SPEC.get("arcs", []):
        if not has_arc(doc, item["layer"], item["center"], item["radius"], item.get("start"), item.get("end")):
            return False
    for item in SPEC.get("hatches", []):
        if not has_hatch_poly(doc, item["layer"], item["points"]):
            return False
    for item in SPEC.get("texts", []):
        if not has_text(doc, item["layer"], item["text"], item.get("insert"), item.get("height")):
            return False
    for item in SPEC.get("texts_exact", []):
        if not has_text_exact(doc, item["layer"], item["text"]):
            return False
    for item in SPEC.get("text_min_counts", []):
        if text_count(doc, item["layer"], item["text"]) < item["min"]:
            return False
    for item in SPEC.get("inserts", []):
        if not has_insert(doc, item["name"], item["insert"], item.get("layer"), item.get("rotation")):
            return False
    for item in SPEC.get("min_counts", []):
        if entity_count(doc, item["type"], item.get("layer")) < item["min"]:
            return False
    for item in SPEC.get("circle_count_min", []):
        if count_circles(doc, item["layer"]) < item["min"]:
            return False
    return True

def evaluate():
    desktop = Path(os.environ.get("ENGIWORLD_DESKTOP", "/home/user/Desktop"))
    root = Path(os.environ.get("OUTPUT_ROOT", str(desktop / "result")))
    if not check_no_gui_bypass(desktop):
        return False
    if not root.is_dir():
        return False
    path = root / OUTPUT_FILE
    if not path.exists() or path.stat().st_size <= 0:
        candidates = sorted(
            p for p in root.iterdir()
            if p.is_file() and p.suffix.lower() in {".dxf", ".dwg"} and p.stat().st_size > 0
        )
        if not candidates:
            return False
        path = candidates[0]
    try:
        doc = ezdxf.readfile(path)
        return bool(check_spec(doc))
    except Exception:
        return False


if __name__ == "__main__":
    print("True" if evaluate() else "False")
