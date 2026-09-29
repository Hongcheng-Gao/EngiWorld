from __future__ import annotations

import re
from pathlib import Path

import cadquery as cq


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
STEP_NAME = "cli_021_stack_assembly_out.step"
TEXT_NAME = "cli_021_massprops.txt"
TOL = 0.08


def load_solids(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 3 or any(not solid.isValid() for solid in solids):
        raise ValueError("expected three valid independent solids")
    return solids


def bbox_tuple(solid):
    bb = solid.BoundingBox()
    return (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)


def dims(solid):
    bb = solid.BoundingBox()
    return (bb.xlen, bb.ylen, bb.zlen)


def center_xy(solid):
    bb = solid.BoundingBox()
    return ((bb.xmin + bb.xmax) / 2.0, (bb.ymin + bb.ymax) / 2.0)


def close_tuple(actual, expected, tol: float = TOL) -> bool:
    return all(abs(float(a) - float(e)) <= tol for a, e in zip(actual, expected))


def classify(solids):
    plates = []
    spacer = None
    for solid in solids:
        if close_tuple(dims(solid), (120.0, 80.0, 6.0)):
            plates.append(solid)
        elif close_tuple(dims(solid), (20.0, 20.0, 30.0)):
            spacer = solid
    if len(plates) != 2 or spacer is None:
        raise ValueError("part dimensions do not match instruction")
    plates.sort(key=lambda s: s.BoundingBox().zmin)
    return plates[0], spacer, plates[1]


def check_stack(solids) -> bool:
    base, spacer, top = classify(solids)
    return (
        close_tuple(center_xy(base), (0.0, 0.0))
        and close_tuple(center_xy(spacer), (0.0, 0.0))
        and close_tuple(center_xy(top), (0.0, 0.0))
        and close_tuple(bbox_tuple(base), (-60.0, 60.0, -40.0, 40.0, 0.0, 6.0))
        and close_tuple(bbox_tuple(spacer), (-10.0, 10.0, -10.0, 10.0, 6.0, 36.0))
        and close_tuple(bbox_tuple(top), (-60.0, 60.0, -40.0, 40.0, 36.0, 42.0))
    )


def check_massprops(path: Path) -> bool:
    if not path.exists() or path.stat().st_size <= 0:
        return False
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    if "volume" not in text and "mass" not in text:
        return False
    match = re.search(r"127200(?:\\.0+)?", text)
    return bool(match)


def evaluate() -> bool:
    solids = load_solids(OUTPUT_ROOT / STEP_NAME)
    total_volume = sum(solid.Volume() for solid in solids)
    return (
        check_stack(solids)
        and abs(total_volume - 127200.0) <= 80.0
        and check_massprops(OUTPUT_ROOT / TEXT_NAME)
    )


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
