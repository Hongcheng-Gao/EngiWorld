
from __future__ import annotations

from pathlib import Path
import math
import os
import re

import ezdxf


OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "/home/user/Desktop"))


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

TOL = 0.75


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


def has_no_segment_crossing(doc, layer, y, x1, x2, tol=TOL):
    for a, b in iter_segments(doc, layer):
        ax, ay = a
        bx, by = b
        if close(ay, y, tol) and close(by, y, tol):
            lo, hi = sorted((ax, bx))
            if lo < x2 - tol and hi > x1 + tol and not (hi <= x1 + tol or lo >= x2 - tol):
                return False
    return True


def has_circle(doc, layer, center, radius, tol=TOL):
    return any(pt_close(entity.dxf.center, center, tol) and close(entity.dxf.radius, radius, tol)
               for entity in ents(doc, "CIRCLE", layer))


def count_circles(doc, layer):
    return sum(1 for _ in ents(doc, "CIRCLE", layer))


def angle_close(a, b, tol=3.0):
    return min(abs((a - b) % 360), abs((b - a) % 360)) <= tol


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
    return str(value).upper().replace("Ø", "DIA").replace("⌀", "DIA").replace(" ", "")


def entity_text(entity):
    if entity.dxftype() == "TEXT":
        return str(entity.dxf.text)
    if entity.dxftype() == "MTEXT":
        try:
            return entity.plain_text()
        except Exception:
            return str(entity.text)
    return ""


def text_entities(doc, layer=None):
    for entity in doc.modelspace():
        if entity.dxftype() not in {"TEXT", "MTEXT", "DIMENSION"}:
            continue
        if layer and layer_of(entity) != layer.upper():
            continue
        yield entity


def has_text(doc, layer, value, insert=None, height=None, tol=3.0):
    wanted = norm_text(value)
    for entity in text_entities(doc, layer):
        if entity.dxftype() == "DIMENSION":
            content = str(getattr(entity.dxf, "text", ""))
        else:
            content = entity_text(entity)
        if wanted and wanted not in norm_text(content):
            continue
        if insert is not None and hasattr(entity.dxf, "insert") and not pt_close(entity.dxf.insert, insert, tol):
            continue
        if height is not None and hasattr(entity.dxf, "height") and not close(entity.dxf.height, height, 0.3):
            continue
        return True
    return False


def text_count(doc, layer, value):
    wanted = norm_text(value)
    return sum(1 for entity in text_entities(doc, layer) if wanted in norm_text(entity_text(entity)))


def has_point(doc, layer, point, tol=TOL):
    return any(pt_close(entity.dxf.location, point, tol) for entity in ents(doc, "POINT", layer))


def cycle_match(got, expected, tol=TOL):
    if got and pt_close(got[0], got[-1], 1e-6):
        got = got[:-1]
    exp = list(expected)
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


def has_insert(doc, name, insert, layer=None, tol=TOL):
    for entity in ents(doc, "INSERT", layer):
        if str(entity.dxf.name).upper() == name.upper() and pt_close(entity.dxf.insert, insert, tol):
            return True
    return False


def layer_table(doc, name):
    try:
        return doc.layers.get(name)
    except Exception:
        return None


def layer_linetype(doc, name):
    layer = layer_table(doc, name)
    return "" if layer is None else str(layer.dxf.linetype).upper()


def layer_lineweight(doc, name):
    layer = layer_table(doc, name)
    if layer is None:
        return None
    return int(layer.dxf.lineweight)


def no_entities_on_layer(doc, layer):
    return not any(layer_of(entity) == layer.upper() for entity in doc.modelspace())


OUTPUT_FILE = "gui05_bracket_dimension_completed.dxf"


def annotation_height(doc, entity):
    if entity.dxftype() == "TEXT":
        return float(getattr(entity.dxf, "height", 0.0))
    if entity.dxftype() == "MTEXT":
        return float(getattr(entity.dxf, "char_height", 0.0))
    if entity.dxftype() == "DIMENSION":
        try:
            override = entity.get_acad_dstyle()
            if "dimtxt" in override:
                return float(override["dimtxt"])
        except Exception:
            pass
        try:
            return float(doc.dimstyles.get(entity.dxf.dimstyle).dxf.dimtxt)
        except Exception:
            return 0.0
    return 0.0


def annotation_value(entity):
    if entity.dxftype() in {"TEXT", "MTEXT"}:
        return norm_text(entity_text(entity))
    if entity.dxftype() == "DIMENSION":
        override = str(getattr(entity.dxf, "text", "")).strip()
        if override and override != "<>":
            return norm_text(override)
        try:
            return str(float(entity.get_measurement()))
        except Exception:
            return ""
    return ""


def dim_annotations(doc):
    return [
        (annotation_value(entity), annotation_height(doc, entity))
        for entity in text_entities(doc, "DIM")
    ]


def value_matches(text, wanted):
    numbers = re.findall(r"\d+(?:\.\d+)?", text)
    return any(close(number, wanted, 0.05) for number in numbers)


def has_linear_dimensions(doc):
    annotations = dim_annotations(doc)
    if any(not close(height, 3.5, 0.3) for text, height in annotations if text):
        return False
    return (
        sum(1 for text, _ in annotations if value_matches(text, 160)) >= 1 and
        sum(1 for text, _ in annotations if value_matches(text, 90)) >= 1 and
        sum(1 for text, _ in annotations if value_matches(text, 30)) >= 2
    )


def has_hole_notes(doc):
    diameter_count = 0
    for entity in text_entities(doc, "DIM"):
        text = annotation_value(entity)
        if not value_matches(text, 12):
            continue
        if "2X" in text and "DIA" in text:
            return True
        if entity.dxftype() in {"TEXT", "MTEXT"}:
            if "DIA" in text:
                diameter_count += 1
            continue
        try:
            if int(entity.dxf.dimtype) & 15 == 3:
                diameter_count += 1
        except Exception:
            continue
    return diameter_count >= 2


def check(doc):
    return (
        all(entity.dxftype() != "DIMENSION" or layer_of(entity) == "DIM" for entity in doc.modelspace()) and
        has_polyline_or_edges(doc, "OUTLINE", [(0, 0), (160, 0), (160, 90), (0, 90)]) and
        has_circle(doc, "HOLE", (30, 45), 6) and
        has_circle(doc, "HOLE", (130, 45), 6) and
        has_linear_dimensions(doc) and
        has_hole_notes(doc)
    )


def evaluate():
    if not check_no_gui_bypass(Path(os.environ.get("OUTPUT_ROOT", "/home/user/Desktop"))):
        return False
    path = OUTPUT_ROOT / OUTPUT_FILE
    if not path.exists() or path.stat().st_size <= 0:
        return False
    try:
        doc = ezdxf.readfile(path)
        return bool(check(doc))
    except Exception:
        return False


if __name__ == "__main__":
    print("True" if evaluate() else "False")
