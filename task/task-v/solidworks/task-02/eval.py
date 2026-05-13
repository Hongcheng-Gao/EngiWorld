from __future__ import annotations

import math
from pathlib import Path

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Torus


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
OUTPUT_STEP = "gui_002_flange_out.step"

BBOX_TOL = 0.10
POS_TOL = 0.20
RADIUS_TOL = 0.10
VOLUME_REL_TOL = 0.02

EXPECTED_BOLT_HOLES = [
    (35.0 * math.cos(math.radians(angle)), 35.0 * math.sin(math.radians(angle)))
    for angle in (0, 60, 120, 180, 240, 300)
]
EXPECTED_VOLUME = 76095.896954


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
        "xmin": -50.0,
        "xmax": 50.0,
        "ymin": -50.0,
        "ymax": 50.0,
        "zmin": -6.0,
        "zmax": 6.0,
    }
    return all(close(getattr(bbox, key), value, BBOX_TOL) for key, value in expected.items())


def cylinder_faces(solid):
    faces = []
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Cylinder:
            continue
        cylinder = surface.Cylinder()
        axis = cylinder.Axis().Direction()
        center = face.Center()
        faces.append((face, cylinder.Radius(), axis, center.x, center.y))
    return faces


def z_axis_through_cylinders(solid, radius: float):
    result = []
    for face, actual_radius, axis, center_x, center_y in cylinder_faces(solid):
        if not close(actual_radius, radius, RADIUS_TOL):
            continue
        if abs(abs(axis.Z()) - 1.0) > 0.01:
            continue
        if not close(face.BoundingBox().zlen, 12.0, BBOX_TOL):
            continue
        result.append((center_x, center_y))
    return result


def center_bore_matches(solid) -> bool:
    bores = z_axis_through_cylinders(solid, 20.0)
    return len(bores) == 1 and close(bores[0][0], 0.0, POS_TOL) and close(bores[0][1], 0.0, POS_TOL)


def bolt_holes_match(solid) -> bool:
    holes = z_axis_through_cylinders(solid, 3.5)
    if len(holes) != 6:
        return False
    remaining = list(holes)
    for expected_x, expected_y in EXPECTED_BOLT_HOLES:
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


def outside_fillets_match(solid) -> bool:
    fillets = []
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Torus:
            continue
        torus = surface.Torus()
        axis = torus.Axis().Direction()
        if abs(abs(axis.Z()) - 1.0) > 0.01:
            continue
        if close(torus.MinorRadius(), 1.5, RADIUS_TOL) and close(torus.MajorRadius(), 48.5, RADIUS_TOL):
            fillets.append(torus.Location().Z())
    return (
        len(fillets) == 2
        and any(close(z, 4.5, BBOX_TOL) for z in fillets)
        and any(close(z, -4.5, BBOX_TOL) for z in fillets)
    )


def volume_matches(solid) -> bool:
    return abs(solid.Volume() - EXPECTED_VOLUME) / EXPECTED_VOLUME <= VOLUME_REL_TOL


def evaluate() -> bool:
    solid = import_single_solid(OUTPUT_ROOT / OUTPUT_STEP)
    if solid is None:
        return False
    return (
        bbox_matches(solid)
        and center_bore_matches(solid)
        and bolt_holes_match(solid)
        and outside_fillets_match(solid)
        and volume_matches(solid)
    )


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print(True if ok else False)
