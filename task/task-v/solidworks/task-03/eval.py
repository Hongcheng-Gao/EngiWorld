from __future__ import annotations

from pathlib import Path

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cone, GeomAbs_Cylinder, GeomAbs_Plane
import sys

_TASK_V_ROOT = Path(__file__).resolve().parents[2]
if str(_TASK_V_ROOT) not in sys.path:
    sys.path.insert(0, str(_TASK_V_ROOT))
from _gui_bypass import check_no_gui_bypass



OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
OUTPUT_STEP = "gui_003_shaft_keyway_out.step"

BBOX_TOL = 0.15
POS_TOL = 0.25
RADIUS_TOL = 0.10
VOLUME_REL_TOL = 0.02

EXPECTED_VOLUME = 60548.872075


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
        "xmin": -10.0,
        "xmax": 100.0,
        "ymin": -15.0,
        "ymax": 15.0,
        "zmin": -15.0,
        "zmax": 15.0,
    }
    return all(close(getattr(bbox, key), value, BBOX_TOL) for key, value in expected.items())


def cylinder_faces(solid):
    result = []
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Cylinder:
            continue
        cylinder = surface.Cylinder()
        axis = cylinder.Axis().Direction()
        center = face.Center()
        result.append((face, cylinder.Radius(), axis, center))
    return result


def shaft_segments_match(solid) -> bool:
    has_left = False
    has_right = False
    for face, radius, axis, center in cylinder_faces(solid):
        if abs(abs(axis.X()) - 1.0) > 0.01:
            continue
        bbox = face.BoundingBox()
        if close(radius, 15.0, RADIUS_TOL) and bbox.xlen >= 45.0 and close(center.x, 20.0, 1.0):
            has_left = True
        if close(radius, 11.0, RADIUS_TOL) and bbox.xlen >= 45.0 and close(center.x, 74.5, 1.0):
            has_right = True
    return has_left and has_right


def keyway_matches(solid) -> bool:
    bottom_found = False
    side_y = []
    end_x = []
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Plane:
            continue
        bbox = face.BoundingBox()
        center = face.Center()
        if (
            close(bbox.xlen, 35.0, POS_TOL)
            and close(bbox.ylen, 8.0, POS_TOL)
            and bbox.zlen <= 0.02
            and close(center.x, 20.0, POS_TOL)
            and close(center.y, 0.0, POS_TOL)
            and close(center.z, 12.0, POS_TOL)
        ):
            bottom_found = True
        if close(bbox.xlen, 35.0, POS_TOL) and bbox.ylen <= 0.02 and 2.0 <= bbox.zlen <= 3.2:
            if close(center.x, 20.0, POS_TOL) and close(abs(center.y), 4.0, POS_TOL):
                side_y.append(center.y)
        if bbox.xlen <= 0.02 and close(bbox.ylen, 8.0, POS_TOL) and 2.5 <= bbox.zlen <= 3.5:
            if close(abs(center.x - 20.0), 17.5, POS_TOL) and close(center.y, 0.0, POS_TOL):
                end_x.append(center.x)
    return (
        bottom_found
        and any(y > 0 for y in side_y)
        and any(y < 0 for y in side_y)
        and any(close(x, 2.5, POS_TOL) for x in end_x)
        and any(close(x, 37.5, POS_TOL) for x in end_x)
    )


def end_chamfers_match(solid) -> bool:
    chamfer_x = []
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Cone:
            continue
        cone = surface.Cone()
        axis = cone.Axis().Direction()
        if abs(abs(axis.X()) - 1.0) > 0.01:
            continue
        bbox = face.BoundingBox()
        center = face.Center()
        if close(bbox.xlen, 1.0, BBOX_TOL):
            chamfer_x.append(center.x)
    return (
        len(chamfer_x) >= 2
        and any(close(x, -9.5, BBOX_TOL) for x in chamfer_x)
        and any(close(x, 99.5, BBOX_TOL) for x in chamfer_x)
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
        and shaft_segments_match(solid)
        and keyway_matches(solid)
        and end_chamfers_match(solid)
        and volume_matches(solid)
    )


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print(True if ok else False)
