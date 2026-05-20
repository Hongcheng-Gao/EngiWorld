from __future__ import annotations

from pathlib import Path

import cadquery as cq
import sys

_TASK_V_ROOT = Path(__file__).resolve().parents[2]
if str(_TASK_V_ROOT) not in sys.path:
    sys.path.insert(0, str(_TASK_V_ROOT))
from _gui_bypass import check_no_gui_bypass



OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
OUTPUT_NAME = "gui_017_adapter_counterbore_out.step"
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
    actual = (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)
    expected = (-35.0, 35.0, -25.0, 25.0, -9.0, 9.0)
    return all(abs(a - e) <= TOL for a, e in zip(actual, expected))


def check_center_hole(solid) -> bool:
    empties = [(0, 0, z) for z in (-8, 0, 8)] + [(12.2, 0, 0), (-12.2, 0, 0)]
    solids = [(13.2, 0, 0), (-13.2, 0, 0), (0, 13.2, 0), (0, -13.2, 0)]
    return empty(solid, empties) and material(solid, solids)


def check_counterbore(solid, cx: float, cy: float) -> bool:
    through_empty = [
        (cx, cy, -8), (cx, cy, 0), (cx, cy, 8),
        (cx + 2.7, cy, -7), (cx - 2.7, cy, 2),
    ]
    through_material = [(cx + 3.6, cy, -4), (cx - 3.6, cy, 0)]
    counterbore_empty = [(cx + 5.7, cy, 8), (cx - 5.7, cy, 6), (cx, cy + 5.7, 8)]
    counterbore_material = [(cx + 6.6, cy, 8), (cx, cy + 6.6, 6), (cx + 5.0, cy, 3.5)]
    return (
        empty(solid, through_empty)
        and material(solid, through_material)
        and empty(solid, counterbore_empty)
        and material(solid, counterbore_material)
    )


def check_all_counterbores(solid) -> bool:
    return all(
        check_counterbore(solid, cx, cy)
        for cx in (-25.0, 25.0)
        for cy in (-15.0, 15.0)
    )


def check_top_outer_chamfer(solid) -> bool:
    # A 2 mm top chamfer removes the sharp top perimeter while leaving the top
    # face inset and the side wall below the chamfer intact.
    return (
        material(solid, [(32.0, 0, 8.8), (-32.0, 0, 8.8), (0, 22.0, 8.8), (0, -22.0, 8.8)])
        and empty(solid, [(34.5, 0, 8.8), (-34.5, 0, 8.8), (0, 24.5, 8.8), (0, -24.5, 8.8)])
        and material(solid, [(34.8, 0, 6.8), (-34.8, 0, 6.8), (0, 24.8, 6.8), (0, -24.8, 6.8)])
    )


def check_volume(solid) -> bool:
    return abs(solid.Volume() - 49962.7) / 49962.7 <= 0.02


def evaluate() -> bool:
    if not check_no_gui_bypass(Path(r"C:\Users\User\Desktop")):
        return False
    solid = load_single_solid(OUTPUT_ROOT / OUTPUT_NAME)
    return all([
        check_bbox(solid),
        check_center_hole(solid),
        check_all_counterbores(solid),
        check_top_outer_chamfer(solid),
        check_volume(solid),
    ])


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
