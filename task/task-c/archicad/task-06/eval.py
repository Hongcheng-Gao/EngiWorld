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

    "min_counts": {"IfcSlab": 1, "IfcRoof": 1},

    "area_tolerance_m2": 0.10,

    "classroom_area_range_m2": (89.0, 91.0),

    "total_area_range_m2": (241.0, 243.0),

    "csv_headers": ["ZoneNumber", "ZoneName", "Area", "Storey"],

    "zone_rows": [

        ("01", "CLASSROOM-1", 22.5, "GROUND"),

        ("02", "CLASSROOM-2", 22.5, "GROUND"),

        ("03", "CLASSROOM-3", 22.5, "GROUND"),

        ("04", "CLASSROOM-4", 22.5, "GROUND"),

        ("05", "PLAY-HALL", 64.0, "GROUND"),

        ("06", "NAP", 16.0, "GROUND"),

        ("07", "STAFF", 16.0, "GROUND"),

        ("08", "WC-CHILD", 10.0, "GROUND"),

        ("09", "WC-STAFF", 6.0, "GROUND"),

        ("10", "YARD", 40.0, "GROUND"),

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

    storey = model.by_type("IfcBuildingStorey")[0]

    records = space_records(model)

    if set(records) != {norm(name) for _, name, _, _ in SPEC["zone_rows"]}:

        return False

    classroom_area = 0.0

    total_area = 0.0

    for _, name, expected_area, _ in SPEC["zone_rows"]:

        rec = records[norm(name)]

        if rec["area"] is None or abs(rec["area"] - expected_area) > SPEC["area_tolerance_m2"]:

            return False

        parent = parent_storey(rec["entity"])

        if parent is None or parent.id() != storey.id():

            return False

        total_area += rec["area"]

        if name.startswith("CLASSROOM-"):

            classroom_area += rec["area"]

    class_low, class_high = SPEC["classroom_area_range_m2"]

    total_low, total_high = SPEC["total_area_range_m2"]

    return class_low <= classroom_area <= class_high and total_low <= total_area <= total_high





def check_csv(path, model):

    rows = parse_csv(path)

    if not rows or list(rows[0].keys()) != SPEC["csv_headers"]:

        return False

    if len(rows) != len(SPEC["zone_rows"]):

        return False

    records = space_records(model)

    for row, (number, name, expected_area, storey) in zip(rows, SPEC["zone_rows"]):

        if row.get("ZoneNumber") != number:

            return False

        if norm(row.get("ZoneName")) != norm(name) or norm(row.get("Storey")) != norm(storey):

            return False

        try:

            csv_area = float(str(row.get("Area", "")).strip())

        except Exception:

            return False

        if abs(csv_area - expected_area) > SPEC["area_tolerance_m2"]:

            return False

        if abs(csv_area - records[norm(name)]["area"]) > SPEC["area_tolerance_m2"]:

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

