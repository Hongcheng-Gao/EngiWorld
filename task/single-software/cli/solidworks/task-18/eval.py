from __future__ import annotations

from pathlib import Path

import cadquery as cq


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
OUTPUT_NAME = "cli_038_normalized_layout_out.step"
CENTERS = [(x, y) for y in (0.0, 90.0) for x in (0.0, 120.0, 240.0, 360.0)]
TOL = 0.08


def load_solids(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 8 or any(not s.isValid() for s in solids):
        raise ValueError("expected eight normalized brackets")
    return solids


def bbox_tuple(solid):
    bb = solid.BoundingBox()
    return (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)


def close_tuple(actual, expected) -> bool:
    return all(abs(float(a) - float(e)) <= TOL for a, e in zip(actual, expected))


def inside(solid, x: float, y: float, z: float) -> bool:
    return bool(solid.isInside(cq.Vector(x, y, z), 1e-5))


def check_bracket_at(solid, cx: float, cy: float) -> bool:
    expected_bbox = (cx - 25.0, cx + 25.0, cy - 15.0, cy + 15.0, 0.0, 20.0)
    return (
        close_tuple(bbox_tuple(solid), expected_bbox)
        and inside(solid, cx, cy, 4.0)
        and inside(solid, cx + 20.0, cy, 14.0)
        and not inside(solid, cx - 20.0, cy, 14.0)
        and abs(solid.Volume() - 14400.0) <= 50.0
    )


def evaluate() -> bool:
    unmatched = load_solids(OUTPUT_ROOT / OUTPUT_NAME)
    for cx, cy in CENTERS:
        match = None
        for solid in unmatched:
            if close_tuple(bbox_tuple(solid), (cx - 25, cx + 25, cy - 15, cy + 15, 0, 20)):
                match = solid
                break
        if match is None or not check_bracket_at(match, cx, cy):
            return False
        unmatched.remove(match)
    return True


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
