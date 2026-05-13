from __future__ import annotations

from pathlib import Path

import cadquery as cq


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
OUTPUT_NAME = "cli_022_hole_transfer_out.step"
TOL = 0.08
REL_CENTERS = [(-40.0, -20.0), (0.0, -20.0), (40.0, -20.0),
               (-40.0, 20.0), (0.0, 20.0), (40.0, 20.0)]


def load_solids(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 2 or any(not solid.isValid() for solid in solids):
        raise ValueError("expected two valid independent solids")
    return solids


def inside(solid, x: float, y: float, z: float) -> bool:
    return bool(solid.isInside(cq.Vector(x, y, z), 1e-5))


def bbox_tuple(solid):
    bb = solid.BoundingBox()
    return (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)


def dims(solid):
    bb = solid.BoundingBox()
    return (bb.xlen, bb.ylen, bb.zlen)


def center_xy(solid):
    bb = solid.BoundingBox()
    return ((bb.xmin + bb.xmax) / 2.0, (bb.ymin + bb.ymax) / 2.0)


def close_tuple(actual, expected) -> bool:
    return all(abs(float(a) - float(e)) <= TOL for a, e in zip(actual, expected))


def classify(solids):
    source = target = None
    for solid in solids:
        if close_tuple(dims(solid), (120.0, 80.0, 8.0)):
            source = solid
        elif close_tuple(dims(solid), (140.0, 90.0, 8.0)):
            target = solid
    if source is None or target is None:
        raise ValueError("source and target plates not found")
    return source, target


def check_hole_pattern(solid, center, bbox_expected) -> bool:
    if not close_tuple(bbox_tuple(solid), bbox_expected):
        return False
    cx0, cy0 = center
    for rx, ry in REL_CENTERS:
        cx, cy = cx0 + rx, cy0 + ry
        if any(inside(solid, x, y, z) for x, y, z in [(cx, cy, 4), (cx + 2.7, cy, 4), (cx, cy + 2.7, 4)]):
            return False
        if not all(inside(solid, x, y, z) for x, y, z in [(cx + 3.5, cy, 4), (cx, cy + 3.5, 4)]):
            return False
    return True


def evaluate() -> bool:
    solids = load_solids(OUTPUT_ROOT / OUTPUT_NAME)
    source, target = classify(solids)
    return (
        check_hole_pattern(source, (0.0, 0.0), (-60.0, 60.0, -40.0, 40.0, 0.0, 8.0))
        and check_hole_pattern(target, (125.0, 0.0), (55.0, 195.0, -45.0, 45.0, 0.0, 8.0))
        and abs(sum(s.Volume() for s in solids) - 174885.7) <= 100.0
    )


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
