from __future__ import annotations

from pathlib import Path

import cadquery as cq
import sys

_TASK_V_ROOT = Path(__file__).resolve().parents[2]
if str(_TASK_V_ROOT) not in sys.path:
    sys.path.insert(0, str(_TASK_V_ROOT))
from _gui_bypass import check_no_gui_bypass



OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
OUTPUT_NAME = "gui_019_cover_boss_ribs_out.step"
TOL = 0.08
BOSSES = [(-40.0, -25.0), (-40.0, 25.0), (40.0, -25.0), (40.0, 25.0)]


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
    expected = (-60.0, 60.0, -45.0, 45.0, 0.0, 15.0)
    return all(abs(a - e) <= TOL for a, e in zip(actual, expected))


def check_rounded_cover(solid) -> bool:
    return (
        material(solid, [(0, 0, 2), (52, 0, 2), (0, 37, 2), (-52, 0, 2), (0, -37, 2)])
        and empty(solid, [(58.5, 43.5, 2), (-58.5, 43.5, 2), (58.5, -43.5, 2), (-58.5, -43.5, 2)])
    )


def check_boss_and_hole(solid, cx: float, cy: float) -> bool:
    return (
        material(solid, [(cx + 4.6, cy, 14), (cx - 4.6, cy, 14), (cx, cy + 4.6, 14)])
        and empty(solid, [(cx + 5.7, cy, 14), (cx, cy + 5.7, 14)])
        and empty(solid, [(cx, cy, 2), (cx, cy, 10), (cx + 1.55, cy, 10)])
        and material(solid, [(cx + 2.2, cy, 10), (cx, cy + 2.2, 2)])
    )


def check_bosses_and_holes(solid) -> bool:
    return all(check_boss_and_hole(solid, cx, cy) for cx, cy in BOSSES)


def check_ribs(solid) -> bool:
    rib_material = [
        (0, 25, 8), (0, -25, 8), (40, 0, 8), (-40, 0, 8),
        (35, 25, 8), (-35, 25, 8), (40, 20, 8), (-40, -20, 8),
    ]
    rib_empty = [
        (0, 25, 12), (0, -25, 12), (40, 0, 12), (-40, 0, 12),
        (0, 28, 8), (0, 22, 8), (43, 0, 8), (37, 0, 8),
    ]
    return material(solid, rib_material) and empty(solid, rib_empty)


def check_volume(solid) -> bool:
    return abs(solid.Volume() - 61628.4) / 61628.4 <= 0.025


def evaluate() -> bool:
    if not check_no_gui_bypass(Path(r"C:\Users\User\Desktop")):
        return False
    solid = load_single_solid(OUTPUT_ROOT / OUTPUT_NAME)
    return all([
        check_bbox(solid),
        check_rounded_cover(solid),
        check_bosses_and_holes(solid),
        check_ribs(solid),
        check_volume(solid),
    ])


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
