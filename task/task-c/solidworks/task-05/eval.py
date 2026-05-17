from __future__ import annotations

from pathlib import Path

import cadquery as cq


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
STEP_NAME = "cli_025_repaired_solid_out.step"
LOG_NAME = "cli_025_repair_log.txt"
TOL = 0.08


def load_single_solid(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 1 or not solids[0].isValid():
        raise ValueError("expected one valid closed solid")
    return solids[0]


def check_solid(solid) -> bool:
    bb = solid.BoundingBox()
    actual = (bb.xlen, bb.ylen, bb.zlen)
    return (
        all(abs(a - e) <= 0.2 for a, e in zip(actual, (80.0, 60.0, 40.0)))
        and abs(solid.Volume() - 192000.0) <= 200.0
    )


def check_log(path: Path) -> bool:
    if not path.exists() or path.stat().st_size <= 0:
        return False
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    required_any = [
        ("gap", "closed"),
        ("duplicate", "removed"),
        ("stitch", "solid"),
    ]
    return all(all(word in text for word in pair) for pair in required_any)


def evaluate() -> bool:
    solid = load_single_solid(OUTPUT_ROOT / STEP_NAME)
    return check_solid(solid) and check_log(OUTPUT_ROOT / LOG_NAME)


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
