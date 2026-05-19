#!/usr/bin/env python3

import re

from pathlib import Path

DESKTOP = Path("C:/Users/user/Desktop")



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

        "IfcSpace": 7,

        "IfcWall": 8,

        "IfcSlab": 1,

        "IfcRoof": 1,

    },

    "min_counts": {"IfcDoor": 3, "IfcWindow": 8},

    "forbidden_counts": {"IfcBuildingElementProxy": 0, "IfcStair": 0, "IfcColumn": 0, "IfcBeam": 0},

    "required_space_tokens": ["lobby", "classroom a", "classroom b", "nap", "dining", "teacher", "toilet"],

    "bbox_ranges_m": {"x": (26.0, 30.0), "y": (22.0, 26.0), "z": (3.0, 4.2)},

    "footprint_ratio_range": (0.68, 0.82),

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

            faces = np.array(shape.geometry.faces, dtype=int).reshape(-1, 3) if shape.geometry.faces else np.zeros((0, 3), dtype=int)

        except Exception:

            continue

        if verts.size:

            records.append({"entity": product, "verts": verts, "faces": faces})

    return records





def horizontal_projected_area(record):

    area = 0.0

    verts = record["verts"]

    for tri in record["faces"]:

        pts = verts[tri]

        if np.ptp(pts[:, 2]) > 0.03:

            continue

        a, b, c = pts[:, :2]

        area += abs((a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1])) / 2.0)

    return area / 2.0





def check_geometry(model):

    records = shape_records(model)

    if not records:

        return False

    mins = np.min([r["verts"].min(axis=0) for r in records], axis=0)

    maxs = np.max([r["verts"].max(axis=0) for r in records], axis=0)

    spans = maxs - mins

    for axis, idx in (("x", 0), ("y", 1), ("z", 2)):

        low, high = SPEC["bbox_ranges_m"][axis]

        if not (low <= float(spans[idx]) <= high):

            return False

    slab_records = [r for r in records if r["entity"].is_a("IfcSlab")]

    if len(slab_records) != 1:

        return False

    rectangle_area = float(spans[0] * spans[1])

    ratio = horizontal_projected_area(slab_records[0]) / rectangle_area if rectangle_area > 0 else 0.0

    low, high = SPEC["footprint_ratio_range"]

    return low <= ratio <= high





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

