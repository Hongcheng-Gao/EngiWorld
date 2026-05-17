#!/usr/bin/env python3
import csv
import re
from pathlib import Path
DESKTOP = Path("C:/Users/Administrator/Desktop")

import ifcopenshell
import ifcopenshell.geom


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
        "IfcSpace": 3,
        "IfcWall": 4,
        "IfcSlab": 1,
        "IfcRoof": 1,
        "IfcDoor": 3,
        "IfcColumn": 12,
        "IfcBeam": 17,
    },
    "forbidden_counts": {
        "IfcWindow": 0,
        "IfcStair": 0,
        "IfcCurtainWall": 0,
        "IfcBuildingElementProxy": 0,
    },
    "bbox_tolerance": 0.35,
    "bbox": {"IfcWall": [0, 0, 0, 24, 14, 5.0], "IfcSlab": [0, 0, 0, 24, 14, 0.25], "IfcRoof": [0, 0, 5.05, 24, 14, 5.25], "IfcColumn": [0, 0, 0, 24.35, 14.35, 5.0], "IfcBeam": [-0.1, 0, 4.4, 24.15, 14.4, 4.85], "IfcSpace": [0, 0, 0, 24, 14, 4.8]},
    "space_token_counts": {"office": 1, "service": 1, "hall": 1},
    "csv_expected": {"Columns": 12, "Beams": 17},
    "csv_ifc_map": {"Columns": "IfcColumn", "Beams": "IfcBeam"},
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
    if [cell.strip() for cell in rows[0]] != ["category", "count"]:
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


def check_csv(model, csv_path):
    parsed = parse_csv_rows(csv_path)
    if parsed != SPEC["csv_expected"]:
        return False
    for label, ifc_class in SPEC["csv_ifc_map"].items():
        if parsed[label] != entity_count(model, ifc_class):
            return False
    return True




def geometry_settings():
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    return settings


def combined_bbox(model, ifc_class):
    xs, ys, zs = [], [], []
    settings = geometry_settings()
    for element in model.by_type(ifc_class):
        try:
            shape = ifcopenshell.geom.create_shape(settings, element)
            verts = shape.geometry.verts
        except Exception:
            continue
        xs.extend(verts[0::3])
        ys.extend(verts[1::3])
        zs.extend(verts[2::3])
    if not xs:
        return None
    return [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)]


def bbox_close(actual, expected, tolerance):
    return actual is not None and all(abs(a - e) <= tolerance for a, e in zip(actual, expected))


def check_geometry(model):
    tolerance = SPEC.get("bbox_tolerance", 0.35)
    for ifc_class, expected in SPEC.get("bbox", {}).items():
        if not bbox_close(combined_bbox(model, ifc_class), expected, tolerance):
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
