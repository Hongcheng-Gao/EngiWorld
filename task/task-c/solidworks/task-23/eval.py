from __future__ import annotations

from pathlib import Path

import cadquery as cq


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
OUTPUT_NAME = "cli_023_cut_plate_out.step"
CENTERS = [(x, y) for x in (-60.0, -20.0, 20.0, 60.0) for y in (-30.0, 0.0, 30.0)]
TOL = 0.08


def load_single_solid(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 1 or not solids[0].isValid():
        raise ValueError("expected one valid solid after deleting cutter bodies")
    return solids[0]


def inside(solid, x: float, y: float, z: float) -> bool:
    return bool(solid.isInside(cq.Vector(x, y, z), 1e-5))


def check_bbox(solid) -> bool:
    bb = solid.BoundingBox()
    actual = (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)
    expected = (-80.0, 80.0, -50.0, 50.0, 0.0, 10.0)
    return all(abs(a - e) <= TOL for a, e in zip(actual, expected))


def check_holes(solid) -> bool:
    for cx, cy in CENTERS:
        if any(inside(solid, x, y, z) for x, y, z in [(cx, cy, 5), (cx + 2.3, cy, 5), (cx, cy + 2.3, 5)]):
            return False
        if not all(inside(solid, x, y, z) for x, y, z in [(cx + 3.0, cy, 5), (cx, cy + 3.0, 5)]):
            return False
    return True


def evaluate() -> bool:
    solid = load_single_solid(OUTPUT_ROOT / OUTPUT_NAME)
    return (
        check_bbox(solid)
        and check_holes(solid)
        and abs(solid.Volume() - 157643.8) <= 120.0
    )


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
