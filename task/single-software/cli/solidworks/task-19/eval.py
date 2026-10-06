from __future__ import annotations

from pathlib import Path

import cadquery as cq


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
OUTPUT_NAME = "cli_039_threaded_insert_out.step"
TOL = 0.08


def load_single_solid(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 1 or not solids[0].isValid():
        raise ValueError("expected one threaded insert solid")
    return solids[0]


def inside(solid, x: float, y: float, z: float) -> bool:
    return bool(solid.isInside(cq.Vector(x, y, z), 1e-5))


def check_bbox_and_bore(solid) -> bool:
    bb = solid.BoundingBox()
    return (
        abs(bb.xlen - 16.0) <= TOL
        and abs(bb.ylen - 16.0) <= TOL
        and abs(bb.zlen - 24.0) <= TOL
        and abs(bb.zmin - 0.0) <= TOL
        and all(not inside(solid, 0, 0, z) for z in (1.0, 12.0, 23.0))
        and all(inside(solid, 3.4, 0, z) for z in (1.0, 12.0, 23.0))
    )


def check_lead_ins(solid) -> bool:
    return (
        inside(solid, 7.8, 0, 1.5)
        and inside(solid, 7.8, 0, 22.5)
        and not inside(solid, 8.3, 0, 1.5)
        and not inside(solid, 8.3, 0, 22.5)
    )


def check_thread_bands(solid) -> bool:
    # Crest bands are full OD16 and root gaps are root OD14.4 over the middle 18 mm.
    for z in (3.5, 5.5, 7.5, 9.5, 11.5, 13.5, 15.5, 17.5, 19.5):
        if not inside(solid, 7.8, 0, z):
            return False
    for z in (4.5, 6.5, 8.5, 10.5, 12.5, 14.5, 16.5, 18.5, 20.5):
        if inside(solid, 7.5, 0, z) or not inside(solid, 7.0, 0, z):
            return False
    return True


def evaluate() -> bool:
    solid = load_single_solid(OUTPUT_ROOT / OUTPUT_NAME)
    return (
        check_bbox_and_bore(solid)
        and check_lead_ins(solid)
        and check_thread_bands(solid)
        and abs(solid.Volume() - 3803.1) <= 80.0
    )


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
