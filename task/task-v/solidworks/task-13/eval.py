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
OUTPUT_STEP = "gui_013_clamp_vjaw_out.step"

BBOX_TOL = 0.15
POS_TOL = 0.30
RADIUS_TOL = 0.08
VOLUME_REL_TOL = 0.03

EXPECTED_VOLUME = 53112.97614


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
        and close(bbox.ymin, -15.0, BBOX_TOL)
        and close(bbox.ymax, 15.0, BBOX_TOL)
        and close(bbox.zmin, 0.0, BBOX_TOL)
        and close(bbox.zmax, 25.0, BBOX_TOL)
    )


def cylinder_faces(solid):
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() == GeomAbs_Cylinder:
            cylinder = surface.Cylinder()
            yield face, cylinder, cylinder.Axis().Direction(), cylinder.Location()


def holes_and_fillets_match(solid) -> bool:
    holes = []
    outside_fillets = 0
    for face, cylinder, axis, location in cylinder_faces(solid):
        radius = cylinder.Radius()
        bbox = face.BoundingBox()
        if close(radius, 3.25, RADIUS_TOL) and abs(abs(axis.Z()) - 1.0) <= 0.01:
            if close(bbox.zlen, 25.0, BBOX_TOL):
                holes.append((location.X(), location.Y()))
        if close(radius, 1.0, RADIUS_TOL):
            outside_fillets += 1
    return (
        any(close(x, -25.0, POS_TOL) and close(y, 0.0, POS_TOL) for x, y in holes)
        and any(close(x, 25.0, POS_TOL) and close(y, 0.0, POS_TOL) for x, y in holes)
        and outside_fillets >= 8
    )


def v_groove_matches(solid) -> bool:
    upper = lower = False
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Plane:
            continue
        bbox = face.BoundingBox()
        center = face.Center()
        if close(bbox.xlen, 80.0, 1.0) and close(bbox.ylen, 8.0, POS_TOL) and close(bbox.zlen, 8.0, POS_TOL):
            if close(center.y, -11.0, POS_TOL) and close(center.z, 8.5, POS_TOL):
                lower = True
            if close(center.y, -11.0, POS_TOL) and close(center.z, 16.5, POS_TOL):
                upper = True
    return upper and lower


def volume_matches(solid) -> bool:
    return abs(solid.Volume() - EXPECTED_VOLUME) / EXPECTED_VOLUME <= VOLUME_REL_TOL


def evaluate() -> bool:
    if not check_no_gui_bypass(Path(r"C:\Users\User\Desktop")):
        return False
    solid = import_single_solid(OUTPUT_ROOT / OUTPUT_STEP)
    if solid is None:
        return False
    return bbox_matches(solid) and holes_and_fillets_match(solid) and v_groove_matches(solid) and volume_matches(solid)


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print(True if ok else False)
