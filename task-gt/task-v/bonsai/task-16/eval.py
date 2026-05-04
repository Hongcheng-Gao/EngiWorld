#!/usr/bin/env python3
import csv
import re
from pathlib import Path


DESKTOP = Path("/home/user/Desktop")

REQUIRED_OUTPUTS = ("result.ifc", "result.csv")
CSV_HEADERS = ("GlobalId", "Class", "TypeName", "Width", "Height", "HostWall")
EXPECTED_ROWS = [
    {"Class": "IfcDoor", "TypeName": "DoorType-1000", "Width": 1.0, "Height": 2.1, "HostWall": "Wall-S"},
    {"Class": "IfcDoor", "TypeName": "DoorType-1000", "Width": 1.0, "Height": 2.1, "HostWall": "Wall-N"},
    {"Class": "IfcWindow", "TypeName": "WindowType-1200", "Width": 1.2, "Height": 1.2, "HostWall": "Wall-N"},
    {"Class": "IfcWindow", "TypeName": "WindowType-1200", "Width": 1.2, "Height": 1.2, "HostWall": "Wall-N"},
    {"Class": "IfcWindow", "TypeName": "WindowType-1000", "Width": 1.0, "Height": 1.2, "HostWall": "Wall-E"},
]
WIDTH_HEIGHT_TOLERANCE = 0.05
FORBIDDEN_CLASSES = ("IfcBuildingElementProxy", "IfcFurnishingElement")


def emit(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def norm(value):
    return re.sub(r"\s+", " ", str(value or "").strip())


def parse_float(value):
    text = str(value).strip().replace(" ", "")
    if text.count(",") == 1 and text.count(".") == 0:
        text = text.replace(",", ".")
    else:
        text = text.replace(",", "")
    return float(text)


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(CSV_HEADERS):
            return None
        return [row for row in reader if any(str(value).strip() for value in row.values())]


def class_count(model, ifc_class):
    return len(model.by_type(ifc_class))


def wall_name_for_filled_element(model):
    opening_to_wall = {}
    for rel in model.by_type("IfcRelVoidsElement"):
        wall = getattr(rel, "RelatingBuildingElement", None)
        opening = getattr(rel, "RelatedOpeningElement", None)
        if wall is not None and opening is not None and wall.is_a("IfcWall"):
            opening_to_wall[opening.id()] = norm(getattr(wall, "Name", ""))

    element_to_wall = {}
    for rel in model.by_type("IfcRelFillsElement"):
        element = getattr(rel, "RelatedBuildingElement", None)
        opening = getattr(rel, "RelatingOpeningElement", None)
        if element is not None and opening is not None:
            host = opening_to_wall.get(opening.id())
            if host:
                element_to_wall[getattr(element, "GlobalId", "")] = host
    return element_to_wall


def check_ifc(path):
    import ifcopenshell

    model = ifcopenshell.open(str(path))
    if model.schema.upper() != "IFC4":
        return None
    expected_counts = {
        "IfcProject": 1,
        "IfcBuildingStorey": 1,
        "IfcWall": 4,
        "IfcSlab": 1,
        "IfcDoor": 2,
        "IfcWindow": 3,
        "IfcOpeningElement": 5,
        "IfcRelVoidsElement": 5,
        "IfcRelFillsElement": 5,
    }
    for ifc_class, expected in expected_counts.items():
        if class_count(model, ifc_class) != expected:
            return None
    for ifc_class in FORBIDDEN_CLASSES:
        if class_count(model, ifc_class) != 0:
            return None
    return model


def check_csv(rows, model):
    if rows is None or len(rows) != len(EXPECTED_ROWS):
        return False

    products = {}
    for ifc_class in ("IfcDoor", "IfcWindow"):
        for product in model.by_type(ifc_class):
            products[getattr(product, "GlobalId", "")] = product
    element_to_wall = wall_name_for_filled_element(model)

    actual_signatures = []
    seen_global_ids = set()
    for row in rows:
        gid = norm(row.get("GlobalId"))
        if gid in seen_global_ids or gid not in products:
            return False
        seen_global_ids.add(gid)
        product = products[gid]
        if row.get("Class") != product.is_a():
            return False
        if norm(row.get("HostWall")) != element_to_wall.get(gid):
            return False
        try:
            width = parse_float(row.get("Width"))
            height = parse_float(row.get("Height"))
        except Exception:
            return False
        actual_signatures.append(
            {
                "Class": product.is_a(),
                "TypeName": norm(row.get("TypeName")),
                "Width": width,
                "Height": height,
                "HostWall": norm(row.get("HostWall")),
            }
        )

    unmatched = actual_signatures[:]
    for expected in EXPECTED_ROWS:
        found_at = None
        for index, actual in enumerate(unmatched):
            if actual["Class"] != expected["Class"]:
                continue
            if actual["TypeName"] != expected["TypeName"]:
                continue
            if actual["HostWall"] != expected["HostWall"]:
                continue
            if abs(actual["Width"] - expected["Width"]) > WIDTH_HEIGHT_TOLERANCE:
                continue
            if abs(actual["Height"] - expected["Height"]) > WIDTH_HEIGHT_TOLERANCE:
                continue
            found_at = index
            break
        if found_at is None:
            return False
        unmatched.pop(found_at)
    return not unmatched


def main():
    try:
        root = DESKTOP
        if not root.is_dir():
            emit(False)
        for name in REQUIRED_OUTPUTS:
            path = root / name
            if not path.is_file() or path.stat().st_size == 0:
                emit(False)
        model = check_ifc(root / "result.ifc")
        if model is None:
            emit(False)
        rows = read_csv(root / "result.csv")
        emit(check_csv(rows, model))
    except SystemExit:
        raise
    except Exception:
        emit(False)


if __name__ == "__main__":
    main()
