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

        "IfcBuildingStorey": 2,

        "IfcSpace": 1,

        "IfcWall": 4,

        "IfcSlab": 2,

        "IfcRamp": 1,

    },

    "min_counts": {"IfcStair": 1, "IfcDoor": 1, "IfcWindow": 1},

    "forbidden_counts": {"IfcBuildingElementProxy": 0, "IfcColumn": 0, "IfcBeam": 0},

    "required_space_tokens": ["plant"],

    "bbox_ranges_m": {"x": (22.0, 26.0), "y": (14.5, 17.5), "z": (3.2, 4.5)},

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





def check_geometry(model):

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

            records.append(verts)

    if not records:

        return False

    mins = np.min([verts.min(axis=0) for verts in records], axis=0)

    maxs = np.max([verts.max(axis=0) for verts in records], axis=0)

    spans = maxs - mins

    for axis, idx in (("x", 0), ("y", 1), ("z", 2)):

        low, high = SPEC["bbox_ranges_m"][axis]

        if not (low <= float(spans[idx]) <= high):

            return False

    return True





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

