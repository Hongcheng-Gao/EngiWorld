from __future__ import annotations

from pathlib import Path

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane
import sys

_TASK_V_ROOT = Path(__file__).resolve().parents[2]
if str(_TASK_V_ROOT) not in sys.path:
    sys.path.insert(0, str(_TASK_V_ROOT))
from _gui_bypass import check_no_gui_bypass



OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
OUTPUT_STEP = "gui_001_mounting_plate_out.step"

BBOX_TOL = 0.10
POS_TOL = 0.20
RADIUS_TOL = 0.10
VOLUME_REL_TOL = 0.02

EXPECTED_HOLES = [(45.0, 25.0), (45.0, -25.0), (-45.0, 25.0), (-45.0, -25.0)]
EXPECTED_VOLUME = 92410.714035


def close(actual: float, expected: float, tol: float) -> bool:
    return abs(float(actual) - float(expected)) <= tol


def import_single_solid(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        return None
    workplane = cq.importers.importStep(str(path))
    solids = workplane.solids().vals()
    if len(solids) != 1 or any(not solid.isValid() for solid in solids):
        return None
    return solids[0]


def bbox_matches(solid) -> bool:
    bbox = solid.BoundingBox()
    expected = {
        "xmin": -60.0,
        "xmax": 60.0,
        "ymin": -40.0,
        "ymax": 40.0,
        "zmin": -5.0,
        "zmax": 5.0,
    }
    return all(close(getattr(bbox, key), value, BBOX_TOL) for key, value in expected.items())


def cylinder_faces(solid):
    faces = []
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() == GeomAbs_Cylinder:
            cylinder = surface.Cylinder()
            axis = cylinder.Axis().Direction()
            faces.append((face, cylinder.Radius(), axis))
    return faces


def through_holes_match(solid) -> bool:
    candidates = []
    for face, radius, axis in cylinder_faces(solid):
        if not close(radius, 4.0, RADIUS_TOL):
            continue
        if abs(abs(axis.Z()) - 1.0) > 0.01:
            continue
        bbox = face.BoundingBox()
        if not close(bbox.zlen, 10.0, BBOX_TOL):
            continue
        center = face.Center()
        candidates.append((center.x, center.y))

    if len(candidates) != 4:
        return False

    remaining = list(candidates)
    for expected_x, expected_y in EXPECTED_HOLES:
        match_index = next(
            (
                idx
                for idx, (actual_x, actual_y) in enumerate(remaining)
                if close(actual_x, expected_x, POS_TOL) and close(actual_y, expected_y, POS_TOL)
            ),
            None,
        )
        if match_index is None:
            return False
        remaining.pop(match_index)
    return True


def horizontal_plane_faces(solid):
    faces = []
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Plane:
            continue
        bbox = face.BoundingBox()
        if bbox.zlen <= 0.01:
            faces.append(face)
    return faces


def outside_chamfers_match(solid) -> bool:
    top_bottom_faces = []
    for face in horizontal_plane_faces(solid):
        bbox = face.BoundingBox()
        center = face.Center()
        if close(bbox.xlen, 116.0, BBOX_TOL) and close(bbox.ylen, 76.0, BBOX_TOL):
            if close(abs(center.z), 5.0, BBOX_TOL):
                top_bottom_faces.append(face)
    return len(top_bottom_faces) == 2


def volume_matches(solid) -> bool:
    volume = solid.Volume()
    return abs(volume - EXPECTED_VOLUME) / EXPECTED_VOLUME <= VOLUME_REL_TOL


def evaluate() -> bool:
    if not check_no_gui_bypass(Path(r"C:\Users\User\Desktop")):
        return False
    solid = import_single_solid(OUTPUT_ROOT / OUTPUT_STEP)
    if solid is None:
        return False
    return (
        bbox_matches(solid)
        and through_holes_match(solid)
        and outside_chamfers_match(solid)
        and volume_matches(solid)
    )


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print(True if ok else False)
