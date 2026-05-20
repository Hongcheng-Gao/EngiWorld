import os

from pathlib import Path

import ezdxf
import sys

_TASK_V_ROOT = Path(__file__).resolve().parents[2]
if str(_TASK_V_ROOT) not in sys.path:
    sys.path.insert(0, str(_TASK_V_ROOT))
from _gui_bypass import check_no_gui_bypass




OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "/home/user/Desktop"))

TARGET = "final_ss_gui_05.dxf"

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

            out.append(((float(s.x), float(s.y)), (float(e.x), float(e.y))))

        elif entity.dxftype() == "LWPOLYLINE":

            pts = [(float(p[0]), float(p[1])) for p in entity.get_points("xy")]

            out.extend(zip(pts, pts[1:]))

            if entity.closed and len(pts) > 2:

                out.append((pts[-1], pts[0]))

    return out





def _has_segment(segments, start, end):

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

    for a, b in segments:

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





def _has_rect_at(doc, x0, y0, x1, y1):

    segs = _segments(doc)

    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

    return all(_has_segment(segs, corners[i], corners[(i + 1) % 4]) for i in range(4))





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

    holes = [(15, 15), (145, 15), (15, 85), (145, 85)]

    return (

        _has_rect_at(doc, 0, 0, 160, 100)

        and _has_rect_at(doc, 30, 25, 130, 75)

        and all(_has_circle(doc, p, 4) for p in holes)

    )





if __name__ == "__main__":

    try:

        ok = evaluate()

    except Exception:

        ok = False

    print("True" if ok else "False")
