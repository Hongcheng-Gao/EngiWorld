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
    "Ground Admin",
    "Level 2 Admin",
    "Level 3 Admin"
  ],
  "bbox_ranges_m": {
    "x": [
      19.4,
      21.3
    ],
    "y": [
      11.4,
      13.3
    ],
    "z": [
      7.9,
      11.8
    ]
  },
  "exact_counts": {
    "IfcBeam": 7,
    "IfcBuilding": 1,
    "IfcBuildingStorey": 3,
    "IfcColumn": 12,
    "IfcProject": 1,
    "IfcRoof": 1,
    "IfcSite": 1,
    "IfcSpace": 9,
    "IfcWall": 18
  },
  "forbidden": [
    "IfcBuildingElementProxy",
    "IfcCurtainWall",
    "IfcDoor",
    "IfcWindow"
  ],
  "min_counts": {
    "IfcSlab": 3
  },
  "min_file_bytes": 20000,
  "min_shaped_products": 22,
  "space_tokens": [
    "Admin G West",
    "Admin G Centre",
    "Admin G East",
    "Admin L2 West",
    "Admin L2 Centre",
    "Admin L2 East",
    "Admin L3 West",
    "Admin L3 Centre",
    "Admin L3 East"
  ],
  "storey_tokens": [
    "Ground Floor",
    "Level 2",
    "Level 3"
  ]
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


def evaluate(result_dir):
    result_dir = Path(result_dir)
    result = result_dir / "result.ifc"
    if not result.is_file() or result.stat().st_size < SPEC["min_file_bytes"]:
        return False
    init = init_path_for(result_dir)
    if init is not None and init.is_file() and sha256(init) == sha256(result):
        return False
    model = ifcopenshell.open(str(result))
    return (
        str(getattr(model, "schema", "")).upper().startswith("IFC4")
        and app_is_revit(model)
        and unique_global_ids(model)
        and check_counts(model)
        and check_names(model)
        and check_geometry(model)
    )


def main():
    try:
        result_dir = Path(os.environ.get("RESULT_DIR", str(DESKTOP)))
        finish(evaluate(result_dir))
    except Exception:
        finish(False)


if __name__ == "__main__":
    main()
