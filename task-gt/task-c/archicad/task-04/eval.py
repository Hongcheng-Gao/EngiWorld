#!/usr/bin/env python3
import re
from pathlib import Path

import ifcopenshell


DESKTOP = Path("C:/Users/Administrator/Desktop")


SPEC = {
    "required_outputs": {"result.ifc": 500},
    "schema": "IFC4",
    "storey_count": 2,
    "min_counts": {"IfcSlab": 2, "IfcRoof": 1, "IfcStair": 1},
    "area_tolerance_m2": 0.10,
    "ground_area_range_m2": (72.0, 74.0),
    "upper_area_range_m2": (32.0, 34.0),
    "zone_rows": [
        ("L01", "G-LOBBY", 9.0, "GROUND"),
        ("L02", "G-READING", 48.0, "GROUND"),
        ("L03", "G-STACKS", 12.0, "GROUND"),
        ("L04", "G-WC", 4.0, "GROUND"),
        ("L05", "1-GALLERY", 15.0, "UPPER"),
        ("L06", "1-STUDY-1", 9.0, "UPPER"),
        ("L07", "1-STUDY-2", 9.0, "UPPER"),
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


def property_value(obj, prop_name):
    for rel in getattr(obj, "IsDefinedBy", None) or []:
        prop_def = getattr(rel, "RelatingPropertyDefinition", None)
        if not prop_def or not prop_def.is_a("IfcPropertySet"):
            continue
        for prop in prop_def.HasProperties or []:
            if getattr(prop, "Name", None) == prop_name:
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
        records[norm(getattr(space, "Name", ""))] = {
            "number": str(property_value(space, "Reference") or getattr(space, "LongName", "") or ""),
            "area": quantity_area(space),
            "storey_id": parent_storey_id(space),
        }
    return records


def in_range(value, key):
    low, high = SPEC[key]
    return low <= value <= high


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

    group_storeys = {"GROUND": set(), "UPPER": set()}
    group_totals = {"GROUND": 0.0, "UPPER": 0.0}
    for number, name, expected_area, group in SPEC["zone_rows"]:
        rec = records[norm(name)]
        if rec["number"] != number or rec["storey_id"] is None:
            return False
        if rec["area"] is None or abs(rec["area"] - expected_area) > SPEC["area_tolerance_m2"]:
            return False
        group_storeys[group].add(rec["storey_id"])
        group_totals[group] += rec["area"]
    if len(group_storeys["GROUND"]) != 1 or len(group_storeys["UPPER"]) != 1:
        return False
    if group_storeys["GROUND"] == group_storeys["UPPER"]:
        return False
    return in_range(group_totals["GROUND"], "ground_area_range_m2") and in_range(
        group_totals["UPPER"], "upper_area_range_m2"
    )


def evaluate():
    root = DESKTOP
    for rel, min_bytes in SPEC["required_outputs"].items():
        path = root / rel
        if not path.is_file() or path.stat().st_size < min_bytes:
            return False
    model = ifcopenshell.open(str(root / "result.ifc"))
    return check_ifc(model)


def main():
    try:
        finish(evaluate())
    except SystemExit:
        raise
    except Exception:
        finish(False)


if __name__ == "__main__":
    main()
