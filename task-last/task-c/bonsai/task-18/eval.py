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
        "IfcBuildingStorey": 2,
        "IfcSpace": 2,
        "IfcWall": 8,
        "IfcSlab": 2,
        "IfcRoof": 1,
        "IfcWallType": 1,
    },
    "forbidden_counts": {
        "IfcDoor": 0,
        "IfcWindow": 0,
        "IfcBuildingElementProxy": 0,
        "IfcFurniture": 0,
        "IfcColumn": 0,
        "IfcBeam": 0,
        "IfcStair": 0,
        "IfcFlowTerminal": 0,
    },
    "project_name": "Normalized IFC4",
    "site_name": "Default Site",
    "building_name": "Default Building",
    "storeys": {"Ground Floor", "Upper Floor"},
    "spaces": {"GF Office": (9.4, 7.4, 2.8), "UF Office": (9.4, 7.4, 2.8)},
    "walls": {
        "W-S": (10.0, 0.2, 3.0),
        "W-S-UP": (10.0, 0.2, 3.0),
        "W-N": (10.0, 0.2, 3.0),
        "W-N-UP": (10.0, 0.2, 3.0),
        "W-W": (0.2, 8.0, 3.0),
        "W-W-UP": (0.2, 8.0, 3.0),
        "W-E": (0.2, 8.0, 3.0),
        "W-E-UP": (0.2, 8.0, 3.0),
    },
    "slabs": {"GF Slab": (10.0, 8.0, 0.2), "UF Slab": (10.0, 8.0, 0.2)},
    "roof": ("Roof", (10.0, 8.0, 0.25)),
    "wall_type_name": "ExtWallType-A",
    "linear_tolerance_m": 0.08,
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


def check_hierarchy(model):
    return (
        len(model.by_type("IfcProject")) == 1
        and clean_name(model.by_type("IfcProject")[0].Name) == SPEC["project_name"]
        and len(model.by_type("IfcSite")) == 1
        and clean_name(model.by_type("IfcSite")[0].Name) == SPEC["site_name"]
        and len(model.by_type("IfcBuilding")) == 1
        and clean_name(model.by_type("IfcBuilding")[0].Name) == SPEC["building_name"]
        and {clean_name(s.Name) for s in model.by_type("IfcBuildingStorey")} == SPEC["storeys"]
        and len(model.by_type("IfcWallType")) == 1
        and clean_name(model.by_type("IfcWallType")[0].Name) == SPEC["wall_type_name"]
    )


def check_products(model):
    spaces = {clean_name(s.Name): s for s in model.by_type("IfcSpace")}
    if set(spaces) != set(SPEC["spaces"]):
        return False
    for name, dims in SPEC["spaces"].items():
        bbox = shape_bbox(spaces[name])
        if bbox is None or not dimensions_match(span(bbox), dims, SPEC["linear_tolerance_m"]):
            return False
    walls = {clean_name(w.Name): w for w in model.by_type("IfcWall")}
    if set(walls) != set(SPEC["walls"]):
        return False
    for name, dims in SPEC["walls"].items():
        bbox = shape_bbox(walls[name])
        if bbox is None or not dimensions_match(span(bbox), dims, SPEC["linear_tolerance_m"]):
            return False
    slabs = {clean_name(s.Name): s for s in model.by_type("IfcSlab")}
    if set(slabs) != set(SPEC["slabs"]):
        return False
    for name, dims in SPEC["slabs"].items():
        bbox = shape_bbox(slabs[name])
        if bbox is None or not dimensions_match(span(bbox), dims, SPEC["linear_tolerance_m"]):
            return False
    roofs = model.by_type("IfcRoof")
    if len(roofs) != 1 or clean_name(roofs[0].Name) != SPEC["roof"][0]:
        return False
    bbox = shape_bbox(roofs[0])
    if bbox is None or not dimensions_match(span(bbox), SPEC["roof"][1], SPEC["linear_tolerance_m"]):
        return False
    return all(parent_storey(entity) is not None and clean_name(parent_storey(entity).Name) in SPEC["storeys"] for entity in list(spaces.values()) + list(walls.values()) + list(slabs.values()) + roofs)


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
        and check_hierarchy(model)
        and check_products(model)
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
