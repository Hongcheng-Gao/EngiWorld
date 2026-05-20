
from __future__ import annotations

from pathlib import Path
import math
import os

import ezdxf
import sys

_TASK_V_ROOT = Path(__file__).resolve().parents[2]
if str(_TASK_V_ROOT) not in sys.path:
    sys.path.insert(0, str(_TASK_V_ROOT))
from _gui_bypass import check_no_gui_bypass



OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "/home/user/Desktop"))
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


OUTPUT_FILE = "gui20_fixture_edit_completed.dxf"


def has_circle_any_layer(doc, center, radius, tol=TOL):
    return any(pt_close(entity.dxf.center, center, tol) and close(entity.dxf.radius, radius, tol)
               for entity in ents(doc, "CIRCLE"))


def has_segment_any_layer(doc, start, end, tol=TOL):
    return any(same_segment(seg, start, end, tol) for seg in iter_segments(doc))


def has_arc_any_layer(doc, center, radius, start_angle, end_angle, tol=TOL):
    for entity in ents(doc, "ARC"):
        if not pt_close(entity.dxf.center, center, tol) or not close(entity.dxf.radius, radius, tol):
            continue
        s = float(entity.dxf.start_angle)
        e = float(entity.dxf.end_angle)
        if (angle_close(s, start_angle) and angle_close(e, end_angle)) or (angle_close(s, end_angle) and angle_close(e, start_angle)):
            return True
    return False


def check(doc):
    corners = [(25, 20), (155, 20), (25, 70), (155, 70)]
    return (
        has_polyline_or_edges(doc, "OUTLINE", [(0, 0), (180, 0), (180, 90), (0, 90)]) and
        all(has_circle_any_layer(doc, c, 5) for c in corners) and
        has_circle_any_layer(doc, (90, 45), 10) and
        has_segment_any_layer(doc, (59, 36), (121, 36)) and
        has_segment_any_layer(doc, (59, 54), (121, 54)) and
        has_arc_any_layer(doc, (59, 45), 9, 90, 270) and
        has_arc_any_layer(doc, (121, 45), 9, 270, 90)
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
