from __future__ import annotations

import math
from pathlib import Path

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Torus
import sys

_TASK_V_ROOT = Path(__file__).resolve().parents[2]
if str(_TASK_V_ROOT) not in sys.path:
    sys.path.insert(0, str(_TASK_V_ROOT))
from _gui_bypass import check_no_gui_bypass



OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
OUTPUT_STEP = "gui_010_wheel_pattern_out.step"

BBOX_TOL = 0.15
POS_TOL = 0.30
RADIUS_TOL = 0.10
VOLUME_REL_TOL = 0.02

EXPECTED_VOLUME = 199948.286009
EXPECTED_BOLT_HOLES = [
    (42.0 * math.cos(math.radians(90 + i * 72)), 42.0 * math.sin(math.radians(90 + i * 72)))
    for i in range(5)
]


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
        close(bbox.xmin, -60.0, BBOX_TOL)
        and close(bbox.xmax, 60.0, BBOX_TOL)
        and close(bbox.ymin, -60.0, BBOX_TOL)
        and close(bbox.ymax, 60.0, BBOX_TOL)
        and close(bbox.zmin, -10.0, BBOX_TOL)
        and close(bbox.zmax, 10.0, BBOX_TOL)
    )


def cylinder_faces(solid):
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() == GeomAbs_Cylinder:
            cylinder = surface.Cylinder()
            yield face, cylinder, cylinder.Axis().Direction()


def z_axis_holes(solid, radius: float):
    holes = []
    for face, cylinder, axis in cylinder_faces(solid):
        if not close(cylinder.Radius(), radius, RADIUS_TOL):
            continue
        if abs(abs(axis.Z()) - 1.0) > 0.01:
            continue
        if close(face.BoundingBox().zlen, 20.0, BBOX_TOL):
            center = face.Center()
            holes.append((center.x, center.y))
    return holes


def center_hole_matches(solid) -> bool:
    holes = z_axis_holes(solid, 17.5)
    return len(holes) == 1 and close(holes[0][0], 0.0, POS_TOL) and close(holes[0][1], 0.0, POS_TOL)


def bolt_holes_match(solid) -> bool:
    holes = z_axis_holes(solid, 4.5)
    if len(holes) != 5:
        return False
    return all(
        any(close(x, ex, POS_TOL) and close(y, ey, POS_TOL) for x, y in holes)
        for ex, ey in EXPECTED_BOLT_HOLES
    )


def rim_fillets_match(solid) -> bool:
    z_values = []
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Torus:
            continue
        torus = surface.Torus()
        if close(torus.MajorRadius(), 58.0, RADIUS_TOL) and close(torus.MinorRadius(), 2.0, RADIUS_TOL):
            z_values.append(torus.Location().Z())
    return len(z_values) == 2 and any(close(z, 8.0, BBOX_TOL) for z in z_values) and any(close(z, -8.0, BBOX_TOL) for z in z_values)


def volume_matches(solid) -> bool:
    return abs(solid.Volume() - EXPECTED_VOLUME) / EXPECTED_VOLUME <= VOLUME_REL_TOL


def evaluate() -> bool:
    if not check_no_gui_bypass(Path(r"C:\Users\User\Desktop")):
        return False
    solid = import_single_solid(OUTPUT_ROOT / OUTPUT_STEP)
    if solid is None:
        return False
    return bbox_matches(solid) and center_hole_matches(solid) and bolt_holes_match(solid) and rim_fillets_match(solid) and volume_matches(solid)


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print(True if ok else False)
