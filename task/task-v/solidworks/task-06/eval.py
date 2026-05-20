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
OUTPUT_STEP = "gui_006_bracket_reinforced_out.step"

BBOX_TOL = 0.15
POS_TOL = 0.30
RADIUS_TOL = 0.10
VOLUME_REL_TOL = 0.03

EXPECTED_VOLUME = 74343.80545


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
        "xmin": -40.0,
        "xmax": 40.0,
        "ymin": -25.0,
        "ymax": 25.0,
        "zmin": 0.0,
        "zmax": 68.0,
    }
    return all(close(getattr(bbox, key), value, BBOX_TOL) for key, value in expected.items())


def cylinder_faces(solid):
    faces = []
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() == GeomAbs_Cylinder:
            cylinder = surface.Cylinder()
            faces.append((face, cylinder, cylinder.Axis().Direction(), cylinder.Location()))
    return faces


def base_holes_match(solid) -> bool:
    holes = []
    for face, cylinder, axis, _location in cylinder_faces(solid):
        if not close(cylinder.Radius(), 4.5, RADIUS_TOL):
            continue
        if abs(abs(axis.Z()) - 1.0) > 0.01:
            continue
        if not close(face.BoundingBox().zlen, 8.0, BBOX_TOL):
            continue
        center = face.Center()
        holes.append((center.x, center.y))
    return (
        len(holes) == 2
        and any(close(x, -25.0, POS_TOL) and close(y, 0.0, POS_TOL) for x, y in holes)
        and any(close(x, 25.0, POS_TOL) and close(y, 0.0, POS_TOL) for x, y in holes)
    )


def slot_matches(solid) -> bool:
    slot_ends = []
    for face, cylinder, axis, location in cylinder_faces(solid):
        if not close(cylinder.Radius(), 5.0, RADIUS_TOL):
            continue
        if abs(abs(axis.Y()) - 1.0) > 0.01:
            continue
        if not close(face.BoundingBox().ylen, 8.0, BBOX_TOL):
            continue
        if close(location.Z(), 35.0, POS_TOL):
            slot_ends.append(location.X())

    has_top = False
    has_bottom = False
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Plane:
            continue
        bbox = face.BoundingBox()
        center = face.Center()
        if close(bbox.xlen, 22.0, POS_TOL) and close(bbox.ylen, 8.0, POS_TOL) and bbox.zlen <= 0.02:
            if close(center.x, 0.0, POS_TOL) and close(center.y, 21.0, POS_TOL):
                has_top = has_top or close(center.z, 40.0, POS_TOL)
                has_bottom = has_bottom or close(center.z, 30.0, POS_TOL)

    return (
        len(slot_ends) == 2
        and any(close(x, -11.0, POS_TOL) for x in slot_ends)
        and any(close(x, 11.0, POS_TOL) for x in slot_ends)
        and has_top
        and has_bottom
    )


def gussets_match(solid) -> bool:
    gusset_centers = []
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Plane:
            continue
        bbox = face.BoundingBox()
        center = face.Center()
        if close(bbox.xlen, 6.0, POS_TOL) and close(bbox.ylen, 35.0, POS_TOL) and close(bbox.zlen, 35.0, POS_TOL):
            gusset_centers.append(center.x)
    return (
        len(gusset_centers) >= 2
        and any(close(x, -20.0, POS_TOL) for x in gusset_centers)
        and any(close(x, 20.0, POS_TOL) for x in gusset_centers)
    )


def volume_matches(solid) -> bool:
    return abs(solid.Volume() - EXPECTED_VOLUME) / EXPECTED_VOLUME <= VOLUME_REL_TOL


def evaluate() -> bool:
    if not check_no_gui_bypass(Path(r"C:\Users\User\Desktop")):
        return False
    solid = import_single_solid(OUTPUT_ROOT / OUTPUT_STEP)
    if solid is None:
        return False
    return (
        bbox_matches(solid)
        and base_holes_match(solid)
        and slot_matches(solid)
        and gussets_match(solid)
        and volume_matches(solid)
    )


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print(True if ok else False)
