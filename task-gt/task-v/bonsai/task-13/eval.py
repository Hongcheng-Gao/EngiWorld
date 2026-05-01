#!/usr/bin/env python3
from pathlib import Path


DESKTOP = Path("/home/user/Desktop")

EXPECTED_OPENINGS = 4
EXPECTED_WINDOWS = 3
EXPECTED_DOORS = 1
MIN_WALLS = 4


def emit(ok):
    print("true" if ok else "false")
    raise SystemExit(0)


def check_outputs(root):
    path = root / "result.ifc"
    return path.is_file() and path.stat().st_size >= 100


def check_ifc(root):
    import ifcopenshell

    model = ifcopenshell.open(str(root / "result.ifc"))
    if model.schema.upper() != "IFC4":
        return False
    if len(model.by_type("IfcProject")) != 1 or len(model.by_type("IfcSite")) != 1:
        return False
    if len(model.by_type("IfcBuilding")) != 1 or len(model.by_type("IfcBuildingStorey")) != 1:
        return False
    if len(model.by_type("IfcWall")) < MIN_WALLS:
        return False
    if len(model.by_type("IfcDoor")) != EXPECTED_DOORS:
        return False
    if len(model.by_type("IfcWindow")) != EXPECTED_WINDOWS:
        return False
    openings = model.by_type("IfcOpeningElement")
    if len(openings) != EXPECTED_OPENINGS:
        return False
    voids_by_opening = {}
    for rel in model.by_type("IfcRelVoidsElement"):
        opening = getattr(rel, "RelatedOpeningElement", None)
        host = getattr(rel, "RelatingBuildingElement", None)
        if opening is None or host is None or not host.is_a("IfcWall"):
            return False
        voids_by_opening.setdefault(opening.id(), 0)
        voids_by_opening[opening.id()] += 1
    fills_by_opening = {}
    filled_classes = []
    filled_ids = []
    for rel in model.by_type("IfcRelFillsElement"):
        opening = getattr(rel, "RelatingOpeningElement", None)
        element = getattr(rel, "RelatedBuildingElement", None)
        if opening is None or element is None or not (element.is_a("IfcDoor") or element.is_a("IfcWindow")):
            return False
        fills_by_opening.setdefault(opening.id(), 0)
        fills_by_opening[opening.id()] += 1
        filled_classes.append(element.is_a())
        filled_ids.append(element.id())
    if sorted(filled_classes) != sorted(["IfcDoor"] * EXPECTED_DOORS + ["IfcWindow"] * EXPECTED_WINDOWS):
        return False
    expected_filled_ids = {element.id() for element in model.by_type("IfcDoor") + model.by_type("IfcWindow")}
    if set(filled_ids) != expected_filled_ids or len(filled_ids) != len(expected_filled_ids):
        return False
    for opening in openings:
        if voids_by_opening.get(opening.id()) != 1:
            return False
        if fills_by_opening.get(opening.id()) != 1:
            return False
    if model.by_type("IfcBuildingElementProxy") or model.by_type("IfcFurniture"):
        return False
    return True


def main():
    try:
        root = DESKTOP
        emit(root.is_dir() and check_outputs(root) and check_ifc(root))
    except SystemExit:
        raise
    except Exception:
        emit(False)


if __name__ == "__main__":
    main()
