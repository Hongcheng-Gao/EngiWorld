import math
import os
from pathlib import Path
import ezdxf

OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "/home/user/Desktop"))
TARGET = "final_ss_gui_07.dxf"
TOL = 0.75


def _close(a, b, tol=TOL):
    return abs(float(a) - float(b)) <= tol


def _point_close(a, b, tol=TOL):
    return _close(a[0], b[0], tol) and _close(a[1], b[1], tol)


def _circles(doc):
    out = []
    for entity in doc.modelspace():
        if entity.dxftype() == "CIRCLE":
            c = entity.dxf.center
            out.append(((float(c.x), float(c.y)), float(entity.dxf.radius)))
    return out


def _find_flange_center(circles):
    for center, radius in circles:
        if not _close(radius, 60):
            continue
        if any(_point_close(other_center, center) and _close(other_radius, 30) for other_center, other_radius in circles):
            return center
    return None


def _has_circle(circles, center, radius):
    return any(_point_close(c, center) and _close(r, radius) for c, r in circles)


def evaluate():
    path = OUTPUT_ROOT / TARGET
    if not path.exists() or path.stat().st_size <= 0:
        return False
    doc = ezdxf.readfile(path)
    circles = _circles(doc)
    center = _find_flange_center(circles)
    if center is None:
        return False
    for angle in [90, 150, 210, 270, 330, 30]:
        expected = (
            center[0] + 45 * math.cos(math.radians(angle)),
            center[1] + 45 * math.sin(math.radians(angle)),
        )
        if not _has_circle(circles, expected, 4):
            return False
    return True


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print("True" if ok else "False")
