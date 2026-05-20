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
        "IfcSpace": 1,
        "IfcWall": 4,
        "IfcSlab": 1,
        "IfcRoof": 1,
        "IfcDoor": 1,
        "IfcWindow": 4,
        "IfcOpeningElement": 5,
        "IfcRelVoidsElement": 5,
        "IfcRelFillsElement": 5,
    },
    "forbidden_counts": {
        "IfcBuildingElementProxy": 0,
        "IfcFurniture": 0,
        "IfcColumn": 0,
        "IfcBeam": 0,
        "IfcStair": 0,
        "IfcFlowTerminal": 0,
    },
    "storey_name": "Ground Floor",
    "space_name": "Lobby",
    "space_dims": (9.4, 5.4, 3.0),
    "slab": ("Base Slab", (10.0, 6.0, 0.2)),
    "roof": ("Entrance Canopy", (2.2, 0.8, 0.18)),
    "opening_specs": {
        "Accessible Entrance Door": ("IfcDoor", "South Wall", 1.2, 2.2),
        "North Window A": ("IfcWindow", "North Wall", 1.5, 1.2),
        "North Window B": ("IfcWindow", "North Wall", 1.5, 1.2),
        "East Window A": ("IfcWindow", "East Wall", 1.5, 1.2),
        "West Window A": ("IfcWindow", "West Wall", 1.5, 1.2),
    },
    "csv_headers": ["GlobalId", "Class", "Width", "Height", "HostWall"],
    "linear_tolerance_m": 0.08,
    "height_tolerance_m": 0.05,
    "csv_tolerance": 0.02,
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


def check_geometry(model):
    storeys = model.by_type("IfcBuildingStorey")
    if len(storeys) != 1 or clean_name(storeys[0].Name) != SPEC["storey_name"]:
        return False
    spaces = model.by_type("IfcSpace")
    if len(spaces) != 1 or clean_name(spaces[0].Name) != SPEC["space_name"]:
        return False
    bbox = shape_bbox(spaces[0])
    if bbox is None or not dimensions_match(span(bbox), SPEC["space_dims"], SPEC["linear_tolerance_m"]):
        return False
    slab = model.by_type("IfcSlab")[0]
    if clean_name(slab.Name) != SPEC["slab"][0]:
        return False
    bbox = shape_bbox(slab)
    if bbox is None or not dimensions_match(span(bbox), SPEC["slab"][1], SPEC["linear_tolerance_m"]):
        return False
    roofs = model.by_type("IfcRoof")
    if len(roofs) != 1 or clean_name(roofs[0].Name) != SPEC["roof"][0]:
        return False
    bbox = shape_bbox(roofs[0])
    if bbox is None or not dimensions_match(span(bbox), SPEC["roof"][1], SPEC["linear_tolerance_m"]):
        return False
    for ifc_class in ("IfcSpace", "IfcWall", "IfcSlab", "IfcRoof", "IfcDoor", "IfcWindow"):
        for entity in model.by_type(ifc_class):
            storey = parent_storey(entity)
            if storey is None or clean_name(storey.Name) != SPEC["storey_name"]:
                return False
    return True


def fill_opening(fill):
    rels = getattr(fill, "FillsVoids", None) or []
    return getattr(rels[0], "RelatingOpeningElement", None) if len(rels) == 1 else None


def opening_host(opening):
    rels = getattr(opening, "VoidsElements", None) or []
    return getattr(rels[0], "RelatingBuildingElement", None) if len(rels) == 1 else None


def opening_width_height(opening):
    bbox = shape_bbox(opening)
    if bbox is None:
        return None
    sx, sy, sz = span(bbox)
    return max(sx, sy), sz


def check_openings(model):
    products = {}
    products.update({clean_name(d.Name): d for d in model.by_type("IfcDoor")})
    products.update({clean_name(w.Name): w for w in model.by_type("IfcWindow")})
    if set(products) != set(SPEC["opening_specs"]):
        return False
    opening_ids = set()
    for name, (ifc_class, host_name, expected_width, expected_height) in SPEC["opening_specs"].items():
        product = products[name]
        if product.is_a() != ifc_class:
            return False
        opening = fill_opening(product)
        if opening is None:
            return False
        host = opening_host(opening)
        if host is None or clean_name(host.Name) != host_name:
            return False
        dims = opening_width_height(opening)
        if dims is None:
            return False
        if not approx(dims[0], expected_width, SPEC["linear_tolerance_m"]) or not approx(dims[1], expected_height, SPEC["linear_tolerance_m"]):
            return False
        opening_ids.add(opening.id())
    return len(opening_ids) == SPEC["counts"]["IfcOpeningElement"]


def check_csv_export(root, model):
    headers, rows = read_csv(root / "result.csv")
    if headers != SPEC["csv_headers"] or len(rows) != len(SPEC["opening_specs"]):
        return False
    by_gid = {}
    for name, (_, host_name, width, height) in SPEC["opening_specs"].items():
        product = next(e for e in list(model.by_type("IfcDoor")) + list(model.by_type("IfcWindow")) if clean_name(e.Name) == name)
        by_gid[product.GlobalId] = (product.is_a(), width, height, host_name)
    if set(row.get("GlobalId", "") for row in rows) != set(by_gid):
        return False
    for row in rows:
        spec = by_gid.get(row.get("GlobalId", ""))
        if spec is None:
            return False
        if row.get("Class", "") != spec[0]:
            return False
        if not approx(parse_number(row.get("Width", "")), spec[1], SPEC["csv_tolerance"]):
            return False
        if not approx(parse_number(row.get("Height", "")), spec[2], SPEC["csv_tolerance"]):
            return False
        if clean_name(row.get("HostWall", "")) != spec[3]:
            return False
    return True


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
        and check_openings(model)
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
