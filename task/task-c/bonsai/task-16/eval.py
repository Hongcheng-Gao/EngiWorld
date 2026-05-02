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
        "IfcSpace": 5,
        "IfcWall": 7,
        "IfcSlab": 1,
        "IfcDoor": 4,
        "IfcWindow": 3,
        "IfcOpeningElement": 7,
        "IfcRelVoidsElement": 7,
        "IfcRelFillsElement": 7,
        "IfcMaterial": 4,
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
        "Lobby": (3.6, 2.8),
        "Office A": (3.6, 6.4),
        "Office B": (3.6, 9.4),
        "Meeting": (3.4, 4.4),
        "WC": (3.4, 4.6),
    },
    "space_height_m": 2.8,
    "walls": {
        "Wall-S": (12.0, 0.2, 3.0),
        "Wall-N": (12.0, 0.2, 3.0),
        "Wall-W": (0.2, 10.0, 3.0),
        "Wall-E": (0.2, 10.0, 3.0),
        "Part-1": (0.2, 9.6, 3.0),
        "Part-2": (0.2, 9.6, 3.0),
        "Part-3": (3.8, 0.2, 3.0),
    },
    "slab": ("Office Slab", (12.0, 10.0, 0.2)),
    "typed_csv_rows": {
        "Office Slab": ("IfcSlab", "OfficeSlabType", "Concrete:0.200m", 120.0, 24.0),
        "Wall-S": ("IfcWall", "OfficeWallType", "Brick:0.120m | Insulation:0.050m | Gypsum:0.015m", 36.0, 7.2),
        "Wall-N": ("IfcWall", "OfficeWallType", "Brick:0.120m | Insulation:0.050m | Gypsum:0.015m", 36.0, 7.2),
        "Wall-W": ("IfcWall", "OfficeWallType", "Brick:0.120m | Insulation:0.050m | Gypsum:0.015m", 30.0, 6.0),
        "Wall-E": ("IfcWall", "OfficeWallType", "Brick:0.120m | Insulation:0.050m | Gypsum:0.015m", 30.0, 6.0),
        "Part-1": ("IfcWall", "OfficeWallType", "Brick:0.120m | Insulation:0.050m | Gypsum:0.015m", 5.76, 5.76),
        "Part-2": ("IfcWall", "OfficeWallType", "Brick:0.120m | Insulation:0.050m | Gypsum:0.015m", 5.76, 5.76),
        "Part-3": ("IfcWall", "OfficeWallType", "Brick:0.120m | Insulation:0.050m | Gypsum:0.015m", 2.28, 2.28),
    },
    "csv_headers": ["GlobalId", "Class", "TypeName", "MaterialSummary", "NetArea", "NetVolume"],
    "linear_tolerance_m": 0.08,
    "quantity_tolerance": 0.02,
}


def emit(ok):
    print("true" if ok else "false")
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


def check_geometry(model):
    storeys = model.by_type("IfcBuildingStorey")
    if len(storeys) != 1 or clean_name(storeys[0].Name) != SPEC["storey_name"]:
        return False
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
        if not approx(sz, SPEC["space_height_m"], SPEC["linear_tolerance_m"]):
            return False
    walls = {clean_name(w.Name): w for w in model.by_type("IfcWall")}
    if set(walls) != set(SPEC["walls"]):
        return False
    for name, expected_dims in SPEC["walls"].items():
        bbox = shape_bbox(walls[name])
        if bbox is None or not dimensions_match(span(bbox), expected_dims, SPEC["linear_tolerance_m"]):
            return False
    slabs = model.by_type("IfcSlab")
    if len(slabs) != 1 or clean_name(slabs[0].Name) != SPEC["slab"][0]:
        return False
    bbox = shape_bbox(slabs[0])
    if bbox is None or not dimensions_match(span(bbox), SPEC["slab"][1], SPEC["linear_tolerance_m"]):
        return False
    for ifc_class in ("IfcSpace", "IfcWall", "IfcSlab", "IfcDoor", "IfcWindow"):
        for entity in model.by_type(ifc_class):
            storey = parent_storey(entity)
            if storey is None or clean_name(storey.Name) != SPEC["storey_name"]:
                return False
    return True


def check_csv_export(root, model):
    headers, rows = read_csv(root / "result.csv")
    if headers != SPEC["csv_headers"] or len(rows) != len(SPEC["typed_csv_rows"]):
        return False
    products_by_gid = {
        getattr(product, "GlobalId", ""): product
        for ifc_class in ("IfcWall", "IfcSlab")
        for product in model.by_type(ifc_class)
    }
    seen = set()
    for row in rows:
        gid = row.get("GlobalId", "")
        product = products_by_gid.get(gid)
        if product is None:
            return False
        name = clean_name(getattr(product, "Name", ""))
        spec = SPEC["typed_csv_rows"].get(name)
        if spec is None or name in seen:
            return False
        seen.add(name)
        if row.get("Class", "") != spec[0]:
            return False
        if row.get("TypeName", "") != spec[1]:
            return False
        if row.get("MaterialSummary", "") != spec[2]:
            return False
        if not approx(parse_number(row.get("NetArea", "")), spec[3], SPEC["quantity_tolerance"]):
            return False
        if not approx(parse_number(row.get("NetVolume", "")), spec[4], SPEC["quantity_tolerance"]):
            return False
    return seen == set(SPEC["typed_csv_rows"])


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
        and check_geometry(model)
        and check_csv_export(result_dir, model)
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
