#!/usr/bin/env python3
import re
from pathlib import Path
DESKTOP = Path("C:/Users/Administrator/Desktop")

import ifcopenshell
import ifcopenshell.geom
import numpy as np


SPEC = {
    "required_output": "result.ifc",
    "min_file_bytes": 500,
    "schema": "IFC4",
    "counts": {
        "IfcProject": 1,
        "IfcSite": 1,
        "IfcBuilding": 1,
        "IfcBuildingStorey": 1,
        "IfcSpace": 4,
        "IfcWall": 5,
        "IfcSlab": 1,
        "IfcRoof": 1,
    },
    "min_counts": {
        "IfcDoor": 3,
        "IfcWindow": 6,
        "IfcCurtainWall": 2,
    },
    "forbidden_counts": {
        "IfcBuildingElementProxy": 0,
        "IfcStair": 0,
        "IfcColumn": 0,
        "IfcBeam": 0,
    },
    "required_space_tokens": ["retail", "storage", "prep", "toilet"],
    "bbox_ranges_m": {"x": (16.5, 19.5), "y": (10.5, 13.5), "z": (3.3, 4.5)},
    "curtain_edge_tolerance_m": 1.0,
    "rear_space_min_y_m": 8.0,
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


def geometry_settings():
    settings = ifcopenshell.geom.settings()
    try:
        settings.set(settings.USE_WORLD_COORDS, True)
    except Exception:
        pass
    return settings


def product_vertices(settings, product):
    shape = ifcopenshell.geom.create_shape(settings, product)
    return np.array(shape.geometry.verts, dtype=float).reshape(-1, 3)


def product_centroid(settings, product):
    verts = product_vertices(settings, product)
    if not verts.size:
        raise ValueError("empty geometry")
    return verts.mean(axis=0)


def shaped_records(model, settings):
    records = []
    for product in model.by_type("IfcProduct"):
        if product.is_a("IfcOpeningElement") or not getattr(product, "Representation", None):
            continue
        try:
            verts = product_vertices(settings, product)
        except Exception:
            continue
        if verts.size:
            records.append((product, verts))
    return records


def check_counts(model):
    for ifc_class, expected in SPEC["counts"].items():
        if entity_count(model, ifc_class) != expected:
            return False
    for ifc_class, minimum in SPEC["min_counts"].items():
        if entity_count(model, ifc_class) < minimum:
            return False
    for ifc_class, expected in SPEC["forbidden_counts"].items():
        if entity_count(model, ifc_class) != expected:
            return False
    return True


def check_spaces(model):
    names = [norm(getattr(space, "Name", "") or getattr(space, "LongName", "")) for space in model.by_type("IfcSpace")]
    return all(any(token in name for name in names) for token in SPEC["required_space_tokens"])


def check_geometry(model):
    settings = geometry_settings()
    records = shaped_records(model, settings)
    if not records:
        return False
    mins = np.min([verts.min(axis=0) for _, verts in records], axis=0)
    maxs = np.max([verts.max(axis=0) for _, verts in records], axis=0)
    spans = maxs - mins
    for axis, idx in (("x", 0), ("y", 1), ("z", 2)):
        low, high = SPEC["bbox_ranges_m"][axis]
        if not (low <= float(spans[idx]) <= high):
            return False

    curtain_centroids = []
    for curtain in model.by_type("IfcCurtainWall"):
        try:
            curtain_centroids.append(product_centroid(settings, curtain))
        except Exception:
            continue
    tol = SPEC["curtain_edge_tolerance_m"]
    south_ok = any(abs(float(c[1]) - float(mins[1])) <= tol for c in curtain_centroids)
    east_ok = any(abs(float(c[0]) - float(maxs[0])) <= tol for c in curtain_centroids)
    if not (south_ok and east_ok):
        return False

    rear_ys = {}
    for space in model.by_type("IfcSpace"):
        name = norm(getattr(space, "Name", "") or getattr(space, "LongName", ""))
        for token in ("storage", "prep", "toilet"):
            if token in name:
                try:
                    rear_ys[token] = float(product_centroid(settings, space)[1])
                except Exception:
                    pass
    return set(rear_ys) == {"storage", "prep", "toilet"} and all(y >= SPEC["rear_space_min_y_m"] for y in rear_ys.values())


def evaluate(result_dir):
    path = Path(result_dir) / SPEC["required_output"]
    if not path.is_file() or path.stat().st_size < SPEC["min_file_bytes"]:
        return False
    model = ifcopenshell.open(str(path))
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
