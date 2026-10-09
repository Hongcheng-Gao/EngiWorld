#!/usr/bin/env python3
import math
import re
from pathlib import Path

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import ifcopenshell.util.unit


DESKTOP = Path("/home/user/Desktop")
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
        "IfcWallType": 1,
        "IfcSlabType": 1,
    },
    "forbidden": {
        "IfcBuildingElementProxy": 0,
        "IfcFurniture": 0,
        "IfcRoof": 0,
        "IfcColumn": 0,
        "IfcBeam": 0,
        "IfcStair": 0,
        "IfcFlowTerminal": 0,
    },
    "storey_name": "00_GROUND",
    "space_name": "AUTOMATION OFFICE",
    "space_reference": "OFF-001",
    "occupancy": "Office",
    "wall_names": {"WALL-SOUTH", "WALL-EAST", "WALL-NORTH", "WALL-WEST"},
    "slab_name": "OFFICE FLOOR SLAB",
    "wall_type": "OfficeWallType",
    "slab_type": "OfficeSlabType",
    "wall_layer_set": "OfficeWall-200mm",
    "slab_layer_set": "OfficeSlab-200mm",
    "automation": {
        "TaskCode": "BONSAI-CLI-01",
        "AutomationStatus": "CLI_UPDATED",
    },
    "room_dims": (6.0, 4.0),
    "wall_height": 3.0,
    "wall_thickness": 0.20,
    "slab_thickness": 0.20,
    "tol": 0.06,
    "thickness_tol": 0.035,
    "min_file_bytes": 1000,
}


def finish(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def norm(value):
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def text_equal(actual, expected):
    return norm(actual) == norm(expected)


def approx(actual, expected, tol):
    return actual is not None and abs(float(actual) - float(expected)) <= float(tol)


def unit_scale(model):
    try:
        return float(ifcopenshell.util.unit.calculate_unit_scale(model))
    except Exception:
        return 1.0


def entity_count(model, ifc_class):
    return len(model.by_type(ifc_class))


def check_schema(model):
    return str(getattr(model, "schema", "")).upper().startswith(SPEC["schema"])


def check_counts(model):
    for ifc_class, expected in SPEC["counts"].items():
        if entity_count(model, ifc_class) != expected:
            return False
    for ifc_class, expected in SPEC["forbidden"].items():
        if entity_count(model, ifc_class) != expected:
            return False
    return True


def unique_global_ids(model):
    gids = [e.GlobalId for e in model.by_type("IfcRoot") if getattr(e, "GlobalId", None)]
    return len(gids) == len(set(gids))


def psets(entity):
    try:
        return ifcopenshell.util.element.get_psets(entity, should_inherit=True)
    except Exception:
        return {}


def prop(entity, name):
    wanted = norm(name)
    for values in psets(entity).values():
        for key, value in values.items():
            if key == "id":
                continue
            if norm(key) == wanted:
                return value
    return None


def has_properties(entity, expected):
    return all(text_equal(prop(entity, key), value) for key, value in expected.items())


def container(entity):
    if entity.is_a("IfcSpace"):
        for rel in getattr(entity, "Decomposes", None) or []:
            parent = getattr(rel, "RelatingObject", None)
            if parent and parent.is_a("IfcBuildingStorey"):
                return parent
    try:
        return ifcopenshell.util.element.get_container(entity, should_get_direct=True)
    except Exception:
        return None


def type_of(entity):
    try:
        return ifcopenshell.util.element.get_type(entity)
    except Exception:
        return None


def material_of(entity):
    try:
        return ifcopenshell.util.element.get_material(entity, should_skip_usage=True, should_inherit=True)
    except Exception:
        return None


def material_name(material):
    return norm(getattr(material, "Name", ""))


def layer_set_matches(material, expected_name, expected_layers):
    if material is None:
        return False
    if material.is_a("IfcMaterialLayerSetUsage"):
        material = material.ForLayerSet
    if not material.is_a("IfcMaterialLayerSet"):
        return False
    if not text_equal(getattr(material, "LayerSetName", None) or getattr(material, "Name", None), expected_name):
        return False
    layers = list(getattr(material, "MaterialLayers", None) or [])
    if len(layers) != len(expected_layers):
        return False
    remaining = [(norm(name), float(thickness)) for name, thickness in expected_layers]
    for layer in layers:
        mat = getattr(layer, "Material", None)
        lname = material_name(mat)
        thickness = getattr(layer, "LayerThickness", None)
        matched = None
        for i, (expected_mat, expected_thickness) in enumerate(remaining):
            if expected_mat in lname and approx(thickness, expected_thickness, SPEC["thickness_tol"]):
                matched = i
                break
        if matched is None:
            return False
        remaining.pop(matched)
    return not remaining


def shape_bbox(entity):
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
    return min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)


