from __future__ import annotations

from pathlib import Path

import cadquery as cq


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
TOL = 0.08


RIGHT_BBOX = (20.0, 75.0, -15.0, 15.0, 0.0, 20.0)
LEFT_BBOX = (-75.0, -20.0, -15.0, 15.0, 0.0, 20.0)


def load_solids(path: Path, expected_count: int):
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != expected_count or any(not solid.isValid() for solid in solids):
        raise ValueError("invalid solid count")
    return solids


def bbox_tuple(solid):
    bb = solid.BoundingBox()
    return (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)


def close_tuple(actual, expected) -> bool:
    return all(abs(float(a) - float(e)) <= TOL for a, e in zip(actual, expected))


def inside(solid, x: float, y: float, z: float) -> bool:
    return bool(solid.isInside(cq.Vector(x, y, z), 1e-5))


def check_right_shape(solid) -> bool:
    return (
        close_tuple(bbox_tuple(solid), RIGHT_BBOX)
        and inside(solid, 30, 0, 5)
        and inside(solid, 65, 0, 15)
        and not inside(solid, 30, 0, 15)
        and abs(solid.Volume() - 20500.0) <= 50.0
    )


def check_left_shape(solid) -> bool:
    return (
        close_tuple(bbox_tuple(solid), LEFT_BBOX)
        and inside(solid, -30, 0, 5)
        and inside(solid, -65, 0, 15)
        and not inside(solid, -30, 0, 15)
        and abs(solid.Volume() - 20500.0) <= 50.0
    )


def check_assembly() -> bool:
    solids = load_solids(OUTPUT_ROOT / "cli_033_pair_assembly.step", 2)
    left = right = None
    for solid in solids:
        if close_tuple(bbox_tuple(solid), LEFT_BBOX):
            left = solid
        elif close_tuple(bbox_tuple(solid), RIGHT_BBOX):
            right = solid
    if left is None or right is None:
        return False
    gap = right.BoundingBox().xmin - left.BoundingBox().xmax
    return gap >= 20.0 - TOL and check_left_shape(left) and check_right_shape(right)


def evaluate() -> bool:
    right = load_solids(OUTPUT_ROOT / "cli_033_right_original.step", 1)[0]
    left = load_solids(OUTPUT_ROOT / "cli_033_left_mirrored.step", 1)[0]
    return check_right_shape(right) and check_left_shape(left) and check_assembly()


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
