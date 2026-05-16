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

    "min_counts": {"IfcWall": 4, "IfcSlab": 2, "IfcRoof": 1, "IfcWindow": 6},

    "bbox_exact": {"min": [0.0, 0.0, 0.0], "max": [29.0, 13.0, 3.6]},

    "bbox_tolerance": 0.5,

    "csv_headers": ["ZoneNumber", "ZoneName", "Area"],

    "area_tolerance_m2": 0.10,

    "csv_total_area_range_m2": (259.0, 261.0),

    "zone_rows": [

        ("Z01", "LINK", 20.0),

        ("Z02", "HALL", 84.0),

        ("Z03", "MEETING-1", 48.0),

        ("Z04", "MEETING-2", 48.0),

        ("Z05", "STORE", 12.0),

        ("Z06", "WC", 12.0),

        ("Z07", "COURTYARD", 36.0),

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

    spaces = model.by_type("IfcSpace")

    if len(spaces) != len(SPEC["zone_rows"]):

        return False

    for cls, minimum in SPEC["min_counts"].items():

        if len(model.by_type(cls)) < minimum:

            return False

    if {norm(getattr(space, "Name", "")) for space in spaces} != {norm(name) for _, name, _ in SPEC["zone_rows"]}:

        return False

    storey = model.by_type("IfcBuildingStorey")[0]

    for space in spaces:

        parent = parent_storey(space)

        if parent is None or parent.id() != storey.id():

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

    for row, (zone_number, zone_name, expected_area) in zip(rows, SPEC["zone_rows"]):

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

