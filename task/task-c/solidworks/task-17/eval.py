from __future__ import annotations

from pathlib import Path

import cadquery as cq


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
OUTPUT_NAME = "cli_037_replaced_motor_out.step"
TOL = 0.08
HOLES = [(25.0, -20.0), (25.0, 20.0), (55.0, -20.0), (55.0, 20.0)]


def load_solids(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 3 or any(not s.isValid() for s in solids):
        raise ValueError("expected frame, new_motor, and coupler")
    return solids


def bbox_tuple(solid):
    bb = solid.BoundingBox()
    return (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)


def dims(solid):
    bb = solid.BoundingBox()
    return (bb.xlen, bb.ylen, bb.zlen)


def close_tuple(actual, expected) -> bool:
    return all(abs(float(a) - float(e)) <= TOL for a, e in zip(actual, expected))


def inside(solid, x: float, y: float, z: float) -> bool:
    return bool(solid.isInside(cq.Vector(x, y, z), 1e-5))


def classify(solids):
    frame = motor = coupler = None
    for solid in solids:
        if close_tuple(bbox_tuple(solid), (-30.0, 70.0, -35.0, 35.0, 0.0, 8.0)):
            frame = solid
        elif close_tuple(bbox_tuple(solid), (10.0, 85.0, -22.5, 22.5, 8.0, 48.0)):
            motor = solid
        elif close_tuple(bbox_tuple(solid), (85.0, 115.0, -9.0, 9.0, 21.0, 39.0)):
            coupler = solid
    if frame is None or motor is None or coupler is None:
        raise ValueError("replacement assembly parts not found")
    return frame, motor, coupler


def check_mounting_holes(frame, motor) -> bool:
    for cx, cy in HOLES:
        if inside(frame, cx, cy, 4.0) or inside(motor, cx, cy, 12.0):
            return False
        if not inside(frame, cx + 3.6, cy, 4.0):
            return False
    return True


def check_axis_alignment(motor, coupler) -> bool:
    return (
        inside(motor, 75.0, 0.0, 30.0)
        and inside(motor, 75.0, 4.7, 30.0)
        and not inside(motor, 75.0, 5.8, 30.0)
        and inside(coupler, 100.0, 0.0, 30.0)
        and inside(coupler, 100.0, 8.5, 30.0)
        and not inside(coupler, 100.0, 9.8, 30.0)
        and abs(motor.BoundingBox().xmax - coupler.BoundingBox().xmin) <= TOL
    )


def evaluate() -> bool:
    frame, motor, coupler = classify(load_solids(OUTPUT_ROOT / OUTPUT_NAME))
    return (
        check_mounting_holes(frame, motor)
        and check_axis_alignment(motor, coupler)
        and abs(frame.Volume() - 55095.2) <= 80.0
        and abs(motor.Volume() - 104834.3) <= 120.0
        and abs(coupler.Volume() - 7634.1) <= 50.0
    )


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
