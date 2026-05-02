#!/usr/bin/env python3
import csv
import re
from pathlib import Path

import ifcopenshell


DESKTOP = Path("C:/Users/Administrator/Desktop")


SPEC = {
    "required_outputs": {"result.ifc": 500, "result.txt": 20},
    "schema": "IFC4",
    "storey_count": 2,
    "min_counts": {"IfcWall": 8, "IfcSlab": 2, "IfcRoof": 2},
    "bbox_exact": {"min": [0.0, 0.0, 0.0], "max": [18.0, 8.0, 6.6]},
    "bbox_tolerance": 0.5,
    "csv_headers": ["ZoneNumber", "ZoneName", "Area"],
    "area_tolerance_m2": 0.10,
    "csv_total_area_range_m2": (159.0, 161.0),
    "zone_rows": [
        ("Z01", "CLASSROOM-1", 24.0, "LOWER"),
        ("Z02", "CLASSROOM-2", 24.0, "LOWER"),
        ("Z03", "PLAY-HALL", 48.0, "LOWER"),
        ("Z04", "STAFF", 8.0, "LOWER"),
        ("Z05", "WC-CHILD", 4.0, "LOWER"),
        ("Z06", "WC-STAFF", 4.0, "LOWER"),
        ("Z07", "CLASSROOM-3", 24.0, "UPPER"),
        ("Z08", "CLASSROOM-4", 24.0, "UPPER"),
    ],
}


def finish(ok):
    print("true" if ok else "false")
    raise SystemExit(0)


def norm(value):
    return re.sub(r"\s+", " ", str(value or "").replace("_", "-").strip()).upper()


def unique_global_ids(model):
    gids = [e.GlobalId for e in model.by_type("IfcRoot") if getattr(e, "GlobalId", None)]
    return len(gids) == len(set(gids))


def parent_storey_id(obj):
    for rel in getattr(obj, "Decomposes", None) or []:
        parent = getattr(rel, "RelatingObject", None)
        if parent and parent.is_a("IfcBuildingStorey"):
            return parent.id()
    for rel in getattr(obj, "ContainedInStructure", None) or []:
        parent = getattr(rel, "RelatingStructure", None)
        if parent and parent.is_a("IfcBuildingStorey"):
            return parent.id()
    return None


def space_records(model):
    records = {}
    for space in model.by_type("IfcSpace"):
        records[norm(getattr(space, "Name", ""))] = {"storey_id": parent_storey_id(space)}
    return records


def ifc_bbox(model):
    import numpy as np
    import ifcopenshell.geom

    settings = ifcopenshell.geom.settings()
    try:
        settings.set(settings.USE_WORLD_COORDS, True)
    except Exception:
        pass
    mins = None
    maxs = None
    for product in model.by_type("IfcProduct"):
        if product.is_a("IfcOpeningElement") or not getattr(product, "Representation", None):
            continue
        try:
            shape = ifcopenshell.geom.create_shape(settings, product)
            verts = np.array(shape.geometry.verts, dtype=float).reshape(-1, 3)
        except Exception:
            continue
        if verts.size == 0:
            continue
        pmin = verts.min(axis=0)
        pmax = verts.max(axis=0)
        mins = pmin if mins is None else np.minimum(mins, pmin)
        maxs = pmax if maxs is None else np.maximum(maxs, pmax)
    if mins is None or maxs is None:
        return None
    return mins.tolist(), maxs.tolist()


def parse_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def check_ifc(model):
    if not str(getattr(model, "schema", "")).upper().startswith(SPEC["schema"]):
        return False
    if not unique_global_ids(model):
        return False
    if len(model.by_type("IfcBuildingStorey")) != SPEC["storey_count"]:
        return False
    if len(model.by_type("IfcSpace")) != len(SPEC["zone_rows"]):
        return False
    for cls, minimum in SPEC["min_counts"].items():
        if len(model.by_type(cls)) < minimum:
            return False
    records = space_records(model)
    if set(records) != {norm(name) for _, name, _, _ in SPEC["zone_rows"]}:
        return False
    groups = {"LOWER": set(), "UPPER": set()}
    for _, name, _, group in SPEC["zone_rows"]:
        storey_id = records[norm(name)]["storey_id"]
        if storey_id is None:
            return False
        groups[group].add(storey_id)
    if len(groups["LOWER"]) != 1 or len(groups["UPPER"]) != 1:
        return False
    if groups["LOWER"] == groups["UPPER"]:
        return False
    bbox = ifc_bbox(model)
    if bbox is None:
        return False
    mins, maxs = bbox
    tol = SPEC["bbox_tolerance"]
    for actual, target in zip(mins, SPEC["bbox_exact"]["min"]):
        if abs(float(actual) - float(target)) > tol:
            return False
    for actual, target in zip(maxs, SPEC["bbox_exact"]["max"]):
        if abs(float(actual) - float(target)) > tol:
            return False
    return True


def check_csv(path):
    rows = parse_csv(path)
    if not rows or list(rows[0].keys()) != SPEC["csv_headers"]:
        return False
    if len(rows) != len(SPEC["zone_rows"]):
        return False
    total_area = 0.0
    for row, (zone_number, zone_name, expected_area, _) in zip(rows, SPEC["zone_rows"]):
        if row.get("ZoneNumber") != zone_number:
            return False
        if norm(row.get("ZoneName")) != norm(zone_name):
            return False
        try:
            area = float(str(row.get("Area", "")).strip())
        except Exception:
            return False
        if abs(area - expected_area) > SPEC["area_tolerance_m2"]:
            return False
        total_area += area
    low, high = SPEC["csv_total_area_range_m2"]
    return low <= total_area <= high


def evaluate():
    root = DESKTOP
    for rel, min_bytes in SPEC["required_outputs"].items():
        path = root / rel
        if not path.is_file() or path.stat().st_size < min_bytes:
            return False
    model = ifcopenshell.open(str(root / "result.ifc"))
    return check_ifc(model) and check_csv(root / "result.txt")


def main():
    try:
        finish(evaluate())
    except SystemExit:
        raise
    except Exception:
        finish(False)


if __name__ == "__main__":
    main()
