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

TARGET = "final_ss_gui_17.dxf"

TOL = 0.75





def _close(a, b, tol=TOL):

    return abs(float(a) - float(b)) <= tol





def _point_close(a, b, tol=TOL):

    return _close(a[0], b[0], tol) and _close(a[1], b[1], tol)





def _segments(doc):

    out = []

    for entity in doc.modelspace():

        if entity.dxftype() == "LINE":

            s, e = entity.dxf.start, entity.dxf.end

            out.append(((float(s.x), float(s.y)), (float(e.x), float(e.y)), 0.0))

        elif entity.dxftype() == "LWPOLYLINE":

            pts = [(float(p[0]), float(p[1]), float(p[2])) for p in entity.get_points("xyb")]

            for p1, p2 in zip(pts, pts[1:]):

                out.append(((p1[0], p1[1]), (p2[0], p2[1]), p1[2]))

            if entity.closed and len(pts) > 2:

                p1, p2 = pts[-1], pts[0]

                out.append(((p1[0], p1[1]), (p2[0], p2[1]), p1[2]))

    return out





def _has_segment(segs, start, end, straight=True):

    vx = float(end[0]) - float(start[0])

    vy = float(end[1]) - float(start[1])

    length = (vx * vx + vy * vy) ** 0.5

    if length <= 0:

        return False

    gap_tol = TOL / max(length, 1.0)



    def interval_for(a, b):

        ax = float(a[0]) - float(start[0])

        ay = float(a[1]) - float(start[1])

        bx = float(b[0]) - float(start[0])

        by = float(b[1]) - float(start[1])

        if abs(ax * vy - ay * vx) > TOL * max(length, 1.0):

            return None

        if abs(bx * vy - by * vx) > TOL * max(length, 1.0):

            return None

        t1 = (ax * vx + ay * vy) / (length * length)

        t2 = (bx * vx + by * vy) / (length * length)

        lo, hi = sorted((t1, t2))

        if hi < -gap_tol or lo > 1.0 + gap_tol:

            return None

        return max(0.0, lo), min(1.0, hi)



    intervals = []

    for a, b, bulge in segs:

        if straight and abs(bulge) > 0.05:

            continue

        interval = interval_for(a, b)

        if interval is not None:

            intervals.append(interval)

    if not intervals:

        return False

    covered = 0.0

    for lo, hi in sorted(intervals):

        if hi < covered - gap_tol:

            continue

        if lo > covered + gap_tol:

            return False

        covered = max(covered, hi)

        if covered >= 1.0 - gap_tol:

            return True

    return covered >= 1.0 - gap_tol





def _has_arc_segment(segs, start, end):

    return any(

        abs(bulge) > 0.2 and ((_point_close(a, start) and _point_close(b, end)) or (_point_close(a, end) and _point_close(b, start)))

        for a, b, bulge in segs

    )





def _has_arc_entity(doc, center, radius, endpoints):

    for entity in doc.modelspace():

        if entity.dxftype() != "ARC":

            continue

        c = entity.dxf.center

        if not (_point_close((c.x, c.y), center) and _close(entity.dxf.radius, radius)):

            continue

        actual = []

        for angle in (entity.dxf.start_angle, entity.dxf.end_angle):

            radians = math.radians(float(angle))

            actual.append((c.x + entity.dxf.radius * math.cos(radians), c.y + entity.dxf.radius * math.sin(radians)))

        if all(any(_point_close(p, q) for p in actual) for q in endpoints):

            return True

    return False





def _has_circle(doc, center, radius):

    for entity in doc.modelspace():

        if entity.dxftype() != "CIRCLE":

            continue

        c = entity.dxf.center

        if _point_close((c.x, c.y), center) and _close(entity.dxf.radius, radius):

            return True

    return False





def _has_bridge_outline(doc):

    segs = _segments(doc)

    return (

        _has_segment(segs, (18, 36), (132, 36))

        and _has_segment(segs, (18, 0), (132, 0))

        and (

            _has_arc_segment(segs, (18, 0), (18, 36))

            or _has_arc_entity(doc, (18, 18), 18, [(18, 0), (18, 36)])

            or _has_circle(doc, (18, 18), 18)

        )

        and (

            _has_arc_segment(segs, (132, 36), (132, 0))

            or _has_arc_entity(doc, (132, 18), 18, [(132, 36), (132, 0)])

            or _has_circle(doc, (132, 18), 18)

        )

    )





def evaluate():
    if not check_no_gui_bypass(Path(os.environ.get("OUTPUT_ROOT", "/home/user/Desktop"))):
        return False

    path = OUTPUT_ROOT / TARGET

    if not path.exists() or path.stat().st_size <= 0:

        return False

    doc = ezdxf.readfile(path)

    holes = [(30, 18), (75, 18), (120, 18)]

    return _has_bridge_outline(doc) and all(_has_circle(doc, p, 3) for p in holes)





if __name__ == "__main__":

    try:

        ok = evaluate()

    except Exception:

        ok = False

    print("True" if ok else "False")
