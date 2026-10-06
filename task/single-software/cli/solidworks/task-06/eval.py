from __future__ import annotations

import re
from pathlib import Path

import cadquery as cq


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
STEP_NAME = "cli_026_clearance_fixed_out.step"
REPORT_NAME = "cli_026_interference_report.txt"
TOL = 0.08


def load_solids(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 2 or any(not solid.isValid() for solid in solids):
        raise ValueError("expected housing and sliding_pin solids")
    return solids


def bbox_tuple(solid):
    bb = solid.BoundingBox()
    return (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)


def dims(solid):
    bb = solid.BoundingBox()
    return (bb.xlen, bb.ylen, bb.zlen)


def close_tuple(actual, expected) -> bool:
    return all(abs(float(a) - float(e)) <= TOL for a, e in zip(actual, expected))


def classify(solids):
    housing = pin = None
    for solid in solids:
        d = dims(solid)
        if close_tuple(d, (60.0, 60.0, 35.0)):
            housing = solid
        elif close_tuple(d, (40.0, 18.0, 18.0)):
            pin = solid
    if housing is None or pin is None:
        raise ValueError("part sizes changed or parts missing")
    return housing, pin


def inside(solid, x: float, y: float, z: float) -> bool:
    return bool(solid.isInside(cq.Vector(x, y, z), 1e-5))


def check_housing_bore(housing) -> bool:
    return (
        not inside(housing, -5.0, 0.0, 0.0)
        and inside(housing, -12.0, 0.0, 0.0)
        and inside(housing, -5.0, 10.8, 0.0)
        and inside(housing, -5.0, 0.0, 10.8)
    )


def check_pin_position(pin) -> bool:
    return close_tuple(bbox_tuple(pin), (-9.5, 30.5, -9.0, 9.0, -9.0, 9.0))


def check_report(path: Path) -> bool:
    if not path.exists() or path.stat().st_size <= 0:
        return False
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    has_zero_interference = "zero interference" in text or re.search(r"interference\s*=\s*0", text)
    has_clearance = "0.5" in text and "clearance" in text
    return bool(has_zero_interference and has_clearance)


def evaluate() -> bool:
    housing, pin = classify(load_solids(OUTPUT_ROOT / STEP_NAME))
    return (
        check_housing_bore(housing)
        and check_pin_position(pin)
        and abs(housing.Volume() - 113433.6) <= 120.0
        and abs(pin.Volume() - 10178.8) <= 50.0
        and check_report(OUTPUT_ROOT / REPORT_NAME)
    )


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
