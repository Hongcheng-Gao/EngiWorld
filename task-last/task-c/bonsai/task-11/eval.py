#!/usr/bin/env python3
import re
from pathlib import Path

import ifcopenshell


DESKTOP = Path("/home/user/Desktop")
import ifcopenshell.geom


SPEC = {
    "required_output": "result.ifc",
    "min_file_bytes": 500,
    "schema": "IFC4",
    "counts": {
        "IfcProject": 1,
        "IfcSite": 1,
        "IfcBuilding": 1,
        "IfcBuildingStorey": 1,
        "IfcSpace": 4,
        "IfcWall": 7,
        "IfcSlab": 1,
        "IfcDoor": 4,
        "IfcWindow": 2,
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
    "storey_name": "Ground Floor",
    "spaces": {
        "Living": (3.6, 3.5),
        "Kitchen": (3.6, 1.65),
        "Bedroom": (3.5, 2.7),
        "Bath": (2.7, 2.45),
    },
    "space_height_m": 3.0,
    "slab": ("Base Slab", (8.0, 6.0, 0.2)),
    "walls": {
        "South Wall": (8.0, 0.2, 3.0),
        "East Wall": (0.2, 6.0, 3.0),
        "North Wall": (8.0, 0.2, 3.0),
        "West Wall": (0.2, 6.0, 3.0),
        "Partition 1": (0.15, 5.6, 3.0),
        "Partition 2": (3.8, 0.15, 3.0),
        "Partition 3": (3.0, 0.15, 3.0),
    },
    "opening_specs": {
        "Main Entrance": ("South Wall", (1.0, 0.2, 2.1)),
        "North Window": ("North Wall", (1.5, 0.2, 1.2)),
        "East Window": ("East Wall", (1.5, 0.2, 1.2)),
        "Door Bedroom": ("Partition 1", (0.8, 0.15, 2.1)),
        "Door Kitchen": ("Partition 2", (0.8, 0.15, 2.1)),
        "Door Bath": ("Partition 3", (0.8, 0.15, 2.1)),
    },
    "linear_tolerance_m": 0.08,
    "height_tolerance_m": 0.05,
}


def emit(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def clean_name(value):
    return re.sub(r"\s+", " ", str(value or "").strip())


def approx(actual, expected, tol):
    return actual is not None and abs(float(actual) - float(expected)) <= float(tol)


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


def dimensions_match(actual, expected, tol):
    return all(approx(a, e, tol) for a, e in zip(sorted(actual), sorted(expected)))


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


def check_storey_assignment(model):
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
    if bbox is None or not dimensions_match(span(bbox), SPEC["slab"][1], SPEC["linear_tolerance_m"]):
        return False
    walls = {clean_name(w.Name): w for w in model.by_type("IfcWall")}
    if set(walls) != set(SPEC["walls"]):
        return False
    for name, expected_dims in SPEC["walls"].items():
        bbox = shape_bbox(walls[name])
        if bbox is None or not dimensions_match(span(bbox), expected_dims, SPEC["linear_tolerance_m"]):
            return False
    return True


def fill_opening(fill):
    rels = getattr(fill, "FillsVoids", None) or []
    return getattr(rels[0], "RelatingOpeningElement", None) if len(rels) == 1 else None


def opening_host(opening):
    rels = getattr(opening, "VoidsElements", None) or []
    return getattr(rels[0], "RelatingBuildingElement", None) if len(rels) == 1 else None


def check_openings(model):
    products = {}
    products.update({clean_name(d.Name): d for d in model.by_type("IfcDoor")})
    products.update({clean_name(w.Name): w for w in model.by_type("IfcWindow")})
    if set(products) != set(SPEC["opening_specs"]):
        return False
    opening_ids = set()
    for name, (host_name, expected_dims) in SPEC["opening_specs"].items():
        opening = fill_opening(products[name])
        if opening is None:
            return False
        host = opening_host(opening)
        if host is None or clean_name(host.Name) != host_name:
            return False
        bbox = shape_bbox(opening)
        if bbox is None or not dimensions_match(span(bbox), expected_dims, SPEC["linear_tolerance_m"]):
            return False
        opening_ids.add(opening.id())
    return len(opening_ids) == SPEC["counts"]["IfcOpeningElement"]


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
        and check_storey_assignment(model)
        and check_spaces(model)
        and check_slab_and_walls(model)
        and check_openings(model)
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
