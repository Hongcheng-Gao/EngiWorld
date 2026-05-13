from __future__ import annotations

from pathlib import Path

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
OUTPUT_STEP = "gui_012_pcb_support_out.step"

BBOX_TOL = 0.15
POS_TOL = 0.25
RADIUS_TOL = 0.08
VOLUME_REL_TOL = 0.03

EXPECTED_VOLUME = 25774.41396
POINTS = [(35.0, 20.0), (35.0, -20.0), (-35.0, 20.0), (-35.0, -20.0)]


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
        close(bbox.xmin, -50.0, BBOX_TOL)
        and close(bbox.xmax, 50.0, BBOX_TOL)
        and close(bbox.ymin, -30.0, BBOX_TOL)
        and close(bbox.ymax, 30.0, BBOX_TOL)
        and close(bbox.zmin, 0.0, BBOX_TOL)
        and close(bbox.zmax, 16.0, BBOX_TOL)
    )


def cylinder_faces(solid):
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() == GeomAbs_Cylinder:
            cylinder = surface.Cylinder()
            yield face, cylinder, cylinder.Axis().Direction(), cylinder.Location()


def standoffs_and_holes_match(solid) -> bool:
    standoffs = []
    holes = []
    corner_fillets = []
    for face, cylinder, axis, location in cylinder_faces(solid):
        if abs(abs(axis.Z()) - 1.0) > 0.01:
            continue
        bbox = face.BoundingBox()
        radius = cylinder.Radius()
        if close(radius, 4.0, RADIUS_TOL) and close(bbox.zlen, 12.0, BBOX_TOL):
            standoffs.append((location.X(), location.Y()))
        if close(radius, 1.6, RADIUS_TOL) and close(bbox.zlen, 16.0, BBOX_TOL):
            holes.append((location.X(), location.Y()))
        if close(radius, 6.0, RADIUS_TOL) and close(bbox.zlen, 4.0, BBOX_TOL):
            corner_fillets.append((location.X(), location.Y()))
    features = all(any(close(x, ex, POS_TOL) and close(y, ey, POS_TOL) for x, y in standoffs) for ex, ey in POINTS)
    through_holes = all(any(close(x, ex, POS_TOL) and close(y, ey, POS_TOL) for x, y in holes) for ex, ey in POINTS)
    corners = (
        len(corner_fillets) == 4
        and any(x < 0 and y < 0 for x, y in corner_fillets)
        and any(x < 0 and y > 0 for x, y in corner_fillets)
        and any(x > 0 and y < 0 for x, y in corner_fillets)
        and any(x > 0 and y > 0 for x, y in corner_fillets)
    )
    return features and through_holes and corners


def volume_matches(solid) -> bool:
    return abs(solid.Volume() - EXPECTED_VOLUME) / EXPECTED_VOLUME <= VOLUME_REL_TOL


def evaluate() -> bool:
    solid = import_single_solid(OUTPUT_ROOT / OUTPUT_STEP)
    if solid is None:
        return False
    return bbox_matches(solid) and standoffs_and_holes_match(solid) and volume_matches(solid)


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print(True if ok else False)
