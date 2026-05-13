from __future__ import annotations

from pathlib import Path

import cadquery as cq


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
OUTPUT_NAME = "gui_020_two_part_aligned_out.step"
TOL = 0.08


def load_solids(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 2 or any(not solid.isValid() for solid in solids):
        raise ValueError("expected two valid independent solids")
    return solids


def dims(solid):
    bb = solid.BoundingBox()
    return (bb.xlen, bb.ylen, bb.zlen)


def center_xy(solid):
    bb = solid.BoundingBox()
    return ((bb.xmin + bb.xmax) / 2.0, (bb.ymin + bb.ymax) / 2.0)


def close_tuple(actual, expected, tol: float = TOL) -> bool:
    return all(abs(float(a) - float(e)) <= tol for a, e in zip(actual, expected))


def classify_solids(solids):
    base = None
    slide = None
    for solid in solids:
        d = dims(solid)
        if close_tuple(d, (100.0, 40.0, 10.0)):
            base = solid
        elif close_tuple(d, (30.0, 30.0, 12.0)):
            slide = solid
    if base is None or slide is None:
        raise ValueError("base and sliding block sizes not found")
    return base, slide


def check_alignment(base, slide) -> bool:
    base_bb = base.BoundingBox()
    slide_bb = slide.BoundingBox()
    return (
        close_tuple(center_xy(base), center_xy(slide))
        and abs(base_bb.zmax - slide_bb.zmin) <= TOL
        and close_tuple((base_bb.xmin, base_bb.xmax, base_bb.ymin, base_bb.ymax, base_bb.zmin, base_bb.zmax),
                       (-50.0, 50.0, -20.0, 20.0, 0.0, 10.0))
        and close_tuple((slide_bb.xmin, slide_bb.xmax, slide_bb.ymin, slide_bb.ymax, slide_bb.zmin, slide_bb.zmax),
                       (-15.0, 15.0, -15.0, 15.0, 10.0, 22.0))
    )


def evaluate() -> bool:
    solids = load_solids(OUTPUT_ROOT / OUTPUT_NAME)
    base, slide = classify_solids(solids)
    total_volume = sum(solid.Volume() for solid in solids)
    return check_alignment(base, slide) and abs(total_volume - 50800.0) <= 50.0


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
