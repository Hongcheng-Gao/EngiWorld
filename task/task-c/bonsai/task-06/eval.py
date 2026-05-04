#!/usr/bin/env python3
import re
from pathlib import Path

import ifcopenshell


DESKTOP = Path("/home/user/Desktop")
import ifcopenshell.geom
import ifcopenshell.util.unit


SPEC = {
    "required_output": "result.ifc",
    "min_file_bytes": 500,
    "schema": "IFC4",
    "counts": {
        "IfcProject": 1,
        "IfcSite": 1,
        "IfcBuilding": 1,
        "IfcBuildingStorey": 1,
        "IfcSpace": 2,
        "IfcWall": 5,
        "IfcSlab": 1,
        "IfcDoor": 1,
        "IfcWindow": 2,
        "IfcOpeningElement": 3,
        "IfcRelVoidsElement": 3,
        "IfcRelFillsElement": 3,
        "IfcProjectedCRS": 1,
        "IfcMapConversion": 1,
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
    "storey_name": "Level 00",
    "spaces": {"Office": (5.6, 4.6), "WC": (1.7, 2.2)},
    "space_height_m": 3.0,
    "slab": ("Floor Slab", (8.0, 5.0, 0.2)),
    "door_width_m": 0.8,
    "window_widths_m": [1.0, 1.4],
    "wall_height_m": 3.0,
    "wall_thickness_options_m": (0.12, 0.20),
    "crs_name": "EPSG:3857",
    "map_conversion": {
        "Eastings": 501234.0,
        "Northings": 6843210.0,
        "OrthogonalHeight": 35.0,
        "XAxisAbscissa": 1.0,
        "XAxisOrdinate": 0.0,
        "Scale": 1.0,
    },
    "max_local_abs_coordinate_m": 100.0,
    "linear_tolerance_m": 0.08,
    "height_tolerance_m": 0.05,
    "thickness_tolerance_m": 0.04,
    "map_tolerance": 0.001,
}


def emit(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def clean_name(value):
    return re.sub(r"\s+", " ", str(value or "").strip())


def approx(actual, expected, tol):
    return actual is not None and abs(float(actual) - float(expected)) <= float(tol)


def unit_scale(model):
    try:
        return float(ifcopenshell.util.unit.calculate_unit_scale(model))
    except Exception:
        return 1.0


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
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def span(bbox):
    minx, miny, minz, maxx, maxy, maxz = bbox
    return (maxx - minx, maxy - miny, maxz - minz)


def parent_storey(obj):
    if obj.is_a("IfcSpace"):
        for rel in getattr(obj, "Decomposes", None) or []:
            parent = getattr(rel, "RelatingObject", None)
            if parent and parent.is_a("IfcBuildingStorey"):
                return parent
    for rel in getattr(obj, "ContainedInStructure", None) or []:
        parent = getattr(rel, "RelatingStructure", None)
        if parent and parent.is_a("IfcBuildingStorey"):
            return parent
    return None


def unique_global_ids(model):
    gids = [e.GlobalId for e in model.by_type("IfcRoot") if getattr(e, "GlobalId", None)]
    return len(gids) == len(set(gids))


def check_counts(model):
    for ifc_class, expected in SPEC["counts"].items():
        if len(model.by_type(ifc_class)) != expected:
            return False
    for ifc_class, expected in SPEC["forbidden_counts"].items():
        if len(model.by_type(ifc_class)) != expected:
            return False
    return True


def dimensions_match(actual, expected, tol):
    return all(approx(a, e, tol) for a, e in zip(sorted(actual), sorted(expected)))


def check_storey_and_assignment(model):
    storeys = model.by_type("IfcBuildingStorey")
    if len(storeys) != 1 or clean_name(storeys[0].Name) != SPEC["storey_name"]:
        return False
    for ifc_class in ("IfcSpace", "IfcWall", "IfcSlab", "IfcDoor", "IfcWindow"):
        for entity in model.by_type(ifc_class):
            storey = parent_storey(entity)
            if storey is None or clean_name(storey.Name) != SPEC["storey_name"]:
                return False
    return True


def check_spaces(model):
    spaces = {clean_name(s.Name): s for s in model.by_type("IfcSpace")}
    if set(spaces) != set(SPEC["spaces"]):
        return False
    for name, expected_xy in SPEC["spaces"].items():
        bbox = shape_bbox(spaces[name])
        if bbox is None:
            return False
        sx, sy, sz = span(bbox)
        if not dimensions_match((sx, sy), expected_xy, SPEC["linear_tolerance_m"]):
            return False
        if not approx(sz, SPEC["space_height_m"], SPEC["height_tolerance_m"]):
            return False
    return True


def check_slab_and_walls(model):
    slabs = model.by_type("IfcSlab")
    if len(slabs) != 1 or clean_name(slabs[0].Name) != SPEC["slab"][0]:
        return False
    bbox = shape_bbox(slabs[0])
    if bbox is None:
        return False
    sx, sy, sz = span(bbox)
    expected = SPEC["slab"][1]
    if not dimensions_match((sx, sy), expected[:2], SPEC["linear_tolerance_m"]):
        return False
    if not approx(sz, expected[2], SPEC["height_tolerance_m"]):
        return False
    for wall in model.by_type("IfcWall"):
        bbox = shape_bbox(wall)
        if bbox is None:
            return False
        wx, wy, wz = span(bbox)
        thickness = min(wx, wy)
        if not approx(wz, SPEC["wall_height_m"], SPEC["height_tolerance_m"]):
            return False
        if not any(approx(thickness, option, SPEC["thickness_tolerance_m"]) for option in SPEC["wall_thickness_options_m"]):
            return False
    return True


def overall_width(entity, model):
    value = getattr(entity, "OverallWidth", None)
    if value in (None, 0, ""):
        return None
    raw = float(value)
    scaled = raw * unit_scale(model)
    return scaled if 0.05 <= scaled <= 20.0 else raw


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


def check_openings(model):
    openings = set()
    door = model.by_type("IfcDoor")[0]
    if not approx(overall_width(door, model), SPEC["door_width_m"], SPEC["linear_tolerance_m"]):
        return False
    opening = fill_opening(door)
    if opening is None or not opening_host(opening).is_a("IfcWall"):
        return False
    openings.add(opening.id())
    actual_window_widths = []
    for window in model.by_type("IfcWindow"):
        actual_window_widths.append(overall_width(window, model))
        opening = fill_opening(window)
        if opening is None or not opening_host(opening).is_a("IfcWall"):
            return False
        openings.add(opening.id())
    if len(openings) != SPEC["counts"]["IfcOpeningElement"]:
        return False
    return all(
        approx(a, e, SPEC["linear_tolerance_m"])
        for a, e in zip(sorted(actual_window_widths), sorted(SPEC["window_widths_m"]))
    )


def check_georeferencing(model):
    crs = model.by_type("IfcProjectedCRS")[0]
    if clean_name(getattr(crs, "Name", "")) != SPEC["crs_name"]:
        return False
    conversion = model.by_type("IfcMapConversion")[0]
    for attr, expected in SPEC["map_conversion"].items():
        if not approx(getattr(conversion, attr, None), expected, SPEC["map_tolerance"]):
            return False
    max_abs = 0.0
    for product in model.by_type("IfcProduct"):
        if product.is_a("IfcOpeningElement") or not getattr(product, "Representation", None):
            continue
        bbox = shape_bbox(product)
        if bbox is None:
            continue
        max_abs = max(max_abs, *(abs(v) for v in bbox))
    return 0.0 < max_abs <= SPEC["max_local_abs_coordinate_m"]


def evaluate():
    result_dir = DESKTOP
    if not result_dir.is_dir():
        return False
    ifc_path = result_dir / SPEC["required_output"]
    if not ifc_path.is_file() or ifc_path.stat().st_size < SPEC["min_file_bytes"]:
        return False
    model = ifcopenshell.open(str(ifc_path))
    return (
        str(getattr(model, "schema", "")).upper().startswith(SPEC["schema"])
        and unique_global_ids(model)
        and check_counts(model)
        and check_storey_and_assignment(model)
        and check_spaces(model)
        and check_slab_and_walls(model)
        and check_openings(model)
        and check_georeferencing(model)
    )


def main():
    try:
        emit(evaluate())
    except SystemExit:
        raise
    except Exception:
        emit(False)


if __name__ == "__main__":
    main()
