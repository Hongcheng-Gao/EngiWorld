#!/usr/bin/env python3
import hashlib
import math
import os
import re
from pathlib import Path

import ifcopenshell
import ifcopenshell.geom
import numpy as np

SPEC = {
  "absent_space_tokens": [
    "Ground Lab",
    "Upper Lab"
  ],
  "bbox_ranges_m": {
    "x": [
      9.4,
      11.2
    ],
    "y": [
      6.4,
      8.2
    ],
    "z": [
      4.9,
      8.5
    ]
  },
  "exact_counts": {
    "IfcBuilding": 1,
    "IfcBuildingStorey": 2,
    "IfcProject": 1,
    "IfcRoof": 1,
    "IfcSite": 1,
    "IfcSpace": 4,
    "IfcWall": 10
  },
  "forbidden": [
    "IfcBeam",
    "IfcBuildingElementProxy",
    "IfcColumn",
    "IfcCurtainWall",
    "IfcDoor",
    "IfcWindow"
  ],
  "min_counts": {
    "IfcSlab": 2
  },
  "min_file_bytes": 20000,
  "min_shaped_products": 12,
  "space_tokens": [
    "Lab",
    "Prep",
    "Lab Upper",
    "Prep Upper"
  ],
  "storey_tokens": [
    "Ground Floor",
    "Level 2"
  ],
  "space_levels": {
    "Lab": 0,
    "Prep": 0,
    "Lab Upper": 1,
    "Prep Upper": 1
  },
  "roof_slope_min_m": 0.2
}
DESKTOP = Path("C:/Users/user/Desktop")


