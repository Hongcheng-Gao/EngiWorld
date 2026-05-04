#!/usr/bin/env python3
import re
from pathlib import Path


DESKTOP = Path("/home/user/Desktop")

REQUIRED_OUTPUTS = ("result.ifc",)
SPACE_NAMES = ("Living", "Bed 1", "Bed 2", "Bath", "Kitchen")
WALL_NAMES = ("Shell-S", "Shell-N", "Shell-W", "Shell-E", "Part-1", "Part-2", "Part-3")
FORBIDDEN_CLASSES = ("IfcBuildingElementProxy", "IfcFurnishingElement")


def emit(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def norm(value):
    return re.sub(r"\s+", " ", str(value or "").replace("_", " ").replace("-", " ").strip()).upper()


def class_count(model, ifc_class):
    return len(model.by_type(ifc_class))


def filled_element_count(model):
    filled_ids = set()
    opening_ids = set()
    for rel in model.by_type("IfcRelFillsElement"):
        element = getattr(rel, "RelatedBuildingElement", None)
        opening = getattr(rel, "RelatingOpeningElement", None)
        if element is None or opening is None:
            return None
        if not (element.is_a("IfcDoor") or element.is_a("IfcWindow")):
            return None
        filled_ids.add(element.id())
        opening_ids.add(opening.id())

    void_opening_ids = set()
    for rel in model.by_type("IfcRelVoidsElement"):
        wall = getattr(rel, "RelatingBuildingElement", None)
        opening = getattr(rel, "RelatedOpeningElement", None)
        if wall is None or opening is None or not wall.is_a("IfcWall"):
            return None
        void_opening_ids.add(opening.id())

    if opening_ids != void_opening_ids:
        return None
    return len(filled_ids)


def check_ifc(path):
    import ifcopenshell

    model = ifcopenshell.open(str(path))
    if model.schema.upper() != "IFC4":
        return False
    expected_counts = {
        "IfcProject": 1,
        "IfcBuildingStorey": 1,
        "IfcSpace": 5,
        "IfcWall": 7,
        "IfcSlab": 1,
        "IfcDoor": 3,
        "IfcWindow": 2,
        "IfcOpeningElement": 5,
        "IfcRelVoidsElement": 5,
        "IfcRelFillsElement": 5,
    }
    for ifc_class, expected in expected_counts.items():
        if class_count(model, ifc_class) != expected:
            return False
    for ifc_class in FORBIDDEN_CLASSES:
        if class_count(model, ifc_class) != 0:
            return False

    actual_space_names = {norm(getattr(space, "Name", "")) for space in model.by_type("IfcSpace")}
    if actual_space_names != {norm(name) for name in SPACE_NAMES}:
        return False
    actual_wall_names = {norm(getattr(wall, "Name", "")) for wall in model.by_type("IfcWall")}
    if actual_wall_names != {norm(name) for name in WALL_NAMES}:
        return False
    return filled_element_count(model) == 5


def main():
    try:
        root = DESKTOP
        if not root.is_dir():
            emit(False)
        for name in REQUIRED_OUTPUTS:
            path = root / name
            if not path.is_file() or path.stat().st_size == 0:
                emit(False)
        emit(check_ifc(root / "result.ifc"))
    except SystemExit:
        raise
    except Exception:
        emit(False)


if __name__ == "__main__":
    main()
