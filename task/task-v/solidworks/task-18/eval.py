from __future__ import annotations

import math
from pathlib import Path

import cadquery as cq
import sys

_TASK_V_ROOT = Path(__file__).resolve().parents[2]
if str(_TASK_V_ROOT) not in sys.path:
    sys.path.insert(0, str(_TASK_V_ROOT))
from _gui_bypass import check_no_gui_bypass



OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
OUTPUT_NAME = "gui_018_motor_mount_out.step"
TOL = 0.08


def load_single_solid(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 1 or not solids[0].isValid():
        raise ValueError("expected one valid solid")
    return solids[0]


def inside(solid, x: float, y: float, z: float) -> bool:
    return bool(solid.isInside(cq.Vector(x, y, z), 1e-5))


def material(solid, points) -> bool:
    return all(inside(solid, *point) for point in points)


def empty(solid, points) -> bool:
    return all(not inside(solid, *point) for point in points)


def check_bbox(solid) -> bool:
    bb = solid.BoundingBox()
    expected = (-50.0, 50.0, -40.0, 40.0, 0.0, 20.0)
    actual = (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)
    return all(abs(a - e) <= TOL for a, e in zip(actual, expected))


def check_base_and_boss(solid) -> bool:
    return (
        material(solid, [(-45, -35, 4), (45, 35, 4), (24.0, 0, 18), (-24.0, 0, 18)])
        and empty(solid, [(26.0, 0, 18), (-26.0, 0, 18), (0, 41, 4), (51, 0, 4)])
    )


def check_center_hole(solid) -> bool:
    return (
        empty(solid, [(0, 0, 2), (0, 0, 12), (10.6, 0, 12), (-10.6, 0, 12)])
        and material(solid, [(11.7, 0, 12), (-11.7, 0, 12), (0, 11.7, 12), (0, -11.7, 12)])
    )


def check_motor_hole(solid, cx: float, cy: float) -> bool:
    return (
        empty(solid, [(cx, cy, 4), (cx + 2.6, cy, 4), (cx - 2.6, cy, 4)])
        and material(solid, [(cx + 3.3, cy, 4), (cx - 3.3, cy, 4), (cx, cy + 3.3, 4)])
    )


def check_motor_holes(solid) -> bool:
    for deg in (45, 135, 225, 315):
        angle = math.radians(deg)
        if not check_motor_hole(solid, 32 * math.cos(angle), 32 * math.sin(angle)):
            return False
    return True


def check_slot(solid, cx: float) -> bool:
    return (
        empty(solid, [(cx, 0, 4), (cx, 11.6, 4), (cx, -11.6, 4), (cx + 3.6, 0, 4), (cx - 3.6, 0, 4)])
        and material(solid, [(cx, 12.8, 4), (cx, -12.8, 4), (cx + 4.7, 0, 4), (cx - 4.7, 0, 4)])
    )


def check_slots(solid) -> bool:
    return check_slot(solid, -35.0) and check_slot(solid, 35.0)


def check_volume(solid) -> bool:
    return abs(solid.Volume() - 76346.8) / 76346.8 <= 0.025


def evaluate() -> bool:
    if not check_no_gui_bypass(Path(r"C:\Users\User\Desktop")):
        return False
    solid = load_single_solid(OUTPUT_ROOT / OUTPUT_NAME)
    return all([
        check_bbox(solid),
        check_base_and_boss(solid),
        check_center_hole(solid),
        check_motor_holes(solid),
        check_slots(solid),
        check_volume(solid),
    ])


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
