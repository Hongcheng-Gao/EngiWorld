from __future__ import annotations

import math
from pathlib import Path

import cadquery as cq


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
OUTPUT_NAME = "cli_032_drafted_part_out.step"
TOL = 0.10
TOP_X = 80.0 + 2.0 * 35.0 * math.tan(math.radians(2.0))
TOP_Y = 50.0 + 2.0 * 35.0 * math.tan(math.radians(2.0))


def load_single_solid(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 1 or not solids[0].isValid():
        raise ValueError("expected one valid drafted box solid")
    return solids[0]


def inside(solid, x: float, y: float, z: float) -> bool:
    return bool(solid.isInside(cq.Vector(x, y, z), 1e-5))


def check_bbox(solid) -> bool:
    bb = solid.BoundingBox()
    return (
        abs(bb.xlen - TOP_X) <= TOL
        and abs(bb.ylen - TOP_Y) <= TOL
        and abs(bb.zlen - 35.0) <= TOL
        and abs(bb.zmin - 0.0) <= TOL
    )


def check_open_box_and_draft(solid) -> bool:
    return (
        # bottom is fixed at the original 80 x 50 size
        inside(solid, 39.8, 0, 1.5)
        and inside(solid, 0, 24.8, 1.5)
        and not inside(solid, 40.4, 0, 1.5)
        and not inside(solid, 0, 25.4, 1.5)
        # top extends outward by the 2 degree draft
        and inside(solid, 40.9, 0, 34.5)
        and inside(solid, 0, 25.9, 34.5)
        # the cavity remains open
        and not inside(solid, 0, 0, 20.0)
        and inside(solid, 0, 0, 1.5)
    )


def evaluate() -> bool:
    solid = load_single_solid(OUTPUT_ROOT / OUTPUT_NAME)
    return check_bbox(solid) and check_open_box_and_draft(solid) and abs(solid.Volume() - 41438.8) <= 150.0


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
