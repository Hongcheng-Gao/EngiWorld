from __future__ import annotations

import math
from pathlib import Path

import cadquery as cq


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
TOL = 0.10
FLAT_LEN = 40.0 + 2.0 * 35.0 + 2.0 * (math.pi / 2.0) * (2.0 + 0.5 * 2.0)


def load_solids(path: Path, expected_count: int):
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != expected_count or any(not solid.isValid() for solid in solids):
        raise ValueError("unexpected solid count")
    return solids


def bbox_tuple(solid):
    bb = solid.BoundingBox()
    return (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)


def close_tuple(actual, expected) -> bool:
    return all(abs(float(a) - float(e)) <= TOL for a, e in zip(actual, expected))


def inside(solid, x: float, y: float, z: float) -> bool:
    return bool(solid.isInside(cq.Vector(x, y, z), 1e-5))


def check_bent_original() -> bool:
    solid = load_solids(OUTPUT_ROOT / "cli_035_bent_original.step", 1)[0]
    return (
        close_tuple(bbox_tuple(solid), (-22.0, 22.0, -30.0, 30.0, 0.0, 37.0))
        and inside(solid, 0, 0, 1.0)
        and inside(solid, -21.0, 0, 20.0)
        and inside(solid, 21.0, 0, 20.0)
        and not inside(solid, 0, 0, 20.0)
    )


def check_flat_pattern() -> bool:
    solid = load_solids(OUTPUT_ROOT / "cli_035_flat_pattern_out.step", 1)[0]
    bb = solid.BoundingBox()
    return (
        abs(bb.xlen - FLAT_LEN) <= TOL
        and abs(bb.ylen - 60.0) <= TOL
        and abs(bb.zlen - 2.0) <= TOL
        and abs(solid.Volume() - (FLAT_LEN * 60.0 * 2.0)) <= 80.0
    )


def evaluate() -> bool:
    return check_bent_original() and check_flat_pattern()


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
