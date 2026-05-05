import math

import os

from pathlib import Path

import ezdxf



OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "/home/user/Desktop"))

TARGET = "final_ss_gui_19.dxf"

TOL = 0.75

ANGLE_TOL = 2.0





def _close(a, b, tol=TOL):

    return abs(float(a) - float(b)) <= tol





def _angle_close(a, b, tol=ANGLE_TOL):

    return abs(((float(a) - float(b) + 180) % 360) - 180) <= tol





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





def _arc_span(entity):

    return (float(entity.dxf.end_angle) - float(entity.dxf.start_angle)) % 360





def _angle_on_arc(entity, angle):

    start = float(entity.dxf.start_angle) % 360

    span = _arc_span(entity)

    delta = (float(angle) - start) % 360

    return delta <= span + ANGLE_TOL or _angle_close(delta, 0) or _angle_close(delta, span)





def _arcs_cover_open_ring(arcs, center, radius):

    relevant = []

    for entity in arcs:

        c = entity.dxf.center

        if _point_close((c.x, c.y), center) and _close(entity.dxf.radius, radius):

            relevant.append(entity)

    if not relevant:

        return False

    required_angles = [0, 90, 180, 270]

    if not all(any(_angle_on_arc(entity, angle) for entity in relevant) for angle in required_angles):

        return False

    return not any(_angle_on_arc(entity, 315) for entity in relevant)





def _find_ring_center(doc):

    arcs = [entity for entity in doc.modelspace() if entity.dxftype() == "ARC"]

    centers = []

    for entity in arcs:

        if not _close(entity.dxf.radius, 60):

            continue

        c = entity.dxf.center

        center = (float(c.x), float(c.y))

        if not any(_point_close(center, old) for old in centers):

            centers.append(center)

    for center in centers:

        if _arcs_cover_open_ring(arcs, center, 60) and _arcs_cover_open_ring(arcs, center, 40):

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

    center = _find_ring_center(doc)

    if center is None:

        return False

    segs = _segments(doc)

    if not _has_segment(segs, (center[0] + 40, center[1]), (center[0] + 60, center[1])):

        return False

    if not _has_segment(segs, (center[0], center[1] - 40), (center[0], center[1] - 60)):

        return False

    for angle in [0, 90, 180]:

        expected = (

            center[0] + 50 * math.cos(math.radians(angle)),

            center[1] + 50 * math.sin(math.radians(angle)),

        )

        if not _has_circle(doc, expected, 3):

            return False

    return True





if __name__ == "__main__":

    try:

        ok = evaluate()

    except Exception:

        ok = False

    print("True" if ok else "False")
