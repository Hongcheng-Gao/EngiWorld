#!/usr/bin/env python3
import csv
import re
from pathlib import Path

import ifcopenshell


DESKTOP = Path("/home/user/Desktop")
import ifcopenshell.geom
import ifcopenshell.util.unit


SPEC = {
    "required_outputs": ("result.ifc", "result.csv"),
    "min_ifc_bytes": 500,
    "schema": "IFC4",
    "counts": {
        "IfcProject": 1,
        "IfcSite": 1,
        "IfcBuilding": 1,
        "IfcBuildingStorey": 1,
        "IfcWall": 4,
        "IfcSlab": 1,
        "IfcDoor": 1,
        "IfcOpeningElement": 1,
        "IfcRelVoidsElement": 1,
        "IfcRelFillsElement": 1,
        "IfcWorkSchedule": 1,
        "IfcTask": 4,
        "IfcRelSequence": 3,
    },
    "forbidden_counts": {
        "IfcSpace": 0,
        "IfcWindow": 0,
        "IfcBuildingElementProxy": 0,
        "IfcFurniture": 0,
        "IfcRoof": 0,
        "IfcColumn": 0,
        "IfcBeam": 0,
        "IfcStair": 0,
        "IfcFlowTerminal": 0,
    },
    "storey_name": "Level 00",
    "schedule_name": "Shell Sequence",
    "tasks": [
        ("Cast Slab", 2, ""),
        ("Build Walls", 4, "Cast Slab"),
        ("Install Door", 1, "Build Walls"),
        ("QC Handover", 1, "Install Door"),
    ],
    "slab": ("Shell Slab", (4.0, 3.0, 0.2)),
    "wall_height_m": 3.0,
    "wall_thickness_m": 0.2,
    "door": ("Shell Door", 0.9),
    "csv_headers": ["TaskName", "DurationDays", "DirectPredecessor"],
    "linear_tolerance_m": 0.08,
    "height_tolerance_m": 0.05,
    "thickness_tolerance_m": 0.04,
}


def emit(ok):
    print("true" if ok else "false")
    raise SystemExit(0)


def clean_name(value):
    return re.sub(r"\s+", " ", str(value or "").strip())


def approx(actual, expected, tol):
    return actual is not None and abs(float(actual) - float(expected)) <= float(tol)


def unit_scale(model):
    try:
        return float(ifcopenshell.util.unit.calculate_unit_scale(model))
    except Exception:
        return 1.0


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


def check_storey_and_geometry(model):
    storeys = model.by_type("IfcBuildingStorey")
    if len(storeys) != 1 or clean_name(storeys[0].Name) != SPEC["storey_name"]:
        return False
    for ifc_class in ("IfcWall", "IfcSlab", "IfcDoor"):
        for entity in model.by_type(ifc_class):
            storey = parent_storey(entity)
            if storey is None or clean_name(storey.Name) != SPEC["storey_name"]:
                return False
    slab = model.by_type("IfcSlab")[0]
    if clean_name(slab.Name) != SPEC["slab"][0]:
        return False
    bbox = shape_bbox(slab)
    if bbox is None or not dimensions_match(span(bbox), SPEC["slab"][1], SPEC["linear_tolerance_m"]):
        return False
    for wall in model.by_type("IfcWall"):
        bbox = shape_bbox(wall)
        if bbox is None:
            return False
        sx, sy, sz = span(bbox)
        if not approx(sz, SPEC["wall_height_m"], SPEC["height_tolerance_m"]):
            return False
        if not approx(min(sx, sy), SPEC["wall_thickness_m"], SPEC["thickness_tolerance_m"]):
            return False
    return True


def overall_width(entity, model):
    value = getattr(entity, "OverallWidth", None)
    if value in (None, 0, ""):
        return None
    raw = float(value)
    scaled = raw * unit_scale(model)
    return scaled if 0.05 <= scaled <= 20.0 else raw


def check_door_opening(model):
    door = model.by_type("IfcDoor")[0]
    if clean_name(door.Name) != SPEC["door"][0]:
        return False
    if not approx(overall_width(door, model), SPEC["door"][1], SPEC["linear_tolerance_m"]):
        return False
    rels = getattr(door, "FillsVoids", None) or []
    if len(rels) != 1:
        return False
    opening = rels[0].RelatingOpeningElement
    host_rels = getattr(opening, "VoidsElements", None) or []
    return len(host_rels) == 1 and host_rels[0].RelatingBuildingElement.is_a("IfcWall")


def duration_days(task):
    task_time = getattr(task, "TaskTime", None)
    duration = clean_name(getattr(task_time, "ScheduleDuration", ""))
    match = re.fullmatch(r"P([0-9]+)D", duration)
    return int(match.group(1)) if match else None


def check_schedule(model):
    schedules = model.by_type("IfcWorkSchedule")
    if len(schedules) != 1 or clean_name(schedules[0].Name) != SPEC["schedule_name"]:
        return False
    expected = {name: (days, pred) for name, days, pred in SPEC["tasks"]}
    tasks = {clean_name(task.Name): task for task in model.by_type("IfcTask")}
    if set(tasks) != set(expected):
        return False
    for name, (days, _) in expected.items():
        if duration_days(tasks[name]) != days:
            return False
    actual_sequences = {(clean_name(rel.RelatingProcess.Name), clean_name(rel.RelatedProcess.Name)) for rel in model.by_type("IfcRelSequence")}
    expected_sequences = {(pred, name) for name, (_, pred) in expected.items() if pred}
    return actual_sequences == expected_sequences


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
        f.seek(0)
        headers = next(csv.reader(f), [])
    return headers, rows


def check_csv_schedule(root):
    headers, rows = read_csv(root / "result.csv")
    if headers != SPEC["csv_headers"]:
        return False
    if len(rows) != len(SPEC["tasks"]):
        return False
    for row, expected in zip(rows, SPEC["tasks"]):
        name, days, pred = expected
        if clean_name(row.get("TaskName", "")) != name:
            return False
        if clean_name(row.get("DirectPredecessor", "")) != pred:
            return False
        try:
            if int(clean_name(row.get("DurationDays", ""))) != days:
                return False
        except Exception:
            return False
    return True


def evaluate():
    result_dir = DESKTOP
    if not result_dir.is_dir():
        return False
    ifc_path = result_dir / "result.ifc"
    csv_path = result_dir / "result.csv"
    if not ifc_path.is_file() or ifc_path.stat().st_size < SPEC["min_ifc_bytes"] or not csv_path.is_file() or csv_path.stat().st_size == 0:
        return False
    model = ifcopenshell.open(str(ifc_path))
    return (
        str(getattr(model, "schema", "")).upper().startswith(SPEC["schema"])
        and unique_global_ids(model)
        and check_counts(model)
        and check_storey_and_geometry(model)
        and check_door_opening(model)
        and check_schedule(model)
        and check_csv_schedule(result_dir)
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
