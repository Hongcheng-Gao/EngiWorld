#!/usr/bin/env python3
import re
from pathlib import Path

import ifcopenshell


DESKTOP = Path("/home/user/Desktop")
import ifcopenshell.geom
import ifcopenshell.util.unit


SPEC = {
    "ifc_file": "result.ifc",
    "min_ifc_bytes": 500,
    "schema": "IFC4",
    "counts": {
        "IfcProject": 1,
        "IfcSite": 1,
        "IfcBuilding": 1,
        "IfcBuildingStorey": 2,
        "IfcSpace": 7,
        "IfcWall": 8,
        "IfcSlab": 3,
        "IfcDoor": 1,
        "IfcWindow": 5,
        "IfcOpeningElement": 7,
        "IfcRelVoidsElement": 7,
        "IfcRelFillsElement": 6,
    },
    "forbidden_counts": {
        "IfcBuildingElementProxy": 0,
        "IfcFurniture": 0,
        "IfcRoof": 0,
        "IfcColumn": 0,
        "IfcBeam": 0,
        "IfcStair": 0,
        "IfcFlowTerminal": 0,
    },
    "storey_names": ["Ground Floor", "First Floor"],
    "space_dimensions": {
        "Living": (3.60, 3.80),
        "Kitchen": (3.20, 2.00),
        "Dining": (3.20, 1.80),
        "Entry": (3.60, 1.00),
        "Bedroom 1": (3.40, 4.80),
        "Bedroom 2": (3.40, 2.80),
        "Bath": (3.40, 2.00),
    },
    "space_tolerance_m": 0.10,
    "slab_names": ["Ground Slab", "First Floor Slab", "Roof Slab"],
    "slab_min_z": {"Ground Slab": 0.00, "First Floor Slab": 3.20, "Roof Slab": 6.20},
    "wall_height_m": 3.00,
    "wall_height_tolerance_m": 0.10,
    "door_widths": {"Main Entrance": 0.95},
    "window_widths": {
        "GF North West Window": 1.20,
        "GF North East Window": 1.20,
        "GF East Window": 1.20,
        "FF North West Window": 1.20,
        "FF North East Window": 1.20,
    },
    "opening_hosts": {
        "Main Entrance": ("IfcDoor", "GF South"),
        "GF North West Window": ("IfcWindow", "GF North"),
        "GF North East Window": ("IfcWindow", "GF North"),
        "GF East Window": ("IfcWindow", "GF East"),
        "FF North West Window": ("IfcWindow", "FF North"),
        "FF North East Window": ("IfcWindow", "FF North"),
    },
    "unfilled_opening": ("Stair Opening", "First Floor Slab"),
    "width_tolerance_m": 0.05,
}


