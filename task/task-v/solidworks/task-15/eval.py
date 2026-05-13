from __future__ import annotations

import math
from pathlib import Path

import cadquery as cq


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
OUTPUT_STEP = "gui_015_gear_lightened_out.step"

BBOX_TOL = 0.15
VOLUME_REL_TOL = 0.03
EXPECTED_VOLUME = 42351.769173


def close(actual: float, expected: float, tol: float) -> bool:
    return abs(float(actual) - float(expected)) <= tol


def import_single_solid(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        return None
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 1 or any(not solid.isValid() for solid in solids):
        return None
    return solids[0]


def bbox_matches(solid) -> bool:
    bbox = solid.BoundingBox()
    return (
        close(bbox.xmin, -40.0, BBOX_TOL)
        and close(bbox.xmax, 40.0, BBOX_TOL)
        and close(bbox.ymin, -40.0, BBOX_TOL)
        and close(bbox.ymax, 40.0, BBOX_TOL)
        and close(bbox.zmin, -5.0, BBOX_TOL)
        and close(bbox.zmax, 5.0, BBOX_TOL)
    )


def material_at(solid, radius: float, angle_degrees: float) -> bool:
    x = radius * math.cos(math.radians(angle_degrees))
    y = radius * math.sin(math.radians(angle_degrees))
    return solid.isInside((x, y, 0.0), 1e-6)


def holes_and_windows_match(solid) -> bool:
    if solid.isInside((0.0, 0.0, 0.0), 1e-6):
        return False
    for angle in range(0, 360, 60):
        if material_at(solid, 27.0, angle):
            return False
        if not material_at(solid, 20.0, angle):
            return False
        if not material_at(solid, 34.0, angle):
            return False
    for angle in range(30, 390, 60):
        if not material_at(solid, 27.0, angle):
            return False
    return True


def volume_matches(solid) -> bool:
    return abs(solid.Volume() - EXPECTED_VOLUME) / EXPECTED_VOLUME <= VOLUME_REL_TOL


def evaluate() -> bool:
    solid = import_single_solid(OUTPUT_ROOT / OUTPUT_STEP)
    if solid is None:
        return False
    return bbox_matches(solid) and holes_and_windows_match(solid) and volume_matches(solid)


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print(True if ok else False)
