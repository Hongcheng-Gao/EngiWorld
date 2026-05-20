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
OUTPUT_STEP = "gui_004_cover_vented_out.step"

BBOX_TOL = 0.15
POS_TOL = 0.25
RADIUS_TOL = 0.10
VOLUME_REL_TOL = 0.03

EXPECTED_SLOT_Y = [-24.0 + i * (48.0 / 7.0) for i in range(8)]
EXPECTED_VOLUME = 22827.610658


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
        "ymin": -35.0,
        "ymax": 35.0,
        "zmin": -9.0,
        "zmax": 9.0,
    }
    return all(close(getattr(bbox, key), value, BBOX_TOL) for key, value in expected.items())


def plane_faces(solid):
    faces = []
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() == GeomAbs_Plane:
            faces.append(face)
    return faces


def shell_matches(solid) -> bool:
    has_inside_top = False
    bottom_open = True
    has_inner_x = 0
    has_inner_y = 0
    for face in plane_faces(solid):
        bbox = face.BoundingBox()
        center = face.Center()
        if (
            close(bbox.xlen, 96.0, BBOX_TOL)
            and close(bbox.ylen, 66.0, BBOX_TOL)
            and bbox.zlen <= 0.02
            and close(center.z, 7.0, POS_TOL)
        ):
            has_inside_top = True
        if (
            close(bbox.xlen, 100.0, BBOX_TOL)
            and close(bbox.ylen, 70.0, BBOX_TOL)
            and bbox.zlen <= 0.02
            and close(center.z, -9.0, POS_TOL)
            and face.Area() > 6000.0
        ):
            bottom_open = False
        if bbox.xlen <= 0.02 and close(bbox.ylen, 60.0, BBOX_TOL) and close(bbox.zlen, 16.0, BBOX_TOL):
            if close(abs(center.x), 48.0, POS_TOL):
                has_inner_x += 1
        if close(bbox.xlen, 90.0, BBOX_TOL) and bbox.ylen <= 0.02 and close(bbox.zlen, 16.0, BBOX_TOL):
            if close(abs(center.y), 33.0, POS_TOL):
                has_inner_y += 1
    return has_inside_top and bottom_open and has_inner_x >= 2 and has_inner_y >= 2


def slots_match(solid) -> bool:
    end_faces = []
    side_faces = []
    for face in plane_faces(solid):
        bbox = face.BoundingBox()
        center = face.Center()
        if bbox.xlen <= 0.02 and close(bbox.ylen, 3.0, POS_TOL) and close(bbox.zlen, 2.0, POS_TOL):
            if close(abs(center.x), 20.0, POS_TOL) and close(center.z, 8.0, POS_TOL):
                end_faces.append((center.x, center.y))
        if close(bbox.xlen, 40.0, POS_TOL) and bbox.ylen <= 0.02 and close(bbox.zlen, 2.0, POS_TOL):
            if close(center.x, 0.0, POS_TOL) and close(center.z, 8.0, POS_TOL):
                side_faces.append(center.y)

    for y in EXPECTED_SLOT_Y:
        if not any(close(x, -20.0, POS_TOL) and close(actual_y, y, POS_TOL) for x, actual_y in end_faces):
            return False
        if not any(close(x, 20.0, POS_TOL) and close(actual_y, y, POS_TOL) for x, actual_y in end_faces):
            return False
        if not any(close(actual_y, y - 1.5, POS_TOL) for actual_y in side_faces):
            return False
        if not any(close(actual_y, y + 1.5, POS_TOL) for actual_y in side_faces):
            return False
    return True


def inside_corner_fillets_match(solid) -> bool:
    fillets = []
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Cylinder:
            continue
        cylinder = surface.Cylinder()
        axis = cylinder.Axis().Direction()
        if abs(abs(axis.Z()) - 1.0) > 0.01:
            continue
        bbox = face.BoundingBox()
        if close(cylinder.Radius(), 3.0, RADIUS_TOL) and close(bbox.zlen, 16.0, BBOX_TOL):
            center = face.Center()
            fillets.append((center.x, center.y))
    return (
        len(fillets) == 4
        and any(x < 0 and y < 0 for x, y in fillets)
        and any(x > 0 and y < 0 for x, y in fillets)
        and any(x < 0 and y > 0 for x, y in fillets)
        and any(x > 0 and y > 0 for x, y in fillets)
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
        and shell_matches(solid)
        and slots_match(solid)
        and inside_corner_fillets_match(solid)
        and volume_matches(solid)
    )


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print(True if ok else False)
