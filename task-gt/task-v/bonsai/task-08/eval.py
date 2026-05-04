#!/usr/bin/env python3
from pathlib import Path


DESKTOP = Path("/home/user/Desktop")

EXPECTED_NAMES = {
    "IfcDuctSegment": {"Supply Segment 1", "Supply Segment 2"},
    "IfcDuctFitting": {"Branch Fitting"},
    "IfcAirTerminal": {"Terminal South", "Terminal East"},
}
EXPECTED_COUNTS = {
    "IfcProject": 1,
    "IfcBuildingStorey": 1,
    "IfcBuildingElementProxy": 0,
    "IfcDuctSegment": 2,
    "IfcDuctFitting": 1,
    "IfcAirTerminal": 2,
    "IfcDistributionSystem": 1,
}
EXPECTED_SPANS = {
    "Supply Segment 1": (1.80, 0.35, 0.25),
    "Supply Segment 2": (1.40, 0.30, 0.25),
    "Branch Fitting": (0.45, 0.40, 0.30),
    "Terminal South": (0.40, 0.40, 0.20),
    "Terminal East": (0.40, 0.40, 0.20),
}


def emit(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def close(actual, expected, tol=0.05):
    return abs(float(actual) - float(expected)) <= tol


def product_spans(product):
    import ifcopenshell.geom
    import numpy as np

    settings = ifcopenshell.geom.settings()
    try:
        settings.set(settings.USE_WORLD_COORDS, True)
    except Exception:
        pass
    shape = ifcopenshell.geom.create_shape(settings, product)
    verts = np.array(shape.geometry.verts, dtype=float).reshape(-1, 3)
    return [float(v) for v in (verts.max(axis=0) - verts.min(axis=0))]


def contained_in_storey(product, storey):
    return any(rel.RelatingStructure == storey for rel in (getattr(product, "ContainedInStructure", []) or []))


def check_geometry(products_by_name):
    for name, expected in EXPECTED_SPANS.items():
        spans = product_spans(products_by_name[name])
        if any(not close(actual, target) for actual, target in zip(spans, expected)):
            return False
    return True


def check_system(model, products_by_name):
    systems = model.by_type("IfcDistributionSystem")
    if len(systems) != 1 or systems[0].Name != "Supply Air":
        return False
    related = set()
    for rel in model.by_type("IfcRelAssignsToGroup"):
        if rel.RelatingGroup == systems[0]:
            related.update(rel.RelatedObjects)
    return related == set(products_by_name.values())


def check_ifc(root):
    import ifcopenshell

    path = root / "result.ifc"
    if not path.is_file() or path.stat().st_size < 100:
        return False
    model = ifcopenshell.open(str(path))
    if str(model.schema).upper() != "IFC4":
        return False
    for cls, expected in EXPECTED_COUNTS.items():
        if len(model.by_type(cls)) != expected:
            return False

    storey = model.by_type("IfcBuildingStorey")[0]
    if storey.Name != "Level 00":
        return False

    products_by_name = {}
    for cls, names in EXPECTED_NAMES.items():
        elements = model.by_type(cls)
        if {element.Name for element in elements} != names:
            return False
        for element in elements:
            if not contained_in_storey(element, storey):
                return False
            products_by_name[element.Name] = element

    return check_system(model, products_by_name) and check_geometry(products_by_name)


def main():
    try:
        root = DESKTOP
        emit(root.is_dir() and check_ifc(root))
    except SystemExit:
        raise
    except Exception:
        emit(False)


if __name__ == "__main__":
    main()