def finish(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def norm(value):
    text = str(value or "").replace("_", " ").replace("-", " ").lower()
    return re.sub(r"\s+", " ", text).strip()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def app_is_revit(model):
    apps = " ".join(
        " ".join(str(getattr(app, attr, "") or "") for attr in ("ApplicationIdentifier", "ApplicationFullName", "Version"))
        for app in model.by_type("IfcApplication")
    )
    header = ""
    try:
        header = model.wrapped_data.header().file_name.originating_system or ""
    except Exception:
        pass
    text = f"{apps} {header}".lower()
    return "revit" in text and "archicad" not in text


def unique_global_ids(model):
    gids = [entity.GlobalId for entity in model.by_type("IfcRoot") if getattr(entity, "GlobalId", None)]
    return bool(gids) and len(gids) == len(set(gids))


def entity_count(model, ifc_class):
    return len(model.by_type(ifc_class))


def check_counts(model):
    for ifc_class, expected in SPEC["exact_counts"].items():
        if entity_count(model, ifc_class) != expected:
            return False
    for ifc_class, minimum in SPEC["min_counts"].items():
        if entity_count(model, ifc_class) < minimum:
            return False
    for ifc_class in SPEC["forbidden"]:
        if entity_count(model, ifc_class) != 0:
            return False
    return True


def space_label(space):
    return norm(f"{getattr(space, 'Name', '')} {getattr(space, 'LongName', '')}")


def check_names(model):
    storey_names = [norm(getattr(s, "Name", "")) for s in model.by_type("IfcBuildingStorey")]
    for token in SPEC["storey_tokens"]:
        if not any(norm(token) in name for name in storey_names):
            return False
    space_names = [space_label(s) for s in model.by_type("IfcSpace")]
    for token in SPEC["space_tokens"]:
        if not any(norm(token) in name for name in space_names):
            return False
    for token in SPEC["absent_space_tokens"]:
        if any(norm(token) in name for name in space_names):
            return False
    return True


def shape_records(model):
    settings = ifcopenshell.geom.settings()
    try:
        settings.set(settings.USE_WORLD_COORDS, True)
    except Exception:
        pass
    records = []
    for product in model.by_type("IfcProduct"):
        if product.is_a("IfcOpeningElement") or not getattr(product, "Representation", None):
            continue
        try:
            shape = ifcopenshell.geom.create_shape(settings, product)
            verts = np.array(shape.geometry.verts, dtype=float).reshape(-1, 3)
        except Exception:
            continue
        if verts.size:
            records.append((product, verts))
    return records


def check_geometry(model):
    records = shape_records(model)
    if len(records) < SPEC["min_shaped_products"]:
        return False
    mins = np.min([verts.min(axis=0) for _, verts in records], axis=0)
    maxs = np.max([verts.max(axis=0) for _, verts in records], axis=0)
    spans = maxs - mins
    for axis, idx in (("x", 0), ("y", 1), ("z", 2)):
        low, high = SPEC["bbox_ranges_m"][axis]
        value = float(spans[idx])
        if not (low <= value <= high) or not math.isfinite(value):
            return False
    return True


def init_path_for(result_dir):
    local = Path(result_dir).parent / "init_file" / "init.ifc"
    if local.is_file():
        return local
    remote = DESKTOP / "init.ifc"
    return remote if remote.is_file() else None



def product_bounds(product):
    settings = ifcopenshell.geom.settings()
    try:
        settings.set(settings.USE_WORLD_COORDS, True)
    except Exception:
        pass
    try:
        shape = ifcopenshell.geom.create_shape(settings, product)
        verts = np.array(shape.geometry.verts, dtype=float).reshape(-1, 3)
    except Exception:
        return None
    if not verts.size:
        return None
    return tuple(float(value) for value in (*verts.min(axis=0), *verts.max(axis=0)))


def bounds_close(first, second, tolerance=0.015):
    return first is not None and second is not None and all(abs(a - b) <= tolerance for a, b in zip(first, second))


def preserved_class_geometry(init_model, result_model, ifc_class):
    init_bounds = [b for item in init_model.by_type(ifc_class) if (b := product_bounds(item)) is not None]
    result_bounds = [b for item in result_model.by_type(ifc_class) if (b := product_bounds(item)) is not None]
    used = set()
    for expected in init_bounds:
        match = next((index for index, actual in enumerate(result_bounds) if index not in used and bounds_close(actual, expected)), None)
        if match is None:
            return False
        used.add(match)
    return True


def exact_space(model, token):
    wanted = norm(token)
    exact = [space for space in model.by_type("IfcSpace") if norm(getattr(space, "LongName", "")) == wanted]
    if len(exact) == 1:
        return exact[0]
    matches = [space for space in model.by_type("IfcSpace") if wanted in space_label(space)]
    return matches[0] if len(matches) == 1 else None


def bounds_volume(bounds):
    return max(0.0, bounds[3] - bounds[0]) * max(0.0, bounds[4] - bounds[1]) * max(0.0, bounds[5] - bounds[2])


def overlap_volume(first, second):
    spans = [max(0.0, min(first[i + 3], second[i + 3]) - max(first[i], second[i])) for i in range(3)]
    return spans[0] * spans[1] * spans[2]


def check_space_geometry(init_model, result_model):
    init_spaces = init_model.by_type("IfcSpace")
    result_spaces = result_model.by_type("IfcSpace")
    init_records = [(space, product_bounds(space)) for space in init_spaces]
    result_records = [(space, product_bounds(space)) for space in result_spaces]
    if any(bounds is None for _, bounds in init_records + result_records):
        return False

    init_total = sum(bounds_volume(bounds) for _, bounds in init_records)
    result_total = sum(bounds_volume(bounds) for _, bounds in result_records)
    if init_total <= 0 or not (0.84 <= result_total / init_total <= 1.02):
        return False
    envelope = (
        min(bounds[0] for _, bounds in init_records), min(bounds[1] for _, bounds in init_records), min(bounds[2] for _, bounds in init_records),
        max(bounds[3] for _, bounds in init_records), max(bounds[4] for _, bounds in init_records), max(bounds[5] for _, bounds in init_records),
    )
    for _, bounds in result_records:
        if any(bounds[i] < envelope[i] - 0.02 for i in range(3)) or any(bounds[i + 3] > envelope[i + 3] + 0.02 for i in range(3)):
            return False
    for index, (_, first) in enumerate(result_records):
        for _, second in result_records[index + 1:]:
            if overlap_volume(first, second) > 1.0e-5:
                return False

    z_levels = []
    for _, bounds in result_records:
        if not any(abs(bounds[2] - level) <= 0.05 for level in z_levels):
            z_levels.append(bounds[2])
    z_levels.sort()
    for token, expected_index in SPEC.get("space_levels", {}).items():
        space = exact_space(result_model, token)
        if space is None:
            return False
        bounds = product_bounds(space)
        actual_index = min(range(len(z_levels)), key=lambda index: abs(bounds[2] - z_levels[index]))
        if actual_index != int(expected_index):
            return False
    for rule in SPEC.get("axis_orders", []):
        axis = {"x": 0, "y": 1, "z": 2}[rule["axis"]]
        centers = []
        for token in rule["tokens"]:
            space = exact_space(result_model, token)
            if space is None:
                return False
            bounds = product_bounds(space)
            centers.append((bounds[axis] + bounds[axis + 3]) / 2.0)
        if any(second <= first + 0.05 for first, second in zip(centers, centers[1:])):
            return False
    return True


def check_preserved_geometry(init_model, result_model):
    return all(preserved_class_geometry(init_model, result_model, ifc_class) for ifc_class in ("IfcWall", "IfcSlab", "IfcColumn", "IfcBeam"))


def check_sloped_roof(model):
    minimum = SPEC.get("roof_slope_min_m")
    if minimum is None:
        return True
    slabs = [slab for slab in model.by_type("IfcSlab") if str(getattr(slab, "PredefinedType", "")).upper() == "ROOF"]
    bounds = [product_bounds(slab) for slab in slabs]
    if len(bounds) < 2 or any(item is None for item in bounds):
        return False
    return all(item[5] - item[2] >= float(minimum) for item in bounds)

def evaluate(result_dir):
    result_dir = Path(result_dir)
    result = result_dir / "result.ifc"
    if not result.is_file() or result.stat().st_size < SPEC["min_file_bytes"]:
        return False
    init = init_path_for(result_dir)
    if init is not None and init.is_file() and sha256(init) == sha256(result):
        return False
    if init is None or not init.is_file():
        return False
    model = ifcopenshell.open(str(result))
    init_model = ifcopenshell.open(str(init))
    return (
        str(getattr(model, "schema", "")).upper().startswith("IFC4")
        and app_is_revit(model)
        and unique_global_ids(model)
        and check_counts(model)
        and check_names(model)
        and check_geometry(model)
        and check_preserved_geometry(init_model, model)
        and check_space_geometry(init_model, model)
        and check_sloped_roof(model)
    )


def main():
    try:
        result_dir = Path(os.environ.get("RESULT_DIR", str(DESKTOP)))
        finish(evaluate(result_dir))
    except Exception:
        finish(False)


if __name__ == "__main__":
    main()
