#!/usr/bin/env python3
from pathlib import Path

import ifcopenshell


DESKTOP = Path("C:/Users/Administrator/Desktop")


SPEC = {
    "required_outputs": {"result.ifc": 500},
    "schema": "IFC4",
    "storey_count": 3,
    "space_count": 0,
    "min_counts": {"IfcWall": 12, "IfcSlab": 3, "IfcDoor": 9, "IfcWindow": 6},
    "bbox_exact": {"min": [0.0, 0.0, -0.048], "max": [12.0, 8.0, 10.2]},
    "bbox_tolerance": 0.5,
}


def finish(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def unique_global_ids(model):
    gids = [e.GlobalId for e in model.by_type("IfcRoot") if getattr(e, "GlobalId", None)]
    return len(gids) == len(set(gids))


def ifc_bbox(model):
    import numpy as np
    import ifcopenshell.geom

    settings = ifcopenshell.geom.settings()
    try:
        settings.set(settings.USE_WORLD_COORDS, True)
    except Exception:
        pass
    mins = None
    maxs = None
    for product in model.by_type("IfcProduct"):
        if product.is_a("IfcOpeningElement") or not getattr(product, "Representation", None):
            continue
        try:
            shape = ifcopenshell.geom.create_shape(settings, product)
            verts = np.array(shape.geometry.verts, dtype=float).reshape(-1, 3)
        except Exception:
            continue
        if verts.size == 0:
            continue
        pmin = verts.min(axis=0)
        pmax = verts.max(axis=0)
        mins = pmin if mins is None else np.minimum(mins, pmin)
        maxs = pmax if maxs is None else np.maximum(maxs, pmax)
    if mins is None or maxs is None:
        return None
    return mins.tolist(), maxs.tolist()


def check_ifc(model):
    if not str(getattr(model, "schema", "")).upper().startswith(SPEC["schema"]):
        return False
    if not unique_global_ids(model):
        return False
    if len(model.by_type("IfcBuildingStorey")) != SPEC["storey_count"]:
        return False
    if len(model.by_type("IfcSpace")) != SPEC["space_count"]:
        return False
    for cls, minimum in SPEC["min_counts"].items():
        if len(model.by_type(cls)) < minimum:
            return False
    bbox = ifc_bbox(model)
    if bbox is None:
        return False
    mins, maxs = bbox
    tol = SPEC["bbox_tolerance"]
    for actual, target in zip(mins, SPEC["bbox_exact"]["min"]):
        if abs(float(actual) - float(target)) > tol:
            return False
    for actual, target in zip(maxs, SPEC["bbox_exact"]["max"]):
        if abs(float(actual) - float(target)) > tol:
            return False
    return True


def evaluate():
    root = DESKTOP
    path = root / "result.ifc"
    if not path.is_file() or path.stat().st_size < SPEC["required_outputs"]["result.ifc"]:
        return False
    model = ifcopenshell.open(str(path))
    return check_ifc(model)


def main():
    try:
        finish(evaluate())
    except SystemExit:
        raise
    except Exception:
        finish(False)


if __name__ == "__main__":
    main()
