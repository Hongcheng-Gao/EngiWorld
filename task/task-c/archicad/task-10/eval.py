#!/usr/bin/env python3
import re
from pathlib import Path

import ifcopenshell


DESKTOP = Path("C:/Users/Administrator/Desktop")


SPEC = {
    "required_outputs": {"result.ifc": 500},
    "schema": "IFC4",
    "storey_count": 1,
    "min_counts": {"IfcSlab": 1, "IfcRoof": 4},
    "area_tolerance_m2": 0.10,
    "guest_area_range_m2": (127.0, 129.0),
    "court_area_range_m2": (79.0, 81.0),
    "total_area_range_m2": (287.0, 289.0),
    "zone_rows": [
        ("GUEST-1", 20.0),
        ("GUEST-2", 20.0),
        ("GUEST-3", 24.0),
        ("GUEST-4", 24.0),
        ("GUEST-5", 20.0),
        ("GUEST-6", 20.0),
        ("RECEPTION", 28.0),
        ("LINEN", 12.0),
        ("LAUNDRY", 40.0),
        ("COURT", 80.0),
    ],
}


def finish(ok):
    print("True" if ok else "False")
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


def parent_storey(obj):
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
        records[norm(getattr(space, "Name", ""))] = {"entity": space, "area": quantity_area(space)}
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
    storey = model.by_type("IfcBuildingStorey")[0]
    records = space_records(model)
    if set(records) != {norm(name) for name, _ in SPEC["zone_rows"]}:
        return False
    guest_area = 0.0
    total_area = 0.0
    court_area = None
    for name, expected_area in SPEC["zone_rows"]:
        rec = records[norm(name)]
        if rec["area"] is None or abs(rec["area"] - expected_area) > SPEC["area_tolerance_m2"]:
            return False
        parent = parent_storey(rec["entity"])
        if parent is None or parent.id() != storey.id():
            return False
        total_area += rec["area"]
        if name.startswith("GUEST-"):
            guest_area += rec["area"]
        if name == "COURT":
            court_area = rec["area"]
    guest_low, guest_high = SPEC["guest_area_range_m2"]
    court_low, court_high = SPEC["court_area_range_m2"]
    total_low, total_high = SPEC["total_area_range_m2"]
    return (
        guest_low <= guest_area <= guest_high
        and court_area is not None
        and court_low <= court_area <= court_high
        and total_low <= total_area <= total_high
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
