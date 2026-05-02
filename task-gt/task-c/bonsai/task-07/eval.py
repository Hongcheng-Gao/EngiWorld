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
        "IfcDuctSegment": 3,
        "IfcDuctFitting": 2,
        "IfcAirTerminal": 2,
        "IfcDistributionSystem": 1,
        "IfcRelAssignsToGroup": 1,
    },
    "forbidden_counts": {
        "IfcSpace": 0,
        "IfcWall": 0,
        "IfcSlab": 0,
        "IfcDoor": 0,
        "IfcWindow": 0,
        "IfcBuildingElementProxy": 0,
        "IfcFurniture": 0,
        "IfcRoof": 0,
        "IfcColumn": 0,
        "IfcBeam": 0,
        "IfcStair": 0,
    },
    "storey_name": "Level 00",
    "system_name": "Supply Air",
    "elements": {
        "IfcDuctSegment": {
            "Main Segment": (2.4, 0.4, 0.3),
            "Branch Spine": (1.8, 0.35, 0.25),
            "Riser Segment": (1.8, 0.3, 0.25),
        },
        "IfcDuctFitting": {
            "Transition": (0.6, 0.45, 0.35),
            "Bend": (0.5, 0.35, 0.35),
        },
        "IfcAirTerminal": {
            "Terminal East": (0.45, 0.45, 0.2),
            "Terminal North": (0.45, 0.45, 0.2),
        },
    },
    "linear_tolerance_m": 0.08,
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


def check_storey_assignment(model):
    storeys = model.by_type("IfcBuildingStorey")
    if len(storeys) != 1 or clean_name(storeys[0].Name) != SPEC["storey_name"]:
        return False
    for ifc_class in SPEC["elements"]:
        for entity in model.by_type(ifc_class):
            storey = parent_storey(entity)
            if storey is None or clean_name(storey.Name) != SPEC["storey_name"]:
                return False
    return True


def dimensions_match(actual, expected, tol):
    return all(approx(a, e, tol) for a, e in zip(sorted(actual), sorted(expected)))


def check_elements(model):
    for ifc_class, expected_by_name in SPEC["elements"].items():
        actual_by_name = {clean_name(e.Name): e for e in model.by_type(ifc_class)}
        if set(actual_by_name) != set(expected_by_name):
            return False
        for name, expected_dims in expected_by_name.items():
            bbox = shape_bbox(actual_by_name[name])
            if bbox is None or not dimensions_match(span(bbox), expected_dims, SPEC["linear_tolerance_m"]):
                return False
    return True


def check_distribution_system(model):
    systems = model.by_type("IfcDistributionSystem")
    if len(systems) != 1 or clean_name(systems[0].Name) != SPEC["system_name"]:
        return False
    rels = model.by_type("IfcRelAssignsToGroup")
    if len(rels) != 1 or rels[0].RelatingGroup.id() != systems[0].id():
        return False
    expected_names = set()
    for expected_by_name in SPEC["elements"].values():
        expected_names.update(expected_by_name)
    actual_names = {clean_name(obj.Name) for obj in rels[0].RelatedObjects}
    return actual_names == expected_names


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
        and check_storey_assignment(model)
        and check_elements(model)
        and check_distribution_system(model)
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
