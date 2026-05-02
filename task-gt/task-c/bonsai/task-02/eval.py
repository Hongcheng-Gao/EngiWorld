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
        "IfcSpace": 3,
        "IfcWall": 6,
        "IfcSlab": 1,
        "IfcDoor": 3,
        "IfcWindow": 3,
        "IfcOpeningElement": 6,
        "IfcRelVoidsElement": 6,
        "IfcRelFillsElement": 6,
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
    "storeys": {"Clinic Level": 0.0},
    "spaces": {
        "Consult 1": (3.2, 3.2),
        "Consult 2": (3.2, 3.2),
        "Corridor": (6.4, 1.8),
    },
    "space_height_m": 2.8,
    "slabs": {"Clinic Slab": (6.8, 5.4, 0.2)},
    "door_width_m": 0.9,
    "window_width_m": 1.2,
    "wall_height_m": 3.0,
    "wall_thickness_options_m": (0.15, 0.20),
    "linear_tolerance_m": 0.08,
    "height_tolerance_m": 0.05,
    "thickness_tolerance_m": 0.04,
}


def emit(ok):
    print("true" if ok else "false")
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


def check_storeys(model):
    storeys = model.by_type("IfcBuildingStorey")
    if {clean_name(s.Name) for s in storeys} != set(SPEC["storeys"]):
        return False
    for storey in storeys:
        if not approx(getattr(storey, "Elevation", None), SPEC["storeys"][clean_name(storey.Name)], 0.05):
            return False
    return True


def check_assignment(model):
    valid_storeys = set(SPEC["storeys"])
    for ifc_class in ("IfcSpace", "IfcWall", "IfcSlab", "IfcDoor", "IfcWindow"):
        for entity in model.by_type(ifc_class):
            storey = parent_storey(entity)
            if storey is None or clean_name(storey.Name) not in valid_storeys:
                return False
    return True


def dimensions_match(actual, expected, tol):
    return all(approx(a, e, tol) for a, e in zip(sorted(actual), sorted(expected)))


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


def check_slabs(model):
    slabs = {clean_name(s.Name): s for s in model.by_type("IfcSlab")}
    if set(slabs) != set(SPEC["slabs"]):
        return False
    for name, expected in SPEC["slabs"].items():
        bbox = shape_bbox(slabs[name])
        if bbox is None:
            return False
        sx, sy, sz = span(bbox)
        if not dimensions_match((sx, sy), expected[:2], SPEC["linear_tolerance_m"]):
            return False
        if not approx(sz, expected[2], SPEC["height_tolerance_m"]):
            return False
    return True


def check_walls(model):
    for wall in model.by_type("IfcWall"):
        bbox = shape_bbox(wall)
        if bbox is None:
            return False
        sx, sy, sz = span(bbox)
        thickness = min(sx, sy)
        if not approx(sz, SPEC["wall_height_m"], SPEC["height_tolerance_m"]):
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


def check_openings_and_widths(model):
    openings = set()
    for door in model.by_type("IfcDoor"):
        if not approx(overall_width(door, model), SPEC["door_width_m"], SPEC["linear_tolerance_m"]):
            return False
        opening = fill_opening(door)
        if opening is None or not opening_host(opening).is_a("IfcWall"):
            return False
        openings.add(opening.id())
    for window in model.by_type("IfcWindow"):
        if not approx(overall_width(window, model), SPEC["window_width_m"], SPEC["linear_tolerance_m"]):
            return False
        opening = fill_opening(window)
        if opening is None or not opening_host(opening).is_a("IfcWall"):
            return False
        openings.add(opening.id())
    return len(openings) == SPEC["counts"]["IfcOpeningElement"]


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
        and check_storeys(model)
        and check_assignment(model)
        and check_spaces(model)
        and check_slabs(model)
        and check_walls(model)
        and check_openings_and_widths(model)
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
