import itertools
import os
from pathlib import Path
import ezdxf

OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "/home/user/Desktop"))
TARGET = "final_ss_gui_10.dxf"
TOL = 0.75


def _close(a, b, tol=TOL):
    return abs(float(a) - float(b)) <= tol


def _point_close(a, b, tol=TOL):
    return _close(a[0], b[0], tol) and _close(a[1], b[1], tol)


def _dedupe(points):
    out = []
    for point in points:
        if not any(_point_close(point, old) for old in out):
            out.append(point)
    return out


def _segment_points(doc):
    points = []
    for entity in doc.modelspace():
        if entity.dxftype() == "LINE":
            start, end = entity.dxf.start, entity.dxf.end
            points.extend([(float(start.x), float(start.y)), (float(end.x), float(end.y))])
        elif entity.dxftype() == "LWPOLYLINE":
            points.extend((float(p[0]), float(p[1])) for p in entity.get_points("xy"))
    return _dedupe(points)


def _trapezoid_center(points):
    if len(points) != 4:
        return None
    ys = sorted(set(round(p[1], 3) for p in points))
    if len(ys) != 2:
        return None
    bottom = sorted([p for p in points if _close(p[1], ys[0])])
    top = sorted([p for p in points if _close(p[1], ys[1])])
    if len(bottom) != 2 or len(top) != 2:
        return None
    bottom_len = abs(bottom[1][0] - bottom[0][0])
    top_len = abs(top[1][0] - top[0][0])
    height = abs(ys[1] - ys[0])
    axis_bottom = (bottom[0][0] + bottom[1][0]) / 2
    axis_top = (top[0][0] + top[1][0]) / 2
    if _close(bottom_len, 140) and _close(top_len, 80) and _close(height, 60) and _close(axis_bottom, axis_top):
        return (axis_bottom, (ys[0] + ys[1]) / 2)
    return None


def _find_trapezoid(doc):
    for entity in doc.modelspace():
        if entity.dxftype() != "LWPOLYLINE":
            continue
        pts = _dedupe([(float(p[0]), float(p[1])) for p in entity.get_points("xy")])
        center = _trapezoid_center(pts)
        if center is not None:
            return center
    points = _segment_points(doc)
    for candidate in itertools.combinations(points, 4):
        center = _trapezoid_center(candidate)
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
    path = OUTPUT_ROOT / TARGET
    if not path.exists() or path.stat().st_size <= 0:
        return False
    doc = ezdxf.readfile(path)
    hole_center = _find_trapezoid(doc)
    return hole_center is not None and _has_circle(doc, hole_center, 10)


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print("True" if ok else "False")
