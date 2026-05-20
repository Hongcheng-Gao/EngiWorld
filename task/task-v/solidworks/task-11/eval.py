from __future__ import annotations

from pathlib import Path

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cone, GeomAbs_Cylinder
import sys

_TASK_V_ROOT = Path(__file__).resolve().parents[2]
if str(_TASK_V_ROOT) not in sys.path:
    sys.path.insert(0, str(_TASK_V_ROOT))
from _gui_bypass import check_no_gui_bypass



OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
OUTPUT_STEP = "gui_011_nozzle_flanged_out.step"

BBOX_TOL = 0.15
POS_TOL = 0.30
RADIUS_TOL = 0.10
VOLUME_REL_TOL = 0.03

EXPECTED_VOLUME = 71995.878842


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
        close(bbox.xmin, -30.0, BBOX_TOL)
        and close(bbox.xmax, 30.0, BBOX_TOL)
        and close(bbox.ymin, -30.0, BBOX_TOL)
        and close(bbox.ymax, 30.0, BBOX_TOL)
        and close(bbox.zmin, -8.0, BBOX_TOL)
        and close(bbox.zmax, 70.0, BBOX_TOL)
    )


def cylinder_faces(solid):
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() == GeomAbs_Cylinder:
            cylinder = surface.Cylinder()
            yield face, cylinder, cylinder.Axis().Direction(), cylinder.Location()


def cylinders_match(solid) -> bool:
    lower = flange = bore = False
    bolt_holes = []
    for face, cylinder, axis, location in cylinder_faces(solid):
        if abs(abs(axis.Z()) - 1.0) > 0.01:
            continue
        bbox = face.BoundingBox()
        center = face.Center()
        radius = cylinder.Radius()
        if close(radius, 18.0, RADIUS_TOL) and close(bbox.zlen, 35.0, BBOX_TOL) and close(center.z, 17.5, POS_TOL):
            lower = True
        if close(radius, 30.0, RADIUS_TOL) and close(bbox.zlen, 8.0, BBOX_TOL) and close(center.z, -4.0, POS_TOL):
            flange = True
        if close(radius, 5.0, RADIUS_TOL) and close(bbox.zlen, 78.0, BBOX_TOL) and close(center.x, 0.0, POS_TOL) and close(center.y, 0.0, POS_TOL):
            bore = True
        if close(radius, 3.0, RADIUS_TOL) and close(bbox.zlen, 8.0, BBOX_TOL):
            bolt_holes.append((location.X(), location.Y()))
    expected = [(23.0, 0.0), (-23.0, 0.0), (0.0, 23.0), (0.0, -23.0)]
    bolts = all(any(close(x, ex, POS_TOL) and close(y, ey, POS_TOL) for x, y in bolt_holes) for ex, ey in expected)
    return lower and flange and bore and bolts


def taper_matches(solid) -> bool:
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Cone:
            continue
        cone = surface.Cone()
        axis = cone.Axis().Direction()
        bbox = face.BoundingBox()
        if abs(abs(axis.Z()) - 1.0) <= 0.01 and close(bbox.zlen, 35.0, BBOX_TOL):
            if close(bbox.xlen, 36.0, BBOX_TOL) and close(bbox.ylen, 36.0, BBOX_TOL):
                return True
    return False


def volume_matches(solid) -> bool:
    return abs(solid.Volume() - EXPECTED_VOLUME) / EXPECTED_VOLUME <= VOLUME_REL_TOL


def evaluate() -> bool:
    if not check_no_gui_bypass(Path(r"C:\Users\User\Desktop")):
        return False
    solid = import_single_solid(OUTPUT_ROOT / OUTPUT_STEP)
    if solid is None:
        return False
    return bbox_matches(solid) and cylinders_match(solid) and taper_matches(solid) and volume_matches(solid)


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print(True if ok else False)
