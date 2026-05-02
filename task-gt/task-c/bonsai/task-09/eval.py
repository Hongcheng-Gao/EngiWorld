#!/usr/bin/env python3
import csv
import re
from pathlib import Path

import ifcopenshell


DESKTOP = Path("/home/user/Desktop")
import ifcopenshell.geom
import ifcopenshell.util.unit


SPEC = {
    "required_outputs": ("result.ifc", "result.csv"),
    "min_ifc_bytes": 500,
    "schema": "IFC4",
    "counts": {
        "IfcProject": 1,
        "IfcSite": 1,
        "IfcBuilding": 1,
        "IfcBuildingStorey": 1,
        "IfcSpace": 2,
        "IfcWall": 5,
        "IfcSlab": 1,
        "IfcDoor": 2,
        "IfcWindow": 3,
        "IfcOpeningElement": 5,
        "IfcRelVoidsElement": 5,
        "IfcRelFillsElement": 5,
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
    "spaces": {"Open Office": (6.6, 5.6), "Meeting": (2.7, 5.6)},
    "space_height_m": 3.0,
    "slab": ("Ground Slab", (10.0, 6.0, 0.2), 60.0),
    "wall_lengths": {
        "South Wall": 10.0,
        "East Wall": 6.0,
        "North Wall": 10.0,
        "West Wall": 6.0,
        "Meeting Partition": 5.6,
    },
    "door_widths": {"Entry Door": 0.9, "Meeting Door": 0.85},
    "window_widths": {"North Window": 1.5, "Meeting Window": 1.2, "East Window": 1.3},
    "csv_headers": ["GlobalId", "Class", "Name", "Storey", "QuantityValue"],
    "csv_row_count": 11,
    "linear_tolerance_m": 0.08,
    "height_tolerance_m": 0.05,
    "quantity_tolerance": 0.02,
}


def emit(ok):
    print("true" if ok else "false")
    raise SystemExit(0)


def clean_name(value):
    return re.sub(r"\s+", " ", str(value or "").strip())


def header_key(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def approx(actual, expected, tol):
    return actual is not None and abs(float(actual) - float(expected)) <= float(tol)


def unit_scale(model):
    try:
        return float(ifcopenshell.util.unit.calculate_unit_scale(model))
    except Exception:
        return 1.0


def parse_number(value):
    return float(str(value).strip())


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
        headers = f.seek(0) or next(csv.reader(f), [])
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


def check_spaces_and_geometry(model):
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
    slab = model.by_type("IfcSlab")[0]
    if clean_name(slab.Name) != SPEC["slab"][0]:
        return False
    bbox = shape_bbox(slab)
    if bbox is None:
        return False
    sx, sy, sz = span(bbox)
    return dimensions_match((sx, sy), SPEC["slab"][1][:2], SPEC["linear_tolerance_m"]) and approx(sz, SPEC["slab"][1][2], SPEC["height_tolerance_m"])


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


def check_widths_and_openings(model):
    openings = set()
    for ifc_class, expected_by_name in (("IfcDoor", SPEC["door_widths"]), ("IfcWindow", SPEC["window_widths"])):
        elements = {clean_name(e.Name): e for e in model.by_type(ifc_class)}
        if set(elements) != set(expected_by_name):
            return False
        for name, expected_width in expected_by_name.items():
            if not approx(overall_width(elements[name], model), expected_width, SPEC["linear_tolerance_m"]):
                return False
            opening = fill_opening(elements[name])
            if opening is None or not opening_host(opening).is_a("IfcWall"):
                return False
            openings.add(opening.id())
    return len(openings) == SPEC["counts"]["IfcOpeningElement"]


def check_csv_export(root, model):
    headers, rows = read_csv(root / "result.csv")
    if [header_key(h) for h in headers] != [header_key(h) for h in SPEC["csv_headers"]]:
        return False
    if len(rows) != SPEC["csv_row_count"]:
        return False
    by_gid = {e.GlobalId: e for cls in ("IfcWall", "IfcSlab", "IfcDoor", "IfcWindow") for e in model.by_type(cls)}
    if set(row.get("GlobalId", "") for row in rows) != set(by_gid):
        return False
    expected_quantities = {}
    expected_quantities.update(SPEC["wall_lengths"])
    expected_quantities[SPEC["slab"][0]] = SPEC["slab"][2]
    expected_quantities.update(SPEC["door_widths"])
    expected_quantities.update(SPEC["window_widths"])
    for row in rows:
        entity = by_gid.get(row.get("GlobalId", ""))
        if entity is None:
            return False
        name = clean_name(row.get("Name", ""))
        if name != clean_name(entity.Name):
            return False
        if row.get("Class", "") != entity.is_a():
            return False
        if clean_name(row.get("Storey", "")) != SPEC["storey_name"]:
            return False
        if name not in expected_quantities:
            return False
        if not approx(parse_number(row.get("QuantityValue", "")), expected_quantities[name], SPEC["quantity_tolerance"]):
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
        and check_storey_assignment(model)
        and check_spaces_and_geometry(model)
        and check_widths_and_openings(model)
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
