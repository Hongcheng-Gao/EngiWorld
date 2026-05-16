#!/usr/bin/env python3

import csv

import re

from pathlib import Path

DESKTOP = Path("C:/Users/Administrator/Desktop")



import ifcopenshell

import ifcopenshell.geom

import numpy as np





SPEC = {

    "required_ifc": "result.ifc",

    "required_csv": "result.csv",

    "min_ifc_bytes": 500,

    "min_csv_bytes": 20,

    "schema": "IFC4",

    "counts": {

        "IfcProject": 1,

        "IfcSite": 1,

        "IfcBuilding": 1,

        "IfcBuildingStorey": 2,

        "IfcSpace": 2,

        "IfcColumn": 20,

        "IfcBeam": 31,

        "IfcSlab": 2,

        "IfcWall": 4,

        "IfcRoof": 1,

    },

    "min_counts": {

        "IfcStair": 1,

        "IfcDoor": 2,

        "IfcWindow": 5,

    },

    "forbidden_counts": {"IfcBuildingElementProxy": 0},

    "required_space_tokens": ["storage", "office"],

    "bbox_ranges_m": {"x": (28.0, 32.0), "y": (17.0, 19.5), "z": (5.8, 7.0)},

    "csv_headers": ["category", "count"],

    "csv_expected": {"columns": 20, "beams": 31, "slabs": 2, "walls": 4},

    "csv_ifc_map": {

        "columns": "IfcColumn",

        "beams": "IfcBeam",

        "slabs": "IfcSlab",

        "walls": "IfcWall",

    },

}





def finish(ok):

    print("True" if ok else "False")

    raise SystemExit(0)





def norm(value):

    text = str(value or "").replace("_", " ").replace("-", " ").lower()

    return re.sub(r"\s+", " ", text).strip()





def entity_count(model, ifc_class):

    return len(model.by_type(ifc_class))





def unique_global_ids(model):

    gids = [e.GlobalId for e in model.by_type("IfcRoot") if getattr(e, "GlobalId", None)]

    return len(gids) == len(set(gids))





def parse_int(value):

    text = str(value).strip().replace(",", "")

    if not re.fullmatch(r"[+-]?\d+", text):

        raise ValueError("not an integer")

    return int(text)





def parse_csv_counts(path):

    with path.open("r", encoding="utf-8-sig", newline="") as handle:

        rows = list(csv.reader(handle))

    if not rows:

        return None

    headers = [cell.strip() for cell in rows[0]]

    if headers != SPEC["csv_headers"]:

        return None

    body = [row for row in rows[1:] if any(cell.strip() for cell in row)]

    if len(body) != len(SPEC["csv_expected"]):

        return None

    result = {}

    for row in body:

        if len(row) != 2:

            return None

        category = norm(row[0])

        if category in result:

            return None

        result[category] = parse_int(row[1])

    return result





def check_counts(model):

    for ifc_class, expected in SPEC["counts"].items():

        if entity_count(model, ifc_class) != expected:

            return False

    for ifc_class, minimum in SPEC["min_counts"].items():

        if entity_count(model, ifc_class) < minimum:

            return False

    for ifc_class, expected in SPEC["forbidden_counts"].items():

        if entity_count(model, ifc_class) != expected:

            return False

    return True





def check_spaces(model):

    names = [norm(getattr(space, "Name", "") or getattr(space, "LongName", "")) for space in model.by_type("IfcSpace")]

    return all(any(token in name for name in names) for token in SPEC["required_space_tokens"])





def check_geometry(model):

    settings = ifcopenshell.geom.settings()

    try:

        settings.set(settings.USE_WORLD_COORDS, True)

    except Exception:

        pass

    records = []

    for product in model.by_type("IfcProduct"):

        if product.is_a("IfcOpeningElement") or not getattr(product, "Representation", None):

            continue

        try:

            shape = ifcopenshell.geom.create_shape(settings, product)

            verts = np.array(shape.geometry.verts, dtype=float).reshape(-1, 3)

        except Exception:

            continue

        if verts.size:

            records.append(verts)

    if not records:

        return False

    mins = np.min([verts.min(axis=0) for verts in records], axis=0)

    maxs = np.max([verts.max(axis=0) for verts in records], axis=0)

    spans = maxs - mins

    for axis, idx in (("x", 0), ("y", 1), ("z", 2)):

        low, high = SPEC["bbox_ranges_m"][axis]

        if not (low <= float(spans[idx]) <= high):

            return False

    return True





def check_csv(model, csv_path):

    csv_counts = parse_csv_counts(csv_path)

    if csv_counts != SPEC["csv_expected"]:

        return False

    for category, ifc_class in SPEC["csv_ifc_map"].items():

        if csv_counts[category] != entity_count(model, ifc_class):

            return False

    return True





def evaluate(result_dir):

    root = Path(result_dir)

    ifc_path = root / SPEC["required_ifc"]

    csv_path = root / SPEC["required_csv"]

    if not ifc_path.is_file() or ifc_path.stat().st_size < SPEC["min_ifc_bytes"]:

        return False

    if not csv_path.is_file() or csv_path.stat().st_size < SPEC["min_csv_bytes"]:

        return False

    model = ifcopenshell.open(str(ifc_path))

    return (

        str(getattr(model, "schema", "")).upper().startswith(SPEC["schema"])

        and unique_global_ids(model)

        and check_counts(model)

        and check_spaces(model)

        and check_geometry(model)

        and check_csv(model, csv_path)

    )





def main():

    try:

        finish(evaluate(DESKTOP))

    except SystemExit:

        raise

    except Exception:

        finish(False)





if __name__ == "__main__":

    main()

