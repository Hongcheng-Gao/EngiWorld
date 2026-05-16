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

    "min_counts": {"IfcWall": 4, "IfcSlab": 1, "IfcRoof": 1},

    "bbox_exact": {"min": [0.0, 0.0, 0.0], "max": [30.0, 10.0, 3.3]},

    "bbox_tolerance": 0.5,

    "csv_headers": ["Status", "Category", "Quantity"],

    "quantity_tolerance": 0.10,

    "csv_total_range": (79.4, 79.6),

    "space_names": [

        "CLASSROOM-1",

        "CLASSROOM-2",

        "CLASSROOM-3",

        "CLASSROOM-4",

        "CORRIDOR",

        "CONNECTOR",

        "STORE",

    ],

    "csv_rows": [

        ("DEMOLISH", "PartitionWalls", 18.6),

        ("DEMOLISH", "OldCorridorSegment", 9.2),

        ("NEW", "ConnectorWalls", 24.4),

        ("NEW", "ClassroomPartitions", 16.8),

        ("NEW", "GlazedLink", 10.5),

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

    if len(spaces) != len(SPEC["space_names"]):

        return False

    for cls, minimum in SPEC["min_counts"].items():

        if len(model.by_type(cls)) < minimum:

            return False

    if {norm(getattr(space, "Name", "")) for space in spaces} != {norm(name) for name in SPEC["space_names"]}:

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

    if len(rows) != len(SPEC["csv_rows"]):

        return False

    total = 0.0

    for row, (status, category, quantity) in zip(rows, SPEC["csv_rows"]):

        if norm(row.get("Status")) != norm(status):

            return False

        if norm(row.get("Category")) != norm(category):

            return False

        try:

            actual = float(str(row.get("Quantity", "")).strip())

        except Exception:

            return False

        if abs(actual - quantity) > SPEC["quantity_tolerance"]:

            return False

        total += actual

    low, high = SPEC["csv_total_range"]

    return low <= total <= high





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

