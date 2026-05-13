from __future__ import annotations

from pathlib import Path

import cadquery as cq


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
TOL = 0.08


ASSEMBLY_BBOXES = [
    (-35.0, 35.0, -22.5, 22.5, 0.0, 12.0),
    (55.0, 95.0, -12.5, 12.5, 0.0, 8.0),
    (100.0, 140.0, -12.5, 12.5, 0.0, 8.0),
    (161.0, 169.0, -4.0, 4.0, 0.0, 40.0),
    (169.0, 187.0, -9.0, 9.0, 0.0, 4.0),
]
PART_SPECS = {
    "cli_030_base.step": ((-35.0, 35.0, -22.5, 22.5, -6.0, 6.0), 37800.0),
    "cli_030_left_cover.step": ((-20.0, 20.0, -12.5, 12.5, -4.0, 4.0), 8000.0),
    "cli_030_right_cover.step": ((-20.0, 20.0, -12.5, 12.5, -4.0, 4.0), 8000.0),
    "cli_030_pin.step": ((-4.0, 4.0, -4.0, 4.0, -20.0, 20.0), 2010.6),
    "cli_030_washer.step": ((-9.0, 9.0, -9.0, 9.0, -2.0, 2.0), 816.8),
}


def load_solids(path: Path, expected_count: int):
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != expected_count or any(not solid.isValid() for solid in solids):
        raise ValueError(f"expected {expected_count} valid solid(s)")
    return solids


def bbox_tuple(solid):
    bb = solid.BoundingBox()
    return (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)


def close_tuple(actual, expected) -> bool:
    return all(abs(float(a) - float(e)) <= TOL for a, e in zip(actual, expected))


def bbox_matches_any(actual, expected_list) -> bool:
    return any(close_tuple(actual, expected) for expected in expected_list)


def check_full_assembly() -> bool:
    solids = load_solids(OUTPUT_ROOT / "cli_030_full_assembly_out.step", 5)
    bboxes = [bbox_tuple(s) for s in solids]
    return (
        all(bbox_matches_any(expected, bboxes) for expected in ASSEMBLY_BBOXES)
        and abs(sum(s.Volume() for s in solids) - 56627.4) <= 80.0
    )


def check_part_file(name: str, expected_bbox, expected_volume: float) -> bool:
    solid = load_solids(OUTPUT_ROOT / name, 1)[0]
    return close_tuple(bbox_tuple(solid), expected_bbox) and abs(solid.Volume() - expected_volume) <= 50.0


def evaluate() -> bool:
    return check_full_assembly() and all(
        check_part_file(name, bbox, volume)
        for name, (bbox, volume) in PART_SPECS.items()
    )


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
