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
        "IfcColumn": 4,
        "IfcBeam": 4,
        "IfcSlab": 1,
        "IfcStructuralAnalysisModel": 1,
        "IfcRelAssignsToGroup": 1,
    },
    "forbidden_counts": {
        "IfcSpace": 0,
        "IfcWall": 0,
        "IfcDoor": 0,
        "IfcWindow": 0,
        "IfcBuildingElementProxy": 0,
        "IfcFurniture": 0,
        "IfcRoof": 0,
        "IfcStair": 0,
        "IfcFlowTerminal": 0,
    },
    "storey_name": "Level 00",
    "analysis_model_name": "Primary Frame",
    "columns": {
        "C1": (0.0, 0.0),
        "C2": (6.0, 0.0),
        "C3": (6.0, 4.0),
        "C4": (0.0, 4.0),
    },
    "column_dims_m": (0.3, 0.3, 3.6),
    "beam_dims_m": {
        "B1": (6.0, 0.3, 0.45),
        "B2": (6.0, 0.3, 0.45),
        "B3": (0.3, 4.0, 0.45),
        "B4": (0.3, 4.0, 0.45),
    },
    "slab": ("Deck Slab", (6.0, 4.0, 0.18)),
    "linear_tolerance_m": 0.08,
    "grid_tolerance_m": 0.12,
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


def center_xy(bbox):
    return ((bbox[0] + bbox[3]) / 2.0, (bbox[1] + bbox[4]) / 2.0)


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


def dimensions_match(actual, expected, tol):
    return all(approx(a, e, tol) for a, e in zip(sorted(actual), sorted(expected)))


def check_storey_assignment(model):
    storeys = model.by_type("IfcBuildingStorey")
    if len(storeys) != 1 or clean_name(storeys[0].Name) != SPEC["storey_name"]:
        return False
    for ifc_class in ("IfcColumn", "IfcBeam", "IfcSlab"):
        for entity in model.by_type(ifc_class):
            storey = parent_storey(entity)
            if storey is None or clean_name(storey.Name) != SPEC["storey_name"]:
                return False
    return True


def check_analysis_model(model):
    groups = model.by_type("IfcStructuralAnalysisModel")
    if len(groups) != 1 or clean_name(groups[0].Name) != SPEC["analysis_model_name"]:
        return False
    rels = model.by_type("IfcRelAssignsToGroup")
    if len(rels) != 1 or rels[0].RelatingGroup.id() != groups[0].id():
        return False
    expected_names = set(SPEC["columns"]) | set(SPEC["beam_dims_m"])
    return {clean_name(obj.Name) for obj in rels[0].RelatedObjects} == expected_names


def check_columns(model):
    columns = {clean_name(c.Name): c for c in model.by_type("IfcColumn")}
    if set(columns) != set(SPEC["columns"]):
        return False
    for name, expected_xy in SPEC["columns"].items():
        bbox = shape_bbox(columns[name])
        if bbox is None:
            return False
        if not dimensions_match(span(bbox), SPEC["column_dims_m"], SPEC["linear_tolerance_m"]):
            return False
        cx, cy = center_xy(bbox)
        if not (approx(cx, expected_xy[0], SPEC["grid_tolerance_m"]) and approx(cy, expected_xy[1], SPEC["grid_tolerance_m"])):
            return False
    return True


def check_beams_and_slab(model):
    beams = {clean_name(b.Name): b for b in model.by_type("IfcBeam")}
    if set(beams) != set(SPEC["beam_dims_m"]):
        return False
    for name, expected_dims in SPEC["beam_dims_m"].items():
        bbox = shape_bbox(beams[name])
        if bbox is None or not dimensions_match(span(bbox), expected_dims, SPEC["linear_tolerance_m"]):
            return False
    slabs = model.by_type("IfcSlab")
    if len(slabs) != 1 or clean_name(slabs[0].Name) != SPEC["slab"][0]:
        return False
    bbox = shape_bbox(slabs[0])
    return bbox is not None and dimensions_match(span(bbox), SPEC["slab"][1], SPEC["linear_tolerance_m"])


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
        and check_analysis_model(model)
        and check_columns(model)
        and check_beams_and_slab(model)
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
