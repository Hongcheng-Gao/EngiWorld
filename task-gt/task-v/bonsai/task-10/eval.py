#!/usr/bin/env python3
import csv
import re
from pathlib import Path


DESKTOP = Path("/home/user/Desktop")

EXPECTED_AREAS = {"OFFICE": 28.00, "MEETING": 8.58, "WC": 3.90}
EXPECTED_WALL_NAMES = {
    "South Wall",
    "East Wall",
    "North Wall",
    "West Wall",
    "Meeting Partition",
    "WC Partition",
}
EXPECTED_CSV_HEADER = ["SpaceName", "Level", "NetFloorArea"]


def emit(ok):
    print("true" if ok else "false")
    raise SystemExit(0)


def norm(value):
    text = str(value or "").replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text.strip()).upper()


def close(actual, expected, tol):
    return abs(float(actual) - float(expected)) <= float(tol)


def parse_float(value):
    text = str(value).strip().replace(" ", "")
    if text.count(",") == 1 and text.count(".") == 0:
        text = text.replace(",", ".")
    else:
        text = text.replace(",", "")
    return float(text)


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        return None, None
    header = [cell.strip() for cell in rows[0]]
    body = []
    for row in rows[1:]:
        if not any(str(cell).strip() for cell in row):
            continue
        padded = row + [""] * max(0, len(header) - len(row))
        body.append({header[i]: padded[i].strip() for i in range(len(header))})
    return header, body


def space_net_area(space):
    for rel in getattr(space, "IsDefinedBy", []) or []:
        if not rel.is_a("IfcRelDefinesByProperties"):
            continue
        definition = rel.RelatingPropertyDefinition
        if not definition.is_a("IfcElementQuantity") or definition.Name != "Qto_SpaceBaseQuantities":
            continue
        for quantity in definition.Quantities or []:
            if quantity.is_a("IfcQuantityArea") and quantity.Name == "NetFloorArea":
                return float(quantity.AreaValue)
    return None


def combined_spans(products):
    import ifcopenshell.geom
    import numpy as np

    settings = ifcopenshell.geom.settings()
    try:
        settings.set(settings.USE_WORLD_COORDS, True)
    except Exception:
        pass
    mins = None
    maxs = None
    for product in products:
        shape = ifcopenshell.geom.create_shape(settings, product)
        verts = np.array(shape.geometry.verts, dtype=float).reshape(-1, 3)
        current_min = verts.min(axis=0)
        current_max = verts.max(axis=0)
        mins = current_min if mins is None else np.minimum(mins, current_min)
        maxs = current_max if maxs is None else np.maximum(maxs, current_max)
    return [float(v) for v in (maxs - mins)]


def check_georeferencing(model):
    crs_list = model.by_type("IfcProjectedCRS")
    if len(crs_list) != 1:
        return False
    crs = crs_list[0]
    if crs.Name != "EPSG:3857" or crs.MapProjection != "Pseudo-Mercator" or crs.MapZone != "Zone-Local":
        return False

    conversions = model.by_type("IfcMapConversion")
    if len(conversions) != 1:
        return False
    conversion = conversions[0]
    checks = {
        "Eastings": 498765.00,
        "Northings": 6812345.00,
        "OrthogonalHeight": 35.00,
        "XAxisAbscissa": 1.00,
        "XAxisOrdinate": 0.00,
        "Scale": 1.00,
    }
    return all(close(getattr(conversion, key), value, 0.01) for key, value in checks.items())


def check_ifc(root):
    import ifcopenshell

    path = root / "result.ifc"
    if not path.is_file() or path.stat().st_size < 100:
        return None
    model = ifcopenshell.open(str(path))
    if str(model.schema).upper() != "IFC4":
        return None
    if len(model.by_type("IfcProject")) != 1:
        return None
    storeys = model.by_type("IfcBuildingStorey")
    if len(storeys) != 1 or storeys[0].Name != "Level 00":
        return None
    if len(model.by_type("IfcBuildingElementProxy")) != 0:
        return None

    spaces = model.by_type("IfcSpace")
    if len(spaces) != 3:
        return None
    areas = {}
    for space in spaces:
        key = norm(space.Name or space.LongName)
        if key not in EXPECTED_AREAS:
            return None
        area = space_net_area(space)
        if area is None or not close(area, EXPECTED_AREAS[key], 0.05):
            return None
        areas[key] = area
    if set(areas) != set(EXPECTED_AREAS):
        return None

    walls = model.by_type("IfcWall")
    slabs = model.by_type("IfcSlab")
    if len(walls) != 6 or {wall.Name for wall in walls} != EXPECTED_WALL_NAMES:
        return None
    if len(slabs) != 1 or slabs[0].Name != "Office Slab":
        return None
    spans = combined_spans(list(walls) + list(slabs))
    if not (close(spans[0], 9.00, 0.05) and close(spans[1], 6.00, 0.05) and close(spans[2], 3.00, 0.05)):
        return None

    if not check_georeferencing(model):
        return None
    return areas


def check_csv(root, ifc_areas):
    path = root / "result.csv"
    if not path.is_file() or path.stat().st_size < 1:
        return False
    header, rows = read_csv(path)
    if header != EXPECTED_CSV_HEADER or len(rows) != 3:
        return False
    seen = set()
    for row in rows:
        name = norm(row.get("SpaceName"))
        if name not in ifc_areas or name in seen:
            return False
        if row.get("Level") != "Level 00":
            return False
        if not close(parse_float(row.get("NetFloorArea")), ifc_areas[name], 0.05):
            return False
        seen.add(name)
    return seen == set(ifc_areas)


def main():
    try:
        root = DESKTOP
        if not root.is_dir():
            emit(False)
        ifc_areas = check_ifc(root)
        emit(bool(ifc_areas) and check_csv(root, ifc_areas))
    except SystemExit:
        raise
    except Exception:
        emit(False)


if __name__ == "__main__":
    main()
