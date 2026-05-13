from __future__ import annotations

from pathlib import Path

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
OUTPUT_STEP = "gui_007_elbow_flanges_out.step"

BBOX_TOL = 0.25
POS_TOL = 0.35
RADIUS_TOL = 0.12
VOLUME_REL_TOL = 0.03

EXPECTED_VOLUME = 63195.427511


def close(actual: float, expected: float, tol: float) -> bool:
    return abs(float(actual) - float(expected)) <= tol


def import_solids(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        return []
    solids = cq.importers.importStep(str(path)).solids().vals()
    if not solids or any(not solid.isValid() for solid in solids):
        return []
    return solids


def all_faces(solids):
    for solid in solids:
        for face in solid.Faces():
            yield face


def bbox_matches(solids) -> bool:
    xs, ys, zs = [], [], []
    for solid in solids:
        bbox = solid.BoundingBox()
        xs.extend([bbox.xmin, bbox.xmax])
        ys.extend([bbox.ymin, bbox.ymax])
        zs.extend([bbox.zmin, bbox.zmax])
    return (
        close(min(xs), -30.0, BBOX_TOL)
        and close(max(xs), 29.0, BBOX_TOL)
        and close(min(ys), -29.0, BBOX_TOL)
        and close(max(ys), 29.0, BBOX_TOL)
        and close(min(zs), -8.0, BBOX_TOL)
        and close(max(zs), 119.0, BBOX_TOL)
    )


def pipe_ends_match(solids) -> bool:
    has_z_end = False
    has_x_end = False
    for face in all_faces(solids):
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Plane:
            continue
        bbox = face.BoundingBox()
        center = face.Center()
        area = face.Area()
        if close(area, 392.7, 3.0) and close(bbox.xlen, 30.0, BBOX_TOL) and close(bbox.ylen, 30.0, BBOX_TOL):
            has_z_end = has_z_end or (bbox.zlen <= 0.02 and close(center.z, 0.0, POS_TOL))
        if close(area, 392.7, 3.0) and bbox.xlen <= 0.02 and close(bbox.ylen, 30.0, BBOX_TOL) and close(bbox.zlen, 30.0, BBOX_TOL):
            has_x_end = has_x_end or (close(center.x, 0.0, POS_TOL) and close(center.z, 90.0, POS_TOL))
    return has_z_end and has_x_end


def cylinder_faces(solids):
    for face in all_faces(solids):
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() == GeomAbs_Cylinder:
            cylinder = surface.Cylinder()
            yield face, cylinder, cylinder.Axis().Direction(), cylinder.Location()


def flange_outer_and_center_holes_match(solids) -> bool:
    z_outer = z_center = x_outer = x_center = False
    for face, cylinder, axis, location in cylinder_faces(solids):
        radius = cylinder.Radius()
        if abs(abs(axis.Z()) - 1.0) <= 0.01 and close(location.X(), 0.0, POS_TOL) and close(location.Y(), 0.0, POS_TOL):
            z_outer = z_outer or (close(radius, 29.0, RADIUS_TOL) and close(location.Z(), -8.0, POS_TOL))
            z_center = z_center or (close(radius, 10.0, RADIUS_TOL) and close(location.Z(), -8.0, POS_TOL))
        if abs(abs(axis.X()) - 1.0) <= 0.01 and close(location.Y(), 0.0, POS_TOL) and close(location.Z(), 90.0, POS_TOL):
            x_outer = x_outer or (close(radius, 29.0, RADIUS_TOL) and close(location.X(), 0.0, POS_TOL))
            x_center = x_center or (close(radius, 10.0, RADIUS_TOL) and close(location.X(), 0.0, POS_TOL))
    return z_outer and z_center and x_outer and x_center


def bolt_holes_match(solids) -> bool:
    z_holes = []
    x_holes = []
    for _face, cylinder, axis, location in cylinder_faces(solids):
        if not close(cylinder.Radius(), 3.0, RADIUS_TOL):
            continue
        if abs(abs(axis.Z()) - 1.0) <= 0.01 and close(location.Z(), -8.0, POS_TOL):
            z_holes.append((location.X(), location.Y()))
        if abs(abs(axis.X()) - 1.0) <= 0.01 and close(location.X(), 0.0, POS_TOL):
            x_holes.append((location.Y(), location.Z()))

    expected_z = [(22.0, 0.0), (-22.0, 0.0), (0.0, 22.0), (0.0, -22.0)]
    expected_x = [(22.0, 90.0), (-22.0, 90.0), (0.0, 112.0), (0.0, 68.0)]
    return all(any(close(x, ex, POS_TOL) and close(y, ey, POS_TOL) for x, y in z_holes) for ex, ey in expected_z) and all(
        any(close(y, ey, POS_TOL) and close(z, ez, POS_TOL) for y, z in x_holes) for ey, ez in expected_x
    )


def volume_matches(solids) -> bool:
    volume = sum(solid.Volume() for solid in solids)
    return abs(volume - EXPECTED_VOLUME) / EXPECTED_VOLUME <= VOLUME_REL_TOL


def evaluate() -> bool:
    solids = import_solids(OUTPUT_ROOT / OUTPUT_STEP)
    if not solids:
        return False
    return (
        bbox_matches(solids)
        and pipe_ends_match(solids)
        and flange_outer_and_center_holes_match(solids)
        and bolt_holes_match(solids)
        and volume_matches(solids)
    )


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print(True if ok else False)
