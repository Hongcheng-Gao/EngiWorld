from __future__ import annotations

import re
from pathlib import Path

import cadquery as cq


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
STEP_NAME = "cli_028_cleanup_out.step"
REPORT_NAME = "cli_028_cleanup_report.txt"
BIG = [(x, y) for x in (-60.0, -20.0, 20.0, 60.0) for y in (-35.0, 35.0)]
SMALL = [(x, y) for x in (-72.0, -36.0, 0.0, 36.0, 72.0) for y in (-10.0, 10.0)]
TOL = 0.08


def load_single_solid(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 1 or not solids[0].isValid():
        raise ValueError("expected one valid cleaned panel")
    return solids[0]


def inside(solid, x: float, y: float, z: float) -> bool:
    return bool(solid.isInside(cq.Vector(x, y, z), 1e-5))


def check_bbox(solid) -> bool:
    bb = solid.BoundingBox()
    actual = (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)
    expected = (-90.0, 90.0, -60.0, 60.0, 0.0, 6.0)
    return all(abs(a - e) <= TOL for a, e in zip(actual, expected))


def check_functional_holes(solid) -> bool:
    for cx, cy in BIG:
        if any(inside(solid, x, y, z) for x, y, z in [(cx, cy, 3), (cx + 3.7, cy, 3), (cx, cy + 3.7, 3)]):
            return False
        if not all(inside(solid, x, y, z) for x, y, z in [(cx + 4.6, cy, 3), (cx, cy + 4.6, 3)]):
            return False
    return True


def check_small_holes_filled(solid) -> bool:
    return all(inside(solid, cx, cy, 3) for cx, cy in SMALL)


def check_report(path: Path) -> bool:
    if not path.exists() or path.stat().st_size <= 0:
        return False
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    return bool(re.search(r"\b10\b", text) and "small" in text and ("removed" in text or "filled" in text))


def evaluate() -> bool:
    solid = load_single_solid(OUTPUT_ROOT / STEP_NAME)
    return (
        check_bbox(solid)
        and check_functional_holes(solid)
        and check_small_holes_filled(solid)
        and abs(solid.Volume() - 127187.3) <= 120.0
        and check_report(OUTPUT_ROOT / REPORT_NAME)
    )


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
