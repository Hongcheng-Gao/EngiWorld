#!/usr/bin/env python3
import csv
import re
from pathlib import Path
DESKTOP = Path("C:/Users/Administrator/Desktop")

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
        "IfcSpace": 4,
        "IfcWall": 6,
        "IfcSlab": 1,
        "IfcRoof": 1,
        "IfcDoor": 3,
        "IfcWindow": 6,
        "IfcCurtainWall": 1,
    },
    "forbidden_counts": {
        "IfcStair": 0,
        "IfcColumn": 0,
        "IfcBeam": 0,
        "IfcBuildingElementProxy": 0,
    },
    "space_token_counts": {"cafe": 1, "storage": 1, "prep": 1, "toilet": 1},
    "csv_expected": {
        "front curtain glazing": 4,
        "east side windows": 2,
        "entry glazed door": 1,
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
        raise ValueError("not integer")
    return int(text)


def parse_csv_rows(path):
    rows = list(csv.reader(path.read_text(encoding="utf-8-sig").splitlines()))
    if not rows:
        return None
    if [cell.strip() for cell in rows[0]] != ["type", "count"]:
        return None
    body = [row for row in rows[1:] if any(cell.strip() for cell in row)]
    if len(body) != len(SPEC["csv_expected"]):
        return None
    parsed = {}
    for row in body:
        if len(row) != 2:
            return None
        parsed[row[0].strip()] = parse_int(row[1])
    return parsed


def check_counts(model):
    for ifc_class, expected in SPEC["counts"].items():
        if entity_count(model, ifc_class) != expected:
            return False
    for ifc_class, expected in SPEC["forbidden_counts"].items():
        if entity_count(model, ifc_class) != expected:
            return False
    return True


def check_spaces(model):
    names = [norm(getattr(space, "Name", "") or getattr(space, "LongName", "")) for space in model.by_type("IfcSpace")]
    return all(sum(1 for name in names if token in name) >= minimum for token, minimum in SPEC["space_token_counts"].items())


def check_csv(csv_path):
    return parse_csv_rows(csv_path) == SPEC["csv_expected"]


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
        and check_csv(csv_path)
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
