from __future__ import annotations

from pathlib import Path

import cadquery as cq


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
TOL = 0.08


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


def dims(solid):
    bb = solid.BoundingBox()
    return (bb.xlen, bb.ylen, bb.zlen)


def close_tuple(actual, expected) -> bool:
    return all(abs(float(a) - float(e)) <= TOL for a, e in zip(actual, expected))


def find_by_dims(solids, expected_dims):
    matches = [solid for solid in solids if close_tuple(dims(solid), expected_dims)]
    if len(matches) != 1:
        raise ValueError(f"expected one solid with dims {expected_dims}")
    return matches[0]


def check_assembly() -> bool:
    solids = load_solids(OUTPUT_ROOT / "cli_024_scaled_assembly_out.step", 3)
    a = find_by_dims(solids, (60.0, 40.0, 20.0))
    b = find_by_dims(solids, (75.0, 50.0, 25.0))
    c = find_by_dims(solids, (55.0, 35.0, 18.0))
    return (
        close_tuple(bbox_tuple(a), (-30.0, 30.0, -20.0, 20.0, 0.0, 20.0))
        and close_tuple(bbox_tuple(b), (27.5, 102.5, -25.0, 25.0, 0.0, 25.0))
        and close_tuple(bbox_tuple(c), (117.5, 172.5, -17.5, 17.5, 0.0, 18.0))
        and abs(sum(s.Volume() for s in solids) - 176400.0) <= 80.0
    )


def check_part_file(name: str, expected_bbox, expected_volume: float) -> bool:
    solid = load_solids(OUTPUT_ROOT / name, 1)[0]
    return close_tuple(bbox_tuple(solid), expected_bbox) and abs(solid.Volume() - expected_volume) <= 60.0


def evaluate() -> bool:
    return (
        check_assembly()
        and check_part_file("cli_024_A.step", (-30.0, 30.0, -20.0, 20.0, -10.0, 10.0), 48000.0)
        and check_part_file("cli_024_B_scaled.step", (-37.5, 37.5, -25.0, 25.0, -12.5, 12.5), 93750.0)
        and check_part_file("cli_024_C.step", (-27.5, 27.5, -17.5, 17.5, -9.0, 9.0), 34650.0)
    )


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
