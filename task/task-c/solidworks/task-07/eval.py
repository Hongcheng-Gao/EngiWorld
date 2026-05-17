from __future__ import annotations

import re
from pathlib import Path

import cadquery as cq


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
STEP_NAME = "cli_027_mass_reduced_out.step"
TEXT_NAME = "cli_027_massprops.txt"
HOLES = [(-30.0, -20.0), (30.0, -20.0), (-30.0, 20.0), (30.0, 20.0)]
TOL = 0.08
DENSITY_G_CM3 = 2.70


def load_single_solid(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 1 or not solids[0].isValid():
        raise ValueError("expected one valid bracket solid")
    return solids[0]


def inside(solid, x: float, y: float, z: float) -> bool:
    return bool(solid.isInside(cq.Vector(x, y, z), 1e-5))


def check_bbox(solid) -> bool:
    bb = solid.BoundingBox()
    actual = (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)
    expected = (-50.0, 50.0, -30.0, 30.0, 0.0, 40.0)
    return all(abs(a - e) <= TOL for a, e in zip(actual, expected))


def check_holes_and_rib(solid) -> bool:
    for cx, cy in HOLES:
        if any(inside(solid, x, y, z) for x, y, z in [(cx, cy, 4), (cx + 2.7, cy, 4), (cx, cy + 2.7, 4)]):
            return False
        if not all(inside(solid, x, y, z) for x, y, z in [(cx + 3.5, cy, 4), (cx, cy + 3.5, 4)]):
            return False
    # The centered rib must remain intact and uncut.
    return all(inside(solid, x, y, z) for x, y, z in [(-45, 0, 20), (0, 0, 35), (45, 0, 20)])


def mass_g(volume_mm3: float) -> float:
    return volume_mm3 / 1000.0 * DENSITY_G_CM3


def check_massprops(path: Path, volume: float) -> bool:
    if not path.exists() or path.stat().st_size <= 0:
        return False
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    numbers = [float(value) for value in re.findall(r"\d+(?:\.\d+)?", text)]
    has_volume = any(abs(value - volume) <= 5.0 for value in numbers)
    has_mass = any(abs(value - mass_g(volume)) <= 0.2 for value in numbers)
    return "mass" in text and "volume" in text and has_volume and has_mass


def evaluate() -> bool:
    solid = load_single_solid(OUTPUT_ROOT / STEP_NAME)
    volume = solid.Volume()
    return (
        check_bbox(solid)
        and check_holes_and_rib(solid)
        and 178.0 <= mass_g(volume) <= 182.0
        and check_massprops(OUTPUT_ROOT / TEXT_NAME, volume)
    )


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
