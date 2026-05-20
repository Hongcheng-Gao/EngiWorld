#!/usr/bin/env python3
import math
import re
from pathlib import Path

import ifcopenshell


DESKTOP = Path("/home/user/Desktop")
import ifcopenshell.geom
import ifcopenshell.util.unit


SPEC = {
    "required_output": "result.ifc",
    "schema": "IFC4",
    "counts": {
        "IfcProject": 1,
        "IfcSite": 1,
        "IfcBuilding": 1,
        "IfcBuildingStorey": 1,
        "IfcSpace": 1,
        "IfcWall": 4,
        "IfcSlab": 1,
        "IfcDoor": 1,
        "IfcWindow": 1,
        "IfcOpeningElement": 2,
        "IfcRelVoidsElement": 2,
        "IfcRelFillsElement": 2,
    },
    "forbidden_counts": {
        "IfcBuildingElementProxy": 0,
        "IfcFurniture": 0,
        "IfcRoof": 0,
        "IfcColumn": 0,
        "IfcBeam": 0,
        "IfcStair": 0,
        "IfcFlowTerminal": 0,
    },
    "space_name": "Room 101",
    "room_clear_x_m": 6.0,
    "room_clear_y_m": 4.0,
    "wall_height_m": 3.0,
    "wall_thickness_m": 0.20,
    "slab_thickness_m": 0.20,
    "door_width_m": 0.90,
    "window_width_m": 1.50,
    "linear_tolerance_m": 0.05,
    "wall_thickness_tolerance_m": 0.03,
    "height_tolerance_m": 0.05,
    "min_file_bytes": 500,
}


