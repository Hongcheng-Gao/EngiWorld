from __future__ import annotations

from pathlib import Path

import cadquery as cq


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
OUTPUT_NAME = "cli_031_ribbed_enclosure_out.step"
TOL = 0.08


def load_single_solid(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 1 or not solids[0].isValid():
        raise ValueError("expected one merged enclosure solid")
    return solids[0]


def inside(solid, x: float, y: float, z: float) -> bool:
    return bool(solid.isInside(cq.Vector(x, y, z), 1e-5))


def check_bbox_and_shell(solid) -> bool:
    bb = solid.BoundingBox()
    actual = (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)
    expected = (-55.0, 55.0, -37.5, 37.5, 0.0, 22.0)
    return (
        all(abs(a - e) <= TOL for a, e in zip(actual, expected))
        and inside(solid, 0, 0, 1.5)
        and not inside(solid, 0, 0, 15.0)
        and inside(solid, 53.5, 0, 10.0)
        and inside(solid, 0, 36.0, 10.0)
    )


def check_ribs(solid) -> bool:
    for y in (-18.0, 0.0, 18.0):
        if not all(inside(solid, x, y, z) for x, z in [(-47.0, 6.0), (0.0, 8.8), (47.0, 6.0)]):
            return False
        if inside(solid, 49.5, y, 6.0) or inside(solid, -49.5, y, 6.0):
            return False
    for x in (-18.0, 18.0):
        if not all(inside(solid, x, y, z) for y, z in [(-29.5, 6.0), (0.0, 8.8), (29.5, 6.0)]):
            return False
        if inside(solid, x, 32.0, 6.0) or inside(solid, x, -32.0, 6.0):
            return False
    return True


def evaluate() -> bool:
    solid = load_single_solid(OUTPUT_ROOT / OUTPUT_NAME)
    return (
        check_bbox_and_shell(solid)
        and check_ribs(solid)
        and abs(solid.Volume() - 51081.0) <= 120.0
    )


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
