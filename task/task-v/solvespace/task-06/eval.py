import itertools
import math
import os
from pathlib import Path
import ezdxf
import sys

_TASK_V_ROOT = Path(__file__).resolve().parents[2]
if str(_TASK_V_ROOT) not in sys.path:
    sys.path.insert(0, str(_TASK_V_ROOT))
from _gui_bypass import check_no_gui_bypass


OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "/home/user/Desktop"))
TARGET = "final_ss_gui_06.dxf"
TOL = 0.75


def _close(a, b, tol=TOL):
    return abs(float(a) - float(b)) <= tol


def _point_close(a, b, tol=TOL):
    return _close(a[0], b[0], tol) and _close(a[1], b[1], tol)


def _dist(a, b):
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def _dedupe(points):
    unique = []
    for point in points:
        if not any(_point_close(point, prev) for prev in unique):
            unique.append(point)
    return unique


def _segment_points(doc):
    points = []
    for entity in doc.modelspace():
        if entity.dxftype() == "LINE":
            start, end = entity.dxf.start, entity.dxf.end
            points.extend([(float(start.x), float(start.y)), (float(end.x), float(end.y))])
        elif entity.dxftype() == "LWPOLYLINE":
            points.extend((float(p[0]), float(p[1])) for p in entity.get_points("xy"))
    return _dedupe(points)


def _regular_hex_center(points):
    if len(points) != 6:
        return None
    center = (sum(p[0] for p in points) / 6, sum(p[1] for p in points) / 6)
    expected_top_y = 40 * math.sin(math.radians(60))
    if not all(_close(_dist(p, center), 40, 1.0) for p in points):
        return None
    rel = sorted((round(p[0] - center[0], 2), round(p[1] - center[1], 2)) for p in points)
    has_left_right = any(_point_close((dx, dy), (-40, 0), 1.0) for dx, dy in rel) and any(_point_close((dx, dy), (40, 0), 1.0) for dx, dy in rel)
    has_top = sum(1 for dx, dy in rel if _close(dy, expected_top_y, 1.0)) == 2
    has_bottom = sum(1 for dx, dy in rel if _close(dy, -expected_top_y, 1.0)) == 2
    if has_left_right and has_top and has_bottom:
        return center
    return None


def _hex_center(doc):
    for entity in doc.modelspace():
        if entity.dxftype() != "LWPOLYLINE":
            continue
        pts = _dedupe([(float(p[0]), float(p[1])) for p in entity.get_points("xy")])
        center = _regular_hex_center(pts)
        if center is not None:
            return center
    points = _segment_points(doc)
    for candidate in itertools.combinations(points, 6):
        center = _regular_hex_center(candidate)
        if center is not None:
            return center
    return None


def _has_circle(doc, center, radius):
    for entity in doc.modelspace():
        if entity.dxftype() != "CIRCLE":
            continue
        c = entity.dxf.center
        if _point_close((c.x, c.y), center) and _close(entity.dxf.radius, radius):
            return True
    return False


def evaluate():
    if not check_no_gui_bypass(Path(os.environ.get("OUTPUT_ROOT", "/home/user/Desktop"))):
        return False
    path = OUTPUT_ROOT / TARGET
    if not path.exists() or path.stat().st_size <= 0:
        return False
    doc = ezdxf.readfile(path)
    center = _hex_center(doc)
    if center is None:
        return False
    return (
        _has_circle(doc, center, 10)
        and _has_circle(doc, (center[0] - 28, center[1]), 3)
        and _has_circle(doc, (center[0] + 28, center[1]), 3)
    )


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print("True" if ok else "False")