def span(bbox):
    minx, miny, minz, maxx, maxy, maxz = bbox
    return maxx - minx, maxy - miny, maxz - minz


def check_geometry_preserved(model):
    tol = SPEC["tol"]
    space = model.by_type("IfcSpace")[0]
    slab = model.by_type("IfcSlab")[0]
    walls = model.by_type("IfcWall")
    bboxes = [shape_bbox(e) for e in [space, slab] + walls]
    if any(b is None for b in bboxes):
        return False
    sx, sy, _ = span(bboxes[0])
    if sorted(round(v, 2) for v in (sx, sy)) != sorted(round(v, 2) for v in SPEC["room_dims"]):
        if not (approx(sorted([sx, sy])[0], min(SPEC["room_dims"]), tol) and approx(sorted([sx, sy])[1], max(SPEC["room_dims"]), tol)):
            return False
    if not approx(span(bboxes[1])[2], SPEC["slab_thickness"], tol):
        return False
    for bbox in bboxes[2:]:
        wx, wy, wz = span(bbox)
        if not approx(wz, SPEC["wall_height"], tol):
            return False
        if not approx(min(wx, wy), SPEC["wall_thickness"], SPEC["thickness_tol"]):
            return False
    return True


def check_hierarchy_and_names(model):
    storey = model.by_type("IfcBuildingStorey")[0]
    space = model.by_type("IfcSpace")[0]
    slab = model.by_type("IfcSlab")[0]
    walls = model.by_type("IfcWall")
    products = [space, slab] + walls + model.by_type("IfcDoor") + model.by_type("IfcWindow")
    if not text_equal(storey.Name, SPEC["storey_name"]):
        return False
    if not text_equal(space.Name, SPEC["space_name"]):
        return False
    if not text_equal(slab.Name, SPEC["slab_name"]):
        return False
    if {str(w.Name or "") for w in walls} != SPEC["wall_names"]:
        return False
    for product in products:
        parent = container(product)
        if parent is None or parent.id() != storey.id():
            return False
    return True


def check_properties(model):
    space = model.by_type("IfcSpace")[0]
    walls = model.by_type("IfcWall")
    if not text_equal(prop(space, "Reference"), SPEC["space_reference"]):
        return False
    if not text_equal(prop(space, "OccupancyType"), SPEC["occupancy"]):
        return False
    if not has_properties(space, SPEC["automation"]):
        return False
    for wall in walls:
        if not has_properties(wall, SPEC["automation"]):
            return False
    return True


def check_types_and_materials(model):
    walls = model.by_type("IfcWall")
    slab = model.by_type("IfcSlab")[0]
    wall_types = {type_of(w).id() if type_of(w) else None for w in walls}
    if len(wall_types) != 1 or None in wall_types:
        return False
    wall_type = model.by_id(next(iter(wall_types)))
    slab_type = type_of(slab)
    if slab_type is None:
        return False
    if not wall_type.is_a("IfcWallType") or not text_equal(wall_type.Name, SPEC["wall_type"]):
        return False
    if not slab_type.is_a("IfcSlabType") or not text_equal(slab_type.Name, SPEC["slab_type"]):
        return False
    if not has_properties(wall_type, SPEC["automation"]) or not has_properties(slab_type, SPEC["automation"]):
        return False
    if not layer_set_matches(
        material_of(wall_type),
        SPEC["wall_layer_set"],
        [("brick", 0.15), ("gypsum board", 0.05)],
    ):
        return False
    if not layer_set_matches(
        material_of(slab_type),
        SPEC["slab_layer_set"],
        [("concrete", 0.20)],
    ):
        return False
    return True


def evaluate():
    ifc_path = DESKTOP / SPEC["required_output"]
    if not ifc_path.is_file() or ifc_path.stat().st_size < SPEC["min_file_bytes"]:
        return False
    model = ifcopenshell.open(str(ifc_path))
    return (
        check_schema(model)
        and unique_global_ids(model)
        and check_counts(model)
        and check_hierarchy_and_names(model)
        and check_properties(model)
        and check_types_and_materials(model)
        and check_geometry_preserved(model)
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
