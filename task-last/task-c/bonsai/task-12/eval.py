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
        "IfcBuildingStorey": 2,
        "IfcSpace": 3,
        "IfcWall": 4,
        "IfcSlab": 2,
        "IfcDoor": 1,
        "IfcOpeningElement": 2,
        "IfcRelVoidsElement": 2,
        "IfcRelFillsElement": 1,
    },
    "forbidden_counts": {
        "IfcWindow": 0,
        "IfcBuildingElementProxy": 0,
        "IfcFurniture": 0,
        "IfcRoof": 0,
        "IfcColumn": 0,
        "IfcBeam": 0,
        "IfcStair": 0,
        "IfcFlowTerminal": 0,
    },
    "storeys": {"Ground Floor", "Mezzanine"},
    "spaces": {
        "Ground Storage": ("Ground Floor", (9.2, 7.4)),
        "Ground Entry": ("Ground Floor", (2.1, 2.2)),
        "Mezzanine Office": ("Mezzanine", (9.4, 3.7)),
    },
    "space_height_m": 3.0,
    "slabs": {
        "Ground Slab": ("Ground Floor", (12.0, 8.0, 0.25)),
        "Mezzanine Slab": ("Mezzanine", (10.0, 8.0, 0.2)),
    },
    "door_opening": ("Entry Door", "South Wall", (1.0, 0.2, 2.1)),
    "slab_void": ("Stair Void", "Mezzanine Slab"),
    "linear_tolerance_m": 0.08,
    "height_tolerance_m": 0.05,
}


def emit(ok):
    print("True" if ok else "False")
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
    if obj.is_a("IfcSpace"):
        for rel in getattr(obj, "Decomposes", None) or []:
            parent = getattr(rel, "RelatingObject", None)
            if parent and parent.is_a("IfcBuildingStorey"):
                return parent
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


def check_storeys(model):
    storeys = {clean_name(s.Name) for s in model.by_type("IfcBuildingStorey")}
    return storeys == SPEC["storeys"]


def check_spaces_and_slabs(model):
    spaces = {clean_name(s.Name): s for s in model.by_type("IfcSpace")}
    if set(spaces) != set(SPEC["spaces"]):
        return False
    for name, (expected_storey, expected_xy) in SPEC["spaces"].items():
        storey = parent_storey(spaces[name])
        if storey is None or clean_name(storey.Name) != expected_storey:
            return False
        bbox = shape_bbox(spaces[name])
        if bbox is None:
            return False
        sx, sy, sz = span(bbox)
        if not dimensions_match((sx, sy), expected_xy, SPEC["linear_tolerance_m"]):
            return False
        if not approx(sz, SPEC["space_height_m"], SPEC["height_tolerance_m"]):
            return False
    slabs = {clean_name(s.Name): s for s in model.by_type("IfcSlab")}
    if set(slabs) != set(SPEC["slabs"]):
        return False
    for name, (expected_storey, expected_dims) in SPEC["slabs"].items():
        storey = parent_storey(slabs[name])
        if storey is None or clean_name(storey.Name) != expected_storey:
            return False
        bbox = shape_bbox(slabs[name])
        if bbox is None or not dimensions_match(span(bbox), expected_dims, SPEC["linear_tolerance_m"]):
            return False
    return True


def check_openings(model):
    doors = model.by_type("IfcDoor")
    if len(doors) != 1 or clean_name(doors[0].Name) != SPEC["door_opening"][0]:
        return False
    rels = getattr(doors[0], "FillsVoids", None) or []
    if len(rels) != 1:
        return False
    opening = rels[0].RelatingOpeningElement
    hosts = getattr(opening, "VoidsElements", None) or []
    if len(hosts) != 1 or clean_name(hosts[0].RelatingBuildingElement.Name) != SPEC["door_opening"][1]:
        return False
    bbox = shape_bbox(opening)
    if bbox is None or not dimensions_match(span(bbox), SPEC["door_opening"][2], SPEC["linear_tolerance_m"]):
        return False
    empty_voids = []
    for op in model.by_type("IfcOpeningElement"):
        fills = getattr(op, "HasFillings", None) or []
        hosts = getattr(op, "VoidsElements", None) or []
        if len(fills) == 0 and len(hosts) == 1:
            host = hosts[0].RelatingBuildingElement
            empty_voids.append((clean_name(op.Name), clean_name(host.Name)))
    return empty_voids == [SPEC["slab_void"]]


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
        and check_storeys(model)
        and check_spaces_and_slabs(model)
        and check_openings(model)
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
