from __future__ import annotations

from pathlib import Path

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cone, GeomAbs_Cylinder


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
OUTPUT_STEP = "gui_009_hinge_leaf_out.step"

BBOX_TOL = 0.15
POS_TOL = 0.25
RADIUS_TOL = 0.08
VOLUME_REL_TOL = 0.03

EXPECTED_VOLUME = 10827.880922
MOUNTING_X = [-33.0, -11.0, 11.0, 33.0]


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
    expected = {
        "xmin": -45.0,
        "xmax": 45.0,
        "ymin": -16.0,
        "ymax": 16.0,
        "zmin": 0.0,
        "zmax": 10.8,
    }
    return all(close(getattr(bbox, key), value, BBOX_TOL) for key, value in expected.items())


def cylinder_faces(solid):
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() == GeomAbs_Cylinder:
            cylinder = surface.Cylinder()
            yield face, cylinder, cylinder.Axis().Direction(), cylinder.Location()


def knuckles_and_pin_bore_match(solid) -> bool:
    outer_centers = []
    bore_centers = []
    for face, cylinder, axis, _location in cylinder_faces(solid):
        if abs(abs(axis.X()) - 1.0) > 0.01:
            continue
        center = face.Center()
        bbox = face.BoundingBox()
        if close(cylinder.Radius(), 4.0, RADIUS_TOL) and close(center.y, 12.0, POS_TOL) and close(center.z, 7.24, 0.6):
            outer_centers.append((center.x, bbox.xlen))
        if close(cylinder.Radius(), 2.1, RADIUS_TOL) and close(center.y, 12.0, POS_TOL) and close(center.z, 6.8, POS_TOL):
            bore_centers.append((center.x, bbox.xlen))

    expected = [(-32.5, 25.0), (0.0, 20.0), (32.5, 25.0)]
    return all(
        any(close(cx, ex, POS_TOL) and close(length, elen, BBOX_TOL) for cx, length in outer_centers)
        for ex, elen in expected
    ) and all(
        any(close(cx, ex, POS_TOL) and close(length, elen, BBOX_TOL) for cx, length in bore_centers)
        for ex, elen in expected
    )


def mounting_holes_match(solid) -> bool:
    through = []
    countersinks = []
    for face, cylinder, axis, _location in cylinder_faces(solid):
        if close(cylinder.Radius(), 2.25, RADIUS_TOL) and abs(abs(axis.Z()) - 1.0) <= 0.01:
            center = face.Center()
            through.append((center.x, center.y))
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Cone:
            continue
        cone = surface.Cone()
        axis = cone.Axis().Direction()
        bbox = face.BoundingBox()
        center = face.Center()
        if abs(abs(axis.Z()) - 1.0) <= 0.01 and close(bbox.xlen, 8.5, BBOX_TOL) and close(bbox.ylen, 8.5, BBOX_TOL):
            if close(bbox.zlen, 2.0, BBOX_TOL):
                countersinks.append((center.x, center.y))

    return all(any(close(x, ex, POS_TOL) and close(y, 0.0, POS_TOL) for x, y in through) for ex in MOUNTING_X) and all(
        any(close(x, ex, POS_TOL) and close(y, 0.0, POS_TOL) for x, y in countersinks) for ex in MOUNTING_X
    )


def volume_matches(solid) -> bool:
    return abs(solid.Volume() - EXPECTED_VOLUME) / EXPECTED_VOLUME <= VOLUME_REL_TOL


def evaluate() -> bool:
    solid = import_single_solid(OUTPUT_ROOT / OUTPUT_STEP)
    if solid is None:
        return False
    return bbox_matches(solid) and knuckles_and_pin_bore_match(solid) and mounting_holes_match(solid) and volume_matches(solid)


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print(True if ok else False)
