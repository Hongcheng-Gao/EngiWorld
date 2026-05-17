from __future__ import annotations

from pathlib import Path

import cadquery as cq


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
OUTPUT_NAME = "cli_034_pins_inserted_out.step"
CENTERS = [(x, y) for x in (-40.0, -20.0, 0.0, 20.0, 40.0) for y in (-20.0, 20.0)]
TOL = 0.08


def load_solids(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 11 or any(not s.isValid() for s in solids):
        raise ValueError("expected fixture plus ten pins")
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
    fixture = None
    pins = []
    for solid in solids:
        if close_tuple(dims(solid), (100.0, 70.0, 8.0)):
            fixture = solid
        elif close_tuple(dims(solid), (4.0, 4.0, 20.0)):
            pins.append(solid)
    if fixture is None or len(pins) != 10:
        raise ValueError("fixture or pins missing")
    return fixture, pins


def check_fixture(fixture) -> bool:
    if not close_tuple(bbox_tuple(fixture), (-50.0, 50.0, -35.0, 35.0, 0.0, 8.0)):
        return False
    for cx, cy in CENTERS:
        if inside(fixture, cx, cy, 6.0):
            return False
        if not inside(fixture, cx, cy, 3.5):
            return False
    return True


def check_pins(pins) -> bool:
    expected = [((cx - 2.0, cx + 2.0, cy - 2.0, cy + 2.0, 4.0, 24.0), (cx, cy)) for cx, cy in CENTERS]
    unmatched = list(pins)
    for bbox, _center in expected:
        match = None
        for pin in unmatched:
            if close_tuple(bbox_tuple(pin), bbox):
                match = pin
                break
        if match is None:
            return False
        unmatched.remove(match)
    return True


def evaluate() -> bool:
    fixture, pins = classify(load_solids(OUTPUT_ROOT / OUTPUT_NAME))
    return (
        check_fixture(fixture)
        and check_pins(pins)
        and abs(fixture.Volume() - 55445.8) <= 100.0
        and abs(sum(pin.Volume() for pin in pins) - 2513.3) <= 80.0
    )


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
