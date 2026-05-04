#!/usr/bin/env python3
import re
from pathlib import Path


DESKTOP = Path("/home/user/Desktop")

REQUIRED_OUTPUT = "result.ifc"
SPACE_NAMES = ("Unit A", "Unit B", "Unit C")
WALL_NAMES = ("Shell-S", "Shell-N", "Shell-W", "Shell-E", "Party-AB", "Party-BC")
FORBIDDEN_CLASSES = (
    "IfcBuildingElementProxy",
    "IfcFurnishingElement",
    "IfcDoor",
    "IfcWindow",
    "IfcOpeningElement",
    "IfcRelVoidsElement",
    "IfcRelFillsElement",
)


def emit(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def norm(value):
    return re.sub(r"\s+", " ", str(value or "").replace("_", " ").replace("-", " ").strip()).upper()


def class_count(model, ifc_class):
    return len(model.by_type(ifc_class))


def check_names(entities, expected):
    return {norm(getattr(entity, "Name", "")) for entity in entities} == {norm(name) for name in expected}


def check_ifc(path):
    import ifcopenshell

    model = ifcopenshell.open(str(path))
    if model.schema.upper() != "IFC4":
        return False
    expected_counts = {
        "IfcProject": 1,
        "IfcBuildingStorey": 1,
        "IfcSpace": 3,
        "IfcWall": 6,
        "IfcSlab": 1,
    }
    for ifc_class, expected in expected_counts.items():
        if class_count(model, ifc_class) != expected:
            return False
    for ifc_class in FORBIDDEN_CLASSES:
        if class_count(model, ifc_class) != 0:
            return False
    if not check_names(model.by_type("IfcSpace"), SPACE_NAMES):
        return False
    if not check_names(model.by_type("IfcWall"), WALL_NAMES):
        return False
    party_walls = [wall for wall in model.by_type("IfcWall") if norm(getattr(wall, "Name", "")).startswith("PARTY")]
    return len(party_walls) == 2


def main():
    try:
        root = DESKTOP
        path = root / REQUIRED_OUTPUT
        emit(root.is_dir() and path.is_file() and path.stat().st_size > 0 and check_ifc(path))
    except SystemExit:
        raise
    except Exception:
        emit(False)


if __name__ == "__main__":
    main()
