from __future__ import annotations

import math
from pathlib import Path

import cadquery as cq


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
TOL = 0.08


VARIANTS = {
    "cli_029_variant_S.step": (4, 30.0, 6.0, 130981.9),
    "cli_029_variant_M.step": (6, 38.0, 6.0, 130529.6),
    "cli_029_variant_L.step": (8, 46.0, 8.0, 128669.7),
}


def load_single_solid(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 1 or not solids[0].isValid():
        raise ValueError("expected one valid variant solid")
    return solids[0]


def inside(solid, x: float, y: float, z: float) -> bool:
    return bool(solid.isInside(cq.Vector(x, y, z), 1e-5))


def check_bbox_and_center_hole(solid) -> bool:
    bb = solid.BoundingBox()
    actual = (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)
    expected = (-70.0, 70.0, -60.0, 60.0, 0.0, 8.0)
    return (
        all(abs(a - e) <= TOL for a, e in zip(actual, expected))
        and all(not inside(solid, x, y, 4.0) for x, y in [(0, 0), (9.5, 0), (0, 9.5)])
        and all(inside(solid, x, y, 4.0) for x, y in [(10.8, 0), (0, 10.8)])
    )


def check_bolt_pattern(solid, count: int, radius: float, diameter: float) -> bool:
    hole_r = diameter / 2.0
    for i in range(count):
        angle = 2.0 * math.pi * i / count
        cx, cy = radius * math.cos(angle), radius * math.sin(angle)
        if any(inside(solid, x, y, 4.0) for x, y in [(cx, cy), (cx + hole_r - 0.3, cy), (cx, cy + hole_r - 0.3)]):
            return False
        if not all(inside(solid, x, y, 4.0) for x, y in [(cx + hole_r + 0.7, cy), (cx, cy + hole_r + 0.7)]):
            return False
    return True


def check_variant(name: str, count: int, radius: float, diameter: float, volume: float) -> bool:
    solid = load_single_solid(OUTPUT_ROOT / name)
    return (
        check_bbox_and_center_hole(solid)
        and check_bolt_pattern(solid, count, radius, diameter)
        and abs(solid.Volume() - volume) <= 120.0
    )


def evaluate() -> bool:
    return all(check_variant(name, *spec) for name, spec in VARIANTS.items())


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
