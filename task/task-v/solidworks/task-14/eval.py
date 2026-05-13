from __future__ import annotations

from pathlib import Path

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
OUTPUT_STEP = "gui_014_handle_ergonomic_out.step"

BBOX_TOL = 0.20
POS_TOL = 0.35
RADIUS_TOL = 0.10
VOLUME_REL_TOL = 0.04

EXPECTED_VOLUME = 26542.774625


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
        close(bbox.xmin, -41.0, BBOX_TOL)
        and close(bbox.xmax, 41.0, BBOX_TOL)
        and close(bbox.ymin, -12.0, BBOX_TOL)
        and close(bbox.ymax, 12.0, BBOX_TOL)
        and close(bbox.zmin, 0.0, BBOX_TOL)
        and close(bbox.zmax, 20.0, BBOX_TOL)
    )


def cylinder_faces(solid):
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() == GeomAbs_Cylinder:
            cylinder = surface.Cylinder()
            yield face, cylinder, cylinder.Axis().Direction(), cylinder.Location()


def bosses_holes_arc_and_fillets_match(solid) -> bool:
    bosses = []
    holes = []
    has_arc = False
    fillet_count = 0
    for face, cylinder, axis, location in cylinder_faces(solid):
        radius = cylinder.Radius()
        bbox = face.BoundingBox()
        center = face.Center()
        if close(radius, 9.0, RADIUS_TOL) and abs(abs(axis.Z()) - 1.0) <= 0.01:
            bosses.append(center.x)
        if close(radius, 2.5, RADIUS_TOL) and abs(abs(axis.Z()) - 1.0) <= 0.01:
            holes.append((center.x, center.y))
        if close(radius, 10.0, RADIUS_TOL) and abs(abs(axis.X()) - 1.0) <= 0.01:
            if close(location.Z(), 10.0, POS_TOL) and bbox.zlen >= 11.5:
                has_arc = True
        if close(radius, 0.8, RADIUS_TOL):
            fillet_count += 1
    return (
        any(close(x, -38.0, 1.0) for x in bosses)
        and any(close(x, 38.0, 1.0) for x in bosses)
        and any(close(x, -32.0, POS_TOL) and close(y, 0.0, POS_TOL) for x, y in holes)
        and any(close(x, 32.0, POS_TOL) and close(y, 0.0, POS_TOL) for x, y in holes)
        and has_arc
        and fillet_count >= 8
    )


def volume_matches(solid) -> bool:
    return abs(solid.Volume() - EXPECTED_VOLUME) / EXPECTED_VOLUME <= VOLUME_REL_TOL


def evaluate() -> bool:
    solid = import_single_solid(OUTPUT_ROOT / OUTPUT_STEP)
    if solid is None:
        return False
    return bbox_matches(solid) and bosses_holes_arc_and_fillets_match(solid) and volume_matches(solid)


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print(True if ok else False)
