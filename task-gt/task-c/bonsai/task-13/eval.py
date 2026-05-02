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
        "IfcWall": 8,
        "IfcSlab": 2,
    },
    "forbidden_counts": {
        "IfcSpace": 0,
        "IfcDoor": 0,
        "IfcWindow": 0,
        "IfcBuildingElementProxy": 0,
        "IfcFurniture": 0,
        "IfcRoof": 0,
        "IfcColumn": 0,
        "IfcBeam": 0,
        "IfcStair": 0,
        "IfcFlowTerminal": 0,
    },
    "project_name": "Unified Project",
    "site_name": "Unified Site",
    "building_name": "Unified Building",
    "storeys": {"Ground Floor", "First Floor"},
    "walls": {
        "WingA South Wall": (8.0, 0.2, 3.0),
        "WingA East Wall": (0.2, 6.0, 3.0),
        "WingA North Wall": (8.0, 0.2, 3.0),
        "WingA West Wall": (0.2, 6.0, 3.0),
        "WingB South Wall": (8.0, 0.2, 3.0),
        "WingB East Wall": (0.2, 6.0, 3.0),
        "WingB North Wall": (8.0, 0.2, 3.0),
        "WingB West Wall": (0.2, 6.0, 3.0),
    },
    "slabs": {
        "WingA Slab": (8.0, 6.0, 0.2),
        "WingB Slab": (8.0, 6.0, 0.2),
    },
    "bbox_min": (-0.2, 0.0, 0.0),
    "bbox_max": (22.0, 6.0, 6.2),
    "linear_tolerance_m": 0.08,
}


def emit(ok):
    print("true" if ok else "false")
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
    projects = model.by_type("IfcProject")
    sites = model.by_type("IfcSite")
    buildings = model.by_type("IfcBuilding")
    storeys = model.by_type("IfcBuildingStorey")
    return (
        len(projects) == 1
        and clean_name(projects[0].Name) == SPEC["project_name"]
        and len(sites) == 1
        and clean_name(sites[0].Name) == SPEC["site_name"]
        and len(buildings) == 1
        and clean_name(buildings[0].Name) == SPEC["building_name"]
        and {clean_name(s.Name) for s in storeys} == SPEC["storeys"]
    )


def check_products(model):
    walls = {clean_name(w.Name): w for w in model.by_type("IfcWall")}
    slabs = {clean_name(s.Name): s for s in model.by_type("IfcSlab")}
    if set(walls) != set(SPEC["walls"]) or set(slabs) != set(SPEC["slabs"]):
        return False
    for name, expected_dims in SPEC["walls"].items():
        bbox = shape_bbox(walls[name])
        if bbox is None or not dimensions_match(span(bbox), expected_dims, SPEC["linear_tolerance_m"]):
            return False
    for name, expected_dims in SPEC["slabs"].items():
        bbox = shape_bbox(slabs[name])
        if bbox is None or not dimensions_match(span(bbox), expected_dims, SPEC["linear_tolerance_m"]):
            return False
    for entity in list(walls.values()) + list(slabs.values()):
        if parent_storey(entity) is None or clean_name(parent_storey(entity).Name) not in SPEC["storeys"]:
            return False
    return True


def check_bbox(model):
    mins = None
    maxs = None
    for product in model.by_type("IfcProduct"):
        if not getattr(product, "Representation", None):
            continue
        bbox = shape_bbox(product)
        if bbox is None:
            continue
        pmin = bbox[:3]
        pmax = bbox[3:]
        mins = list(pmin) if mins is None else [min(a, b) for a, b in zip(mins, pmin)]
        maxs = list(pmax) if maxs is None else [max(a, b) for a, b in zip(maxs, pmax)]
    if mins is None or maxs is None:
        return False
    return all(approx(a, b, SPEC["linear_tolerance_m"]) for a, b in zip(mins, SPEC["bbox_min"])) and all(
        approx(a, b, SPEC["linear_tolerance_m"]) for a, b in zip(maxs, SPEC["bbox_max"])
    )


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
        and check_bbox(model)
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