def finish(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def one_space(value):
    return re.sub(r"\s+", " ", str(value or "").strip())


def approx(actual, expected, tolerance):
    return abs(float(actual) - float(expected)) <= float(tolerance)


def unit_scale(model):
    try:
        return float(ifcopenshell.util.unit.calculate_unit_scale(model))
    except Exception:
        return 1.0


def entity_count(model, ifc_class):
    return len(model.by_type(ifc_class))


def check_counts(model):
    for ifc_class, expected in SPEC["counts"].items():
        if entity_count(model, ifc_class) != expected:
            return False
    for ifc_class, expected in SPEC["forbidden_counts"].items():
        if entity_count(model, ifc_class) != expected:
            return False
    return True


def check_global_ids(model):
    gids = [e.GlobalId for e in model.by_type("IfcRoot") if getattr(e, "GlobalId", None)]
    return len(gids) == len(set(gids))


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


def named_entities(model, ifc_class):
    return {one_space(getattr(e, "Name", "")): e for e in model.by_type(ifc_class)}


def scaled_width(entity, model):
    value = getattr(entity, "OverallWidth", None)
    if value in (None, ""):
        return None
    raw = float(value)
    scaled = raw * unit_scale(model)
    if 0.05 <= scaled <= 50.0:
        return scaled
    return raw


def filling_opening(fill):
    rels = getattr(fill, "FillsVoids", None) or []
    if len(rels) != 1:
        return None
    return getattr(rels[0], "RelatingOpeningElement", None)


def opening_host(opening):
    rels = getattr(opening, "VoidsElements", None) or []
    if len(rels) != 1:
        return None
    return getattr(rels[0], "RelatingBuildingElement", None)


def check_storeys(model):
    names = sorted(one_space(getattr(s, "Name", "")) for s in model.by_type("IfcBuildingStorey"))
    return names == sorted(SPEC["storey_names"])


def check_space_geometry(model):
    spaces = named_entities(model, "IfcSpace")
    if set(spaces) != set(SPEC["space_dimensions"]):
        return False
    for name, (expected_x, expected_y) in SPEC["space_dimensions"].items():
        bbox = shape_bbox(spaces[name])
        if bbox is None:
            return False
        sx, sy, _ = span(bbox)
        tol = SPEC["space_tolerance_m"]
        if not approx(sx, expected_x, tol) or not approx(sy, expected_y, tol):
            return False
    return True


def check_slabs(model):
    slabs = named_entities(model, "IfcSlab")
    if set(slabs) != set(SPEC["slab_names"]):
        return False
    for name, min_z in SPEC["slab_min_z"].items():
        bbox = shape_bbox(slabs[name])
        if bbox is None or bbox[2] < min_z:
            return False
    return True


def check_wall_geometry(model):
    for wall in model.by_type("IfcWall"):
        bbox = shape_bbox(wall)
        if bbox is None:
            return False
        _, _, sz = span(bbox)
        if not approx(sz, SPEC["wall_height_m"], SPEC["wall_height_tolerance_m"]):
            return False
    return True


def check_widths(model):
    doors = named_entities(model, "IfcDoor")
    windows = named_entities(model, "IfcWindow")
    tol = SPEC["width_tolerance_m"]
    for name, expected in SPEC["door_widths"].items():
        if name not in doors or not approx(scaled_width(doors[name], model), expected, tol):
            return False
    for name, expected in SPEC["window_widths"].items():
        if name not in windows or not approx(scaled_width(windows[name], model), expected, tol):
            return False
    return True


def check_openings(model):
    walls = named_entities(model, "IfcWall")
    slabs = named_entities(model, "IfcSlab")
    fills = {}
    for ifc_class in ("IfcDoor", "IfcWindow"):
        fills.update({name: (ifc_class, entity) for name, entity in named_entities(model, ifc_class).items()})
    used_openings = set()
    for fill_name, (ifc_class, host_name) in SPEC["opening_hosts"].items():
        if fill_name not in fills or fills[fill_name][0] != ifc_class or host_name not in walls:
            return False
        opening = filling_opening(fills[fill_name][1])
        if opening is None or opening.id() in used_openings:
            return False
        host = opening_host(opening)
        if host is None or host.id() != walls[host_name].id():
            return False
        used_openings.add(opening.id())

    opening_name, host_name = SPEC["unfilled_opening"]
    openings = named_entities(model, "IfcOpeningElement")
    if opening_name not in openings or host_name not in slabs:
        return False
    opening = openings[opening_name]
    if getattr(opening, "HasFillings", None):
        return False
    host = opening_host(opening)
    return host is not None and host.id() == slabs[host_name].id()


def check_ifc(root):
    path = root / SPEC["ifc_file"]
    if not path.is_file() or path.stat().st_size < SPEC["min_ifc_bytes"]:
        return False
    model = ifcopenshell.open(str(path))
    if not str(getattr(model, "schema", "")).upper().startswith(SPEC["schema"]):
        return False
    return (
        check_counts(model)
        and check_global_ids(model)
        and check_storeys(model)
        and check_space_geometry(model)
        and check_slabs(model)
        and check_wall_geometry(model)
        and check_widths(model)
        and check_openings(model)
    )


def main():
    try:
        root = DESKTOP
        finish(root.is_dir() and check_ifc(root))
    except SystemExit:
        raise
    except Exception:
        finish(False)


if __name__ == "__main__":
    main()
