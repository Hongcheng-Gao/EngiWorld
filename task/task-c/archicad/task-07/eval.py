#!/usr/bin/env python3
import re
from pathlib import Path

import ifcopenshell


DESKTOP = Path("C:/Users/Administrator/Desktop")


SPEC = {
    "required_outputs": {"result.ifc": 500},
    "schema": "IFC4",
    "storey_count": 3,
    "min_counts": {"IfcSlab": 3, "IfcRoof": 1, "IfcStair": 1},
    "area_tolerance_m2": 0.10,
    "group_ranges_m2": {"GROUND": (78.0, 80.0), "LEVEL-1": (76.5, 78.5), "LEVEL-2": (84.0, 86.0)},
    "zone_rows": [
        ("G-RECEPTION", 20.0, "GROUND"),
        ("G-MEETING", 20.0, "GROUND"),
        ("G-CORRIDOR", 30.0, "GROUND"),
        ("G-STAIR", 9.0, "GROUND"),
        ("1-OFFICE-1", 20.0, "LEVEL-1"),
        ("1-OFFICE-2", 20.0, "LEVEL-1"),
        ("1-CORRIDOR", 30.0, "LEVEL-1"),
        ("1-WC", 7.5, "LEVEL-1"),
        ("2-OFFICE-3", 20.0, "LEVEL-2"),
        ("2-OFFICE-4", 20.0, "LEVEL-2"),
        ("2-CORRIDOR", 30.0, "LEVEL-2"),
        ("2-TERRACE", 15.0, "LEVEL-2"),
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
        records[norm(getattr(space, "Name", ""))] = {"area": quantity_area(space), "storey_id": parent_storey_id(space)}
    return records


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
    if set(records) != {norm(name) for name, _, _ in SPEC["zone_rows"]}:
        return False
    group_storeys = {group: set() for group in SPEC["group_ranges_m2"]}
    group_totals = {group: 0.0 for group in SPEC["group_ranges_m2"]}
    for name, expected_area, group in SPEC["zone_rows"]:
        rec = records[norm(name)]
        if rec["storey_id"] is None:
            return False
        if rec["area"] is None or abs(rec["area"] - expected_area) > SPEC["area_tolerance_m2"]:
            return False
        group_storeys[group].add(rec["storey_id"])
        group_totals[group] += rec["area"]
    if any(len(ids) != 1 for ids in group_storeys.values()):
        return False
    if len({next(iter(ids)) for ids in group_storeys.values()}) != len(group_storeys):
        return False
    for group, total in group_totals.items():
        low, high = SPEC["group_ranges_m2"][group]
        if not (low <= total <= high):
            return False
    return True


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
