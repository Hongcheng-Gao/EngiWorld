#!/usr/bin/env python3
import re
from pathlib import Path
DESKTOP = Path("C:/Users/Administrator/Desktop")

import ifcopenshell
import ifcopenshell.geom


SPEC = {
    "required_ifc": "result.ifc",
    "min_ifc_bytes": 500,
    "schema": "IFC4",
    "counts": {
        "IfcProject": 1,
        "IfcSite": 1,
        "IfcBuilding": 1,
        "IfcBuildingStorey": 2,
        "IfcSpace": 5,
        "IfcWall": 12,
        "IfcSlab": 3,
        "IfcCurtainWall": 5,
    },
    "forbidden_counts": {
        "IfcRoof": 0,
        "IfcDoor": 0,
        "IfcWindow": 0,
        "IfcStair": 0,
        "IfcColumn": 0,
        "IfcBeam": 0,
        "IfcBuildingElementProxy": 0,
    },
    "bbox_tolerance": 0.35,
    "bbox": {"IfcWall": [0, 0, 0.25, 28.2, 14.2, 7.05], "IfcSlab": [0, 0, 0, 28, 14, 3.85], "IfcCurtainWall": [1, 0.02, 0.7, 26.4, 0.18, 3.1], "IfcSpace": [1.2, 1.2, 0.25, 26, 9.4, 6.8]},
    "space_token_counts": {"lobby": 1, "meeting": 4},
    "required_space_names": ["central lobby"],
}


def finish(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def norm(value):
    text = str(value or "").replace("_", " ").replace("-", " ").lower()
    return re.sub(r"\s+", " ", text).strip()


def entity_count(model, ifc_class):
    return len(model.by_type(ifc_class))


def unique_global_ids(model):
    gids = [e.GlobalId for e in model.by_type("IfcRoot") if getattr(e, "GlobalId", None)]
    return len(gids) == len(set(gids))


def check_counts(model):
    for ifc_class, expected in SPEC["counts"].items():
        if entity_count(model, ifc_class) != expected:
            return False
    for ifc_class, expected in SPEC["forbidden_counts"].items():
        if entity_count(model, ifc_class) != expected:
            return False
    return True


def check_spaces(model):
    names = [norm(getattr(space, "Name", "") or getattr(space, "LongName", "")) for space in model.by_type("IfcSpace")]
    if not all(sum(1 for name in names if token in name) >= minimum for token, minimum in SPEC["space_token_counts"].items()):
        return False
    return all(norm(required) in names for required in SPEC["required_space_names"])




def geometry_settings():
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    return settings


def combined_bbox(model, ifc_class):
    xs, ys, zs = [], [], []
    settings = geometry_settings()
    for element in model.by_type(ifc_class):
        try:
            shape = ifcopenshell.geom.create_shape(settings, element)
            verts = shape.geometry.verts
        except Exception:
            continue
        xs.extend(verts[0::3])
        ys.extend(verts[1::3])
        zs.extend(verts[2::3])
    if not xs:
        return None
    return [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)]


def bbox_close(actual, expected, tolerance):
    return actual is not None and all(abs(a - e) <= tolerance for a, e in zip(actual, expected))


def check_geometry(model):
    tolerance = SPEC.get("bbox_tolerance", 0.35)
    for ifc_class, expected in SPEC.get("bbox", {}).items():
        if not bbox_close(combined_bbox(model, ifc_class), expected, tolerance):
            return False
    return True

def evaluate(result_dir):
    ifc_path = Path(result_dir) / SPEC["required_ifc"]
    if not ifc_path.is_file() or ifc_path.stat().st_size < SPEC["min_ifc_bytes"]:
        return False
    model = ifcopenshell.open(str(ifc_path))
    return (
        str(getattr(model, "schema", "")).upper().startswith(SPEC["schema"])
        and unique_global_ids(model)
        and check_counts(model)
        and check_spaces(model)
        and check_geometry(model)
    )


def main():
    try:
        finish(evaluate(DESKTOP))
    except SystemExit:
        raise
    except Exception:
        finish(False)


if __name__ == "__main__":
    main()
