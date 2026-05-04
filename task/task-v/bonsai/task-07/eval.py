#!/usr/bin/env python3
import re
from pathlib import Path


DESKTOP = Path("/home/user/Desktop")

EXPECTED_WINDOW_NAMES = {
    "WINDOW N 2.6",
    "WINDOW N 5.2",
    "WINDOW N 7.8",
    "WINDOW W 10.8",
    "WINDOW W 13.4",
    "WINDOW W 16.0",
}


def emit(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def norm(value):
    text = str(value or "").replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text.strip()).upper()


def close(actual, expected, tol):
    return abs(float(actual) - float(expected)) <= float(tol)


def require_files(root):
    if not (root / "result.ifc").is_file() or (root / "result.ifc").stat().st_size < 100:
        return False
    return True


def product_bbox(product):
    import ifcopenshell.geom
    import numpy as np

    settings = ifcopenshell.geom.settings()
    try:
        settings.set(settings.USE_WORLD_COORDS, True)
    except Exception:
        pass
    shape = ifcopenshell.geom.create_shape(settings, product)
    verts = np.array(shape.geometry.verts, dtype=float).reshape(-1, 3)
    spans = verts.max(axis=0) - verts.min(axis=0)
    return [float(v) for v in spans]


def check_dimensions(elements, width, height, expected_count):
    count = 0
    for element in elements:
        if close(element.OverallWidth, width, 20) and close(element.OverallHeight, height, 20):
            count += 1
    return count == expected_count


def check_opening_relationships(model, facade_wall, filled_products):
    openings = model.by_type("IfcOpeningElement")
    voids = model.by_type("IfcRelVoidsElement")
    fills = model.by_type("IfcRelFillsElement")
    if len(openings) != 8 or len(voids) != 8 or len(fills) != 8:
        return False

    facade_openings = set()
    for rel in voids:
        if rel.RelatingBuildingElement != facade_wall:
            return False
        facade_openings.add(rel.RelatedOpeningElement)
    if facade_openings != set(openings):
        return False

    filled = set()
    for rel in fills:
        if rel.RelatingOpeningElement not in facade_openings:
            return False
        filled.add(rel.RelatedBuildingElement)
    return filled == set(filled_products)


def check_ifc(root):
    import ifcopenshell

    model = ifcopenshell.open(str(root / "result.ifc"))
    if str(model.schema).upper() != "IFC4":
        return False
    if len(model.by_type("IfcProject")) != 1:
        return False
    storeys = model.by_type("IfcBuildingStorey")
    if len(storeys) != 1 or getattr(storeys[0], "Name", None) != "Level 00":
        return False
    if len(model.by_type("IfcBuildingElementProxy")) != 0:
        return False

    walls = model.by_type("IfcWall")
    if len(walls) != 1 or getattr(walls[0], "Name", None) != "Facade Wall":
        return False
    spans = product_bbox(walls[0])
    if not (close(spans[0], 18.0, 0.05) and close(spans[1], 0.25, 0.05) and close(spans[2], 3.6, 0.05)):
        return False

    doors = model.by_type("IfcDoor")
    if len(doors) != 2 or {norm(door.Name) for door in doors} != {"DOOR A", "DOOR B"}:
        return False
    for door in doors:
        if not (close(door.OverallWidth, 950, 20) and close(door.OverallHeight, 2200, 20)):
            return False

    windows = model.by_type("IfcWindow")
    if len(windows) != 6 or {norm(window.Name) for window in windows} != EXPECTED_WINDOW_NAMES:
        return False
    if not check_dimensions(windows, 1200, 1200, 3):
        return False
    if not check_dimensions(windows, 1800, 1400, 3):
        return False

    return check_opening_relationships(model, walls[0], list(doors) + list(windows))


def main():
    try:
        root = DESKTOP
        emit(root.is_dir() and require_files(root) and check_ifc(root))
    except SystemExit:
        raise
    except Exception:
        emit(False)


if __name__ == "__main__":
    main()