def finish(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def norm(value):
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def approx(actual, expected, tol):
    return actual is not None and abs(float(actual) - float(expected)) <= float(tol)


def unit_scale(model):
    try:
        return float(ifcopenshell.util.unit.calculate_unit_scale(model))
    except Exception:
        return 1.0


def entity_count(model, ifc_class):
    return len(model.by_type(ifc_class))


def unique_global_ids(model):
    gids = [e.GlobalId for e in model.by_type("IfcRoot") if getattr(e, "GlobalId", None)]
    return len(gids) == len(set(gids))


def parent_storey(obj):
    if obj.is_a("IfcSpace"):
        for rel in getattr(obj, "Decomposes", None) or []:
            parent = getattr(rel, "RelatingObject", None)
            if parent and parent.is_a("IfcBuildingStorey"):
                return parent
        return None
    for rel in getattr(obj, "ContainedInStructure", None) or []:
        parent = getattr(rel, "RelatingStructure", None)
        if parent and parent.is_a("IfcBuildingStorey"):
            return parent
    return None


def one_storey_contains_all_products(model):
    storeys = model.by_type("IfcBuildingStorey")
    if len(storeys) != 1:
        return False
    storey_id = storeys[0].id()
    products = []
    for ifc_class in ("IfcSpace", "IfcWall", "IfcSlab", "IfcDoor", "IfcWindow"):
        products.extend(model.by_type(ifc_class))
    for product in products:
        storey = parent_storey(product)
        if storey is None or storey.id() != storey_id:
            return False
    return True


def shape_bbox(model, entity):
    settings = ifcopenshell.geom.settings()
    try:
        settings.set(settings.USE_WORLD_COORDS, True)
    except Exception:
        pass
    shape = ifcopenshell.geom.create_shape(settings, entity)
    verts = list(shape.geometry.verts)
    if not verts:
        return None
    xs = verts[0::3]
    ys = verts[1::3]
    zs = verts[2::3]
    return (
        min(xs),
        min(ys),
        min(zs),
        max(xs),
        max(ys),
        max(zs),
    )


def span(bbox):
    minx, miny, minz, maxx, maxy, maxz = bbox
    return (maxx - minx, maxy - miny, maxz - minz)


def wall_orientation(bbox):
    sx, sy, _ = span(bbox)
    return "x" if sx >= sy else "y"


def overall_width(entity, model):
    value = getattr(entity, "OverallWidth", None)
    if value not in (None, 0, ""):
        raw = float(value)
        scaled = raw * unit_scale(model)
        if 0.05 <= scaled <= 20.0:
            return scaled
        if 0.05 <= raw <= 20.0:
            return raw
    return None


def fill_opening(fill):
    rels = getattr(fill, "FillsVoids", None) or []
    if len(rels) != 1:
        return None
    return getattr(rels[0], "RelatingOpeningElement", None)


def opening_host(opening):
    rels = getattr(opening, "VoidsElements", None) or []
    if len(rels) != 1:
        return None
    return getattr(rels[0], "RelatingBuildingElement", None)


def host_wall_for_fill(fill):
    opening = fill_opening(fill)
    if opening is None:
        return None
    host = opening_host(opening)
    return host if host is not None and host.is_a("IfcWall") else None


def check_schema(model):
    schema = getattr(model, "schema", "")
    return str(schema).upper().startswith(SPEC["schema"])


def check_counts(model):
    for ifc_class, expected in SPEC["counts"].items():
        if entity_count(model, ifc_class) != expected:
            return False
    for ifc_class, expected in SPEC["forbidden_counts"].items():
        if entity_count(model, ifc_class) != expected:
            return False
    return True


def check_geometry(model):
    tol = SPEC["linear_tolerance_m"]
    height_tol = SPEC["height_tolerance_m"]
    thickness_tol = SPEC["wall_thickness_tolerance_m"]

    space = model.by_type("IfcSpace")[0]
    slab = model.by_type("IfcSlab")[0]
    walls = model.by_type("IfcWall")
    door = model.by_type("IfcDoor")[0]
    window = model.by_type("IfcWindow")[0]

    if norm(getattr(space, "Name", "")) != norm(SPEC["space_name"]):
        return False

    space_bbox = shape_bbox(model, space)
    slab_bbox = shape_bbox(model, slab)
    wall_bboxes = [(wall, shape_bbox(model, wall)) for wall in walls]
    if not space_bbox or not slab_bbox or any(b is None for _, b in wall_bboxes):
        return False

    sx, sy, _ = span(space_bbox)
    clear_dims = sorted([sx, sy])
    target_dims = sorted([SPEC["room_clear_x_m"], SPEC["room_clear_y_m"]])
    if not approx(clear_dims[0], target_dims[0], tol):
        return False
    if not approx(clear_dims[1], target_dims[1], tol):
        return False

    _, _, slab_thickness = span(slab_bbox)
    if not approx(slab_thickness, SPEC["slab_thickness_m"], tol):
        return False

    for _, bbox in wall_bboxes:
        wx, wy, wz = span(bbox)
        thickness = min(wx, wy)
        if not approx(wz, SPEC["wall_height_m"], height_tol):
            return False
        if not approx(thickness, SPEC["wall_thickness_m"], thickness_tol):
            return False

    if not approx(overall_width(door, model), SPEC["door_width_m"], tol):
        return False
    if not approx(overall_width(window, model), SPEC["window_width_m"], tol):
        return False

    door_host = host_wall_for_fill(door)
    window_host = host_wall_for_fill(window)
    if door_host is None or window_host is None:
        return False

    opening_ids = {fill_opening(door).id(), fill_opening(window).id()}
    if len(opening_ids) != 2:
        return False

    # South wall is the wall whose bbox has the lowest centre Y; east wall has the highest centre X.
    def center_x(item):
        bbox = item[1]
        return (bbox[0] + bbox[3]) / 2.0

    def center_y(item):
        bbox = item[1]
        return (bbox[1] + bbox[4]) / 2.0

    south_wall = min(wall_bboxes, key=center_y)[0]
    east_wall = max(wall_bboxes, key=center_x)[0]
    if door_host.id() != south_wall.id():
        return False
    if window_host.id() != east_wall.id():
        return False

    return True


def evaluate():
    result_dir = DESKTOP
    if not result_dir.is_dir():
        return False
    ifc_path = result_dir / SPEC["required_output"]
    if not ifc_path.is_file() or ifc_path.stat().st_size < SPEC["min_file_bytes"]:
        return False
    model = ifcopenshell.open(str(ifc_path))
    return (
        check_schema(model)
        and unique_global_ids(model)
        and check_counts(model)
        and one_storey_contains_all_products(model)
        and check_geometry(model)
    )


def main():
    try:
        finish(evaluate())
    except SystemExit:
        raise
    except Exception:
        finish(False)


if __name__ == "__main__":
    main()
