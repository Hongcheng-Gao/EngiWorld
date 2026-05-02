#!/usr/bin/env python3
import csv
import re
from pathlib import Path

import ifcopenshell


DESKTOP = Path("C:/Users/Administrator/Desktop")


SPEC = {
    "required_outputs": {"result.ifc": 500, "result.txt": 20},
    "schema": "IFC4",
    "storey_count": 1,
    "zone_rows": [
        ("Z01", "ENTRY", 9.0),
        ("Z02", "LIVING-DINING", 24.0),
        ("Z03", "KITCHEN", 9.0),
        ("Z04", "BED-1", 12.0),
        ("Z05", "BED-2", 12.0),
        ("Z06", "BATH", 4.0),
        ("Z07", "LAUNDRY", 3.0),
        ("Z08", "COURTYARD", 18.0),
    ],
    "area_tolerance_m2": 0.10,
    "indoor_area_range_m2": (65.0, 110.0),
    "bedroom_area_range_m2": (8.0, 16.0),
    "courtyard_area_range_m2": (14.0, 24.0),
    "min_roof_entities": 1,
    "min_wall_entities": 8,
    "csv_headers": ["ZoneNumber", "ZoneName", "Area"],
}


def finish(ok):
    print("true" if ok else "false")
    raise SystemExit(0)


def norm(value):
    return re.sub(r"\s+", " ", str(value or "").replace("_", "-").strip()).upper()


def header_key(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def unique_global_ids(model):
    gids = [e.GlobalId for e in model.by_type("IfcRoot") if getattr(e, "GlobalId", None)]
    return len(gids) == len(set(gids))


def property_value(obj, prop_name):
    for rel in getattr(obj, "IsDefinedBy", None) or []:
        prop_def = getattr(rel, "RelatingPropertyDefinition", None)
        if not prop_def or not prop_def.is_a("IfcPropertySet"):
            continue
        for prop in prop_def.HasProperties or []:
            if getattr(prop, "Name", None) != prop_name:
                continue
            nominal = getattr(prop, "NominalValue", None)
            return getattr(nominal, "wrappedValue", nominal)
    return None


def quantity_area(obj):
    for rel in getattr(obj, "IsDefinedBy", None) or []:
        prop_def = getattr(rel, "RelatingPropertyDefinition", None)
        if not prop_def or not prop_def.is_a("IfcElementQuantity"):
            continue
        for quantity in prop_def.Quantities or []:
            if quantity.Name in {"NetFloorArea", "GrossFloorArea", "Area"} and hasattr(quantity, "AreaValue"):
                return float(quantity.AreaValue)
    return None


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


def space_records(model):
    records = {}
    for space in model.by_type("IfcSpace"):
        name = norm(getattr(space, "Name", ""))
        records[name] = {
            "entity": space,
            "number": str(property_value(space, "Reference") or getattr(space, "LongName", "") or ""),
            "area": quantity_area(space),
        }
    return records


def parse_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    if not rows:
        return None, None
    headers = list(rows[0].keys())
    return headers, rows


def check_ifc(model):
    if not str(getattr(model, "schema", "")).upper().startswith(SPEC["schema"]):
        return False
    if not unique_global_ids(model):
        return False
    if len(model.by_type("IfcBuildingStorey")) != SPEC["storey_count"]:
        return False
    if len(model.by_type("IfcSpace")) != len(SPEC["zone_rows"]):
        return False
    if len(model.by_type("IfcWall")) < SPEC["min_wall_entities"]:
        return False
    if len(model.by_type("IfcRoof")) < SPEC["min_roof_entities"]:
        return False
    storey = model.by_type("IfcBuildingStorey")[0]
    records = space_records(model)
    expected_names = [row[1] for row in SPEC["zone_rows"]]
    if set(records) != {norm(name) for name in expected_names}:
        return False
    indoor_total = 0.0
    for number, name, expected_area in SPEC["zone_rows"]:
        rec = records[norm(name)]
        if rec["number"] != number:
            return False
        if rec["area"] is None or abs(rec["area"] - expected_area) > SPEC["area_tolerance_m2"]:
            return False
        if parent_storey(rec["entity"]) is None or parent_storey(rec["entity"]).id() != storey.id():
            return False
        if name.startswith("BED-"):
            low, high = SPEC["bedroom_area_range_m2"]
            if not (low <= rec["area"] <= high):
                return False
            indoor_total += rec["area"]
        elif name == "COURTYARD":
            low, high = SPEC["courtyard_area_range_m2"]
            if not (low <= rec["area"] <= high):
                return False
        else:
            indoor_total += rec["area"]
    low, high = SPEC["indoor_area_range_m2"]
    return low <= indoor_total <= high


def check_csv(path, model):
    headers, rows = parse_csv(path)
    if headers is None:
        return False
    if [header_key(h) for h in headers] != [header_key(h) for h in SPEC["csv_headers"]]:
        return False
    if len(rows) != len(SPEC["zone_rows"]):
        return False
    ifc_records = space_records(model)
    for csv_row, expected in zip(rows, SPEC["zone_rows"]):
        number, name, expected_area = expected
        if csv_row.get("ZoneNumber") != number:
            return False
        if norm(csv_row.get("ZoneName")) != norm(name):
            return False
        try:
            csv_area = float(str(csv_row.get("Area", "")).strip())
        except Exception:
            return False
        if abs(csv_area - expected_area) > SPEC["area_tolerance_m2"]:
            return False
        if abs(csv_area - ifc_records[norm(name)]["area"]) > SPEC["area_tolerance_m2"]:
            return False
    return True


def evaluate():
    root = DESKTOP
    for rel, min_bytes in SPEC["required_outputs"].items():
        path = root / rel
        if not path.is_file() or path.stat().st_size < min_bytes:
            return False
    model = ifcopenshell.open(str(root / "result.ifc"))
    return check_ifc(model) and check_csv(root / "result.txt", model)


def main():
    try:
        finish(evaluate())
    except SystemExit:
        raise
    except Exception:
        finish(False)


if __name__ == "__main__":
    main()
