from __future__ import annotations

from pathlib import Path

import cadquery as cq
import sys

_TASK_V_ROOT = Path(__file__).resolve().parents[2]
if str(_TASK_V_ROOT) not in sys.path:
    sys.path.insert(0, str(_TASK_V_ROOT))
from _gui_bypass import check_no_gui_bypass



OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
OUTPUT_NAME = "gui_016_frame_corner_gusset_out.step"
TOL = 0.08


def load_single_solid(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 1 or not solids[0].isValid():
        raise ValueError("expected one valid solid")
    return solids[0]


def close(a: float, b: float, tol: float = TOL) -> bool:
    return abs(float(a) - float(b)) <= tol


def check_bbox(solid) -> bool:
    bb = solid.BoundingBox()
    expected = (0.0, 120.0, 0.0, 120.0, 0.0, 30.0)
    actual = (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)
    return all(close(a, e) for a, e in zip(actual, expected))


def inside(solid, x: float, y: float, z: float) -> bool:
    return bool(solid.isInside(cq.Vector(x, y, z), 1e-5))


def all_material(solid, points) -> bool:
    return all(inside(solid, *point) for point in points)


def all_empty(solid, points) -> bool:
    return all(not inside(solid, *point) for point in points)


def check_square_tube_frame(solid) -> bool:
    wall_points = [
        (60, 1.5, 15), (60, 28.5, 15), (60, 15, 1.5), (60, 15, 28.5),
        (1.5, 60, 15), (28.5, 60, 15), (15, 60, 1.5), (15, 60, 28.5),
        (10, 10, 1.5), (10, 10, 28.5),
    ]
    void_points = [
        (60, 15, 15), (15, 60, 15), (116, 15, 15), (15, 116, 15),
        (90, 90, 15), (110, 40, 15), (40, 110, 15),
    ]
    return all_material(solid, wall_points) and all_empty(solid, void_points)


def check_gusset(solid) -> bool:
    gusset_material = [
        (40, 40, 12.5), (40, 40, 17.5),
        (55, 35, 15), (35, 55, 15),
        (70, 35, 15), (35, 70, 15),
    ]
    gusset_empty = [
        (40, 40, 11.2), (40, 40, 18.8),
        (70, 70, 15), (87, 31, 15), (31, 87, 15),
    ]
    return all_material(solid, gusset_material) and all_empty(solid, gusset_empty)


def check_vertical_hole(solid, cx: float, cy: float, outside_axis: str) -> bool:
    for z in (1.5, 28.5):
        if not all_empty(solid, [(cx, cy, z), (cx + 3.6, cy, z), (cx - 3.6, cy, z)]):
            return False
        if outside_axis == "x":
            material_points = [(cx + 4.5, cy, z), (cx - 4.5, cy, z)]
        else:
            material_points = [(cx, cy + 4.5, z), (cx, cy - 4.5, z)]
        if not all_material(solid, material_points):
            return False
    return True


def check_fixing_holes(solid) -> bool:
    x_tube = [(100, 7), (100, 23)]
    y_tube = [(7, 100), (23, 100)]
    return (
        all(check_vertical_hole(solid, cx, cy, "x") for cx, cy in x_tube)
        and all(check_vertical_hole(solid, cx, cy, "y") for cx, cy in y_tube)
    )


def check_volume(solid) -> bool:
    return abs(solid.Volume() - 72452.6) / 72452.6 <= 0.025


def evaluate() -> bool:
    if not check_no_gui_bypass(Path(r"C:\Users\User\Desktop")):
        return False
    solid = load_single_solid(OUTPUT_ROOT / OUTPUT_NAME)
    return all([
        check_bbox(solid),
        check_square_tube_frame(solid),
        check_gusset(solid),
        check_fixing_holes(solid),
        check_volume(solid),
    ])


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
