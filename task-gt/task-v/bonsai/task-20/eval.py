#!/usr/bin/env python3
import re
from pathlib import Path


DESKTOP = Path("/home/user/Desktop")

REQUIRED_OUTPUTS = ("result.ifc",)
STOREY_NAMES = ("Ground Floor", "First Floor")
SPACE_TO_STOREY = {
    "GF Living": "Ground Floor",
    "GF Kitchen": "Ground Floor",
    "FF Bed 1": "First Floor",
    "FF Bed 2": "First Floor",
}
WALL_NAMES = (
    "Ground Floor-S",
    "Ground Floor-N",
    "Ground Floor-W",
    "Ground Floor-E",
    "First Floor-S",
    "First Floor-N",
    "First Floor-W",
    "First Floor-E",
)
SLAB_NAMES = ("GF Slab", "FF Slab")
ROOF_NAMES = ("Main Roof", "Rear Roof")
WINDOW_NAMES = ("Upper North 1", "Upper North 2", "Upper East 1", "Upper East 2")
DOOR_NAMES = ("Main Entry",)
FORBIDDEN_CLASSES = ("IfcBuildingElementProxy", "IfcFurnishingElement")


def emit(ok):
    print("true" if ok else "false")
    raise SystemExit(0)


def norm(value):
    return re.sub(r"\s+", " ", str(value or "").replace("_", " ").replace("-", " ").strip()).upper()


def class_count(model, ifc_class):
    return len(model.by_type(ifc_class))


def name_set(entities):
    return {norm(getattr(entity, "Name", "")) for entity in entities}


def check_names(entities, expected):
    return name_set(entities) == {norm(name) for name in expected}


def space_storey_name(space):
    for rel in getattr(space, "Decomposes", []) or []:
        container = getattr(rel, "RelatingObject", None)
        if container is not None and container.is_a("IfcBuildingStorey"):
            return getattr(container, "Name", "")
    for rel in getattr(space, "ContainedInStructure", []) or []:
        container = getattr(rel, "RelatingStructure", None)
        if container is not None and container.is_a("IfcBuildingStorey"):
            return getattr(container, "Name", "")
    return ""


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
        "IfcBuildingStorey": 2,
        "IfcSpace": 4,
        "IfcWall": 8,
        "IfcSlab": 2,
        "IfcRoof": 2,
        "IfcDoor": 1,
        "IfcWindow": 4,
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
    if filled_element_count(model) != 5:
        return False
    checks = (
        check_names(model.by_type("IfcBuildingStorey"), STOREY_NAMES),
        check_names(model.by_type("IfcWall"), WALL_NAMES),
        check_names(model.by_type("IfcSlab"), SLAB_NAMES),
        check_names(model.by_type("IfcRoof"), ROOF_NAMES),
        check_names(model.by_type("IfcDoor"), DOOR_NAMES),
        check_names(model.by_type("IfcWindow"), WINDOW_NAMES),
    )
    if not all(checks):
        return False
    spaces = {norm(getattr(space, "Name", "")): space for space in model.by_type("IfcSpace")}
    if set(spaces) != {norm(name) for name in SPACE_TO_STOREY}:
        return False
    for space_name, storey_name in SPACE_TO_STOREY.items():
        if norm(space_storey_name(spaces[norm(space_name)])) != norm(storey_name):
            return False
    return True


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
