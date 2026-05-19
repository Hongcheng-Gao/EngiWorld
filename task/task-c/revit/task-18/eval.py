#!/usr/bin/env python3

import csv

import re

from pathlib import Path

DESKTOP = Path("C:/Users/user/Desktop")



import ifcopenshell





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

        "IfcBuildingStorey": 1,

        "IfcSlab": 1,

        "IfcColumn": 15,

        "IfcBeam": 22,

    },

    "forbidden_counts": {

        "IfcSpace": 0,

        "IfcWall": 0,

        "IfcRoof": 0,

        "IfcDoor": 0,

        "IfcWindow": 0,

        "IfcStair": 0,

        "IfcCurtainWall": 0,

        "IfcBuildingElementProxy": 0,

    },

    "csv_headers": ["category", "count"],

    "csv_expected": {"columns": 15, "beams": 22},

    "csv_ifc_map": {"columns": "IfcColumn", "beams": "IfcBeam"},

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

        raise ValueError("not integer")

    return int(text)





def parse_csv_rows(path):

    rows = list(csv.reader(path.read_text(encoding="utf-8-sig").splitlines()))

    if not rows:

        return None

    headers = [cell.strip() for cell in rows[0]]

    if headers != SPEC["csv_headers"]:

        return None

    body = [row for row in rows[1:] if any(cell.strip() for cell in row)]

    if len(body) != len(SPEC["csv_expected"]):

        return None

    parsed = {}

    for row in body:

        if len(row) != 2:

            return None

        category = norm(row[0])

        if category in parsed:

            return None

        parsed[category] = parse_int(row[1])

    return parsed





def check_counts(model):

    for ifc_class, expected in SPEC["counts"].items():

        if entity_count(model, ifc_class) != expected:

            return False

    for ifc_class, expected in SPEC["forbidden_counts"].items():

        if entity_count(model, ifc_class) != expected:

            return False

    return True





def check_csv(model, csv_path):

    parsed = parse_csv_rows(csv_path)

    if parsed is None or parsed != SPEC["csv_expected"]:

        return False

    for category, ifc_class in SPEC["csv_ifc_map"].items():

        if parsed[category] != entity_count(model, ifc_class):

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

