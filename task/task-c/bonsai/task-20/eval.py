#!/usr/bin/env python3
import csv
import re
from pathlib import Path

import ifcopenshell


DESKTOP = Path("/home/user/Desktop")
import ifcopenshell.geom


SPEC = {
    "required_outputs": ("result.ifc", "result.csv"),
    "min_ifc_bytes": 500,
    "schema": "IFC4",
    "counts": {
        "IfcProject": 1,
        "IfcSite": 1,
        "IfcBuilding": 1,
        "IfcBuildingStorey": 1,
        "IfcSpace": 4,
        "IfcWall": 10,
        "IfcSlab": 3,
    },
    "forbidden_counts": {
        "IfcDoor": 0,
        "IfcWindow": 0,
        "IfcRoof": 0,
        "IfcBuildingElementProxy": 0,
        "IfcFurniture": 0,
        "IfcColumn": 0,
        "IfcBeam": 0,
        "IfcStair": 0,
        "IfcFlowTerminal": 0,
    },
    "project_name": "Merged House Garage",
    "site_name": "Default Site",
    "building_name": "Default Building",
    "storey_name": "Ground Floor",
    "spaces": {
        "House Living": (3.7, 5.4, 2.8),
        "House Bed": (3.5, 2.7, 2.8),
        "House Kitchen": (3.5, 2.5, 2.8),
        "Garage Bay": (5.4, 3.9, 2.8),
    },
    "slabs": {
        "House Slab": (8.0, 6.0, 0.2),
        "Garage Slab": (6.0, 4.5, 0.2),
        "Connector Apron": (2.0, 1.2, 0.12),
    },
    "csv_headers": ["BuildingPart", "Storey", "GrossFootprintArea", "SpaceCount"],
    "csv_rows": {
        "House": ("Ground Floor", 48.0, 3),
        "Garage": ("Ground Floor", 27.0, 1),
    },
    "linear_tolerance_m": 0.08,
    "area_tolerance": 0.02,
}


def emit(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def clean_name(value):
    return re.sub(r"\s+", " ", str(value or "").strip())


def approx(actual, expected, tol):
    return actual is not None and abs(float(actual) - float(expected)) <= float(tol)


def parse_number(value):
    return float(str(value).strip())


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
        f.seek(0)
        headers = next(csv.reader(f), [])
    return headers, rows


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
        and len(model.by_type("IfcBuildingStorey")) == 1
        and clean_name(model.by_type("IfcBuildingStorey")[0].Name) == SPEC["storey_name"]
    )


def check_products(model):
    spaces = {clean_name(s.Name): s for s in model.by_type("IfcSpace")}
    if set(spaces) != set(SPEC["spaces"]):
        return False
    for name, dims in SPEC["spaces"].items():
        bbox = shape_bbox(spaces[name])
        if bbox is None or not dimensions_match(span(bbox), dims, SPEC["linear_tolerance_m"]):
            return False
        if parent_storey(spaces[name]) is None or clean_name(parent_storey(spaces[name]).Name) != SPEC["storey_name"]:
            return False
    slabs = {clean_name(s.Name): s for s in model.by_type("IfcSlab")}
    if set(slabs) != set(SPEC["slabs"]):
        return False
    for name, dims in SPEC["slabs"].items():
        bbox = shape_bbox(slabs[name])
        if bbox is None or not dimensions_match(span(bbox), dims, SPEC["linear_tolerance_m"]):
            return False
    return True


def check_csv_export(root):
    headers, rows = read_csv(root / "result.csv")
    if headers != SPEC["csv_headers"] or len(rows) != len(SPEC["csv_rows"]):
        return False
    seen = set()
    for row in rows:
        part = clean_name(row.get("BuildingPart", ""))
        spec = SPEC["csv_rows"].get(part)
        if spec is None:
            return False
        seen.add(part)
        if clean_name(row.get("Storey", "")) != spec[0]:
            return False
        if not approx(parse_number(row.get("GrossFootprintArea", "")), spec[1], SPEC["area_tolerance"]):
            return False
        if int(row.get("SpaceCount", "")) != spec[2]:
            return False
    return seen == set(SPEC["csv_rows"])


def evaluate():
    result_dir = DESKTOP
    if not result_dir.is_dir():
        return False
    ifc_path = result_dir / "result.ifc"
    csv_path = result_dir / "result.csv"
    if not ifc_path.is_file() or ifc_path.stat().st_size < SPEC["min_ifc_bytes"] or not csv_path.is_file() or csv_path.stat().st_size == 0:
        return False
    model = ifcopenshell.open(str(ifc_path))
    return (
        str(getattr(model, "schema", "")).upper().startswith(SPEC["schema"])
        and unique_global_ids(model)
        and check_counts(model)
        and check_hierarchy(model)
        and check_products(model)
        and check_csv_export(result_dir)
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
