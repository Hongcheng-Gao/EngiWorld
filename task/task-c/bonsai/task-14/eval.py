#!/usr/bin/env python3
import re
from pathlib import Path

import ifcopenshell


DESKTOP = Path("/home/user/Desktop")
import ifcopenshell.geom


SPEC = {
    "required_output": "result.ifc",
    "min_file_bytes": 500,
    "schema": "IFC4",
    "counts": {
        "IfcProject": 1,
        "IfcSite": 1,
        "IfcBuilding": 1,
        "IfcBuildingStorey": 1,
        "IfcWall": 4,
        "IfcSlab": 1,
        "IfcDoor": 1,
        "IfcWindow": 2,
        "IfcOpeningElement": 3,
        "IfcRelVoidsElement": 3,
        "IfcRelFillsElement": 3,
        "IfcProjectedCRS": 1,
        "IfcMapConversion": 1,
    },
    "forbidden_counts": {
        "IfcSpace": 0,
        "IfcBuildingElementProxy": 0,
        "IfcFurniture": 0,
        "IfcRoof": 0,
        "IfcColumn": 0,
        "IfcBeam": 0,
        "IfcStair": 0,
        "IfcFlowTerminal": 0,
    },
    "storey_name": "Ground Floor",
    "crs_name": "EPSG:3857",
    "map_conversion": {
        "Eastings": 1000000.0,
        "Northings": 2000000.0,
        "OrthogonalHeight": 0.0,
        "XAxisAbscissa": 1.0,
        "XAxisOrdinate": 0.0,
        "Scale": 1.0,
    },
    "products": {
        "South Wall": (12.0, 0.2, 3.0),
        "East Wall": (0.2, 8.0, 3.0),
        "North Wall": (12.0, 0.2, 3.0),
        "West Wall": (0.2, 8.0, 3.0),
        "Base Slab": (12.0, 8.0, 0.25),
        "Entry": (0.244, 0.115, 1.083),
        "Win E": (0.119, 0.075, 0.119),
        "Win W": (0.119, 0.075, 0.119),
    },
    "max_local_abs_coordinate_m": 200.0,
    "linear_tolerance_m": 0.08,
    "map_tolerance": 0.001,
}


def emit(ok):
    print("true" if ok else "false")
    raise SystemExit(0)


def clean_name(value):
    return re.sub(r"\s+", " ", str(value or "").strip())


def approx(actual, expected, tol):
    return actual is not None and abs(float(actual) - float(expected)) <= float(tol)


def shape_bbox(entity):
    settings = ifcopenshell.geom.settings()
    try:
        settings.set(settings.USE_WORLD_COORDS, True)
    except Exception:
        pass
    shape = ifcopenshell.geom.create_shape(settings, entity)
    verts = list(shape.geometry.verts)
    if not verts:
        return None
    xs = verts[0::3]
    ys = verts[1::3]
    zs = verts[2::3]
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def span(bbox):
    minx, miny, minz, maxx, maxy, maxz = bbox
    return (maxx - minx, maxy - miny, maxz - minz)


def dimensions_match(actual, expected, tol):
    return all(approx(a, e, tol) for a, e in zip(sorted(actual), sorted(expected)))


def parent_storey(obj):
    for rel in getattr(obj, "ContainedInStructure", None) or []:
        parent = getattr(rel, "RelatingStructure", None)
        if parent and parent.is_a("IfcBuildingStorey"):
            return parent
    return None


def unique_global_ids(model):
    gids = [e.GlobalId for e in model.by_type("IfcRoot") if getattr(e, "GlobalId", None)]
    return len(gids) == len(set(gids))


def check_counts(model):
    for ifc_class, expected in SPEC["counts"].items():
        if len(model.by_type(ifc_class)) != expected:
            return False
    for ifc_class, expected in SPEC["forbidden_counts"].items():
        if len(model.by_type(ifc_class)) != expected:
            return False
    return True


def check_storey(model):
    storeys = model.by_type("IfcBuildingStorey")
    if len(storeys) != 1 or clean_name(storeys[0].Name) != SPEC["storey_name"]:
        return False
    for ifc_class in ("IfcWall", "IfcSlab", "IfcDoor", "IfcWindow"):
        for entity in model.by_type(ifc_class):
            storey = parent_storey(entity)
            if storey is None or clean_name(storey.Name) != SPEC["storey_name"]:
                return False
    return True


def check_products(model):
    products = {}
    for ifc_class in ("IfcWall", "IfcSlab", "IfcDoor", "IfcWindow"):
        products.update({clean_name(p.Name): p for p in model.by_type(ifc_class)})
    if set(products) != set(SPEC["products"]):
        return False
    for name, expected_dims in SPEC["products"].items():
        bbox = shape_bbox(products[name])
        if bbox is None or not dimensions_match(span(bbox), expected_dims, SPEC["linear_tolerance_m"]):
            return False
    return True


def check_georef(model):
    crs = model.by_type("IfcProjectedCRS")
    maps = model.by_type("IfcMapConversion")
    if len(crs) != 1 or clean_name(crs[0].Name) != SPEC["crs_name"] or len(maps) != 1:
        return False
    for attr, expected in SPEC["map_conversion"].items():
        if not approx(getattr(maps[0], attr, None), expected, SPEC["map_tolerance"]):
            return False
    max_abs = 0.0
    for product in model.by_type("IfcProduct"):
        if product.is_a("IfcOpeningElement") or not getattr(product, "Representation", None):
            continue
        bbox = shape_bbox(product)
        if bbox is None:
            continue
        max_abs = max(max_abs, *(abs(v) for v in bbox))
    return 0.0 < max_abs <= SPEC["max_local_abs_coordinate_m"]


def evaluate():
    result_dir = DESKTOP
    if not result_dir.is_dir():
        return False
    ifc_path = result_dir / SPEC["required_output"]
    if not ifc_path.is_file() or ifc_path.stat().st_size < SPEC["min_file_bytes"]:
        return False
    model = ifcopenshell.open(str(ifc_path))
    return (
        str(getattr(model, "schema", "")).upper().startswith(SPEC["schema"])
        and unique_global_ids(model)
        and check_counts(model)
        and check_storey(model)
        and check_products(model)
        and check_georef(model)
    )


def main():
    try:
        emit(evaluate())
    except SystemExit:
        raise
    except Exception:
        emit(False)


if __name__ == "__main__":
    main()
