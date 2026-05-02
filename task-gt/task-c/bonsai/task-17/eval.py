#!/usr/bin/env python3
import csv
import re
from pathlib import Path

import ifcopenshell


DESKTOP = Path("/home/user/Desktop")
import ifcopenshell.geom


SPEC = {
    "required_outputs": ("result.ifc", "result.csv"),
    "min_ifc_bytes": 500,
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
        "IfcDistributionPort": 13,
        "IfcRelConnectsPorts": 12,
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
    "storey_name": "Ground Floor",
    "system_name": "Supply Air",
    "products": {
        "Bend Fitting": ("IfcDuctFitting", 2, 4),
        "Branch Segment": ("IfcDuctSegment", 2, 4),
        "Main Segment 1": ("IfcDuctSegment", 2, 2),
        "Main Segment 2": ("IfcDuctSegment", 2, 4),
        "Terminal East": ("IfcAirTerminal", 1, 2),
        "Terminal North": ("IfcAirTerminal", 1, 2),
        "Transition Fitting": ("IfcDuctFitting", 3, 6),
    },
    "csv_headers": ["GlobalId", "Class", "Name", "SystemName", "PortCount", "ConnectedToCount"],
    "linear_tolerance_m": 0.08,
}


def emit(ok):
    print("true" if ok else "false")
    raise SystemExit(0)


def clean_name(value):
    return re.sub(r"\s+", " ", str(value or "").strip())


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


def nested_ports(entity):
    ports = []
    for rel in getattr(entity, "IsNestedBy", None) or []:
        for obj in getattr(rel, "RelatedObjects", None) or []:
            if obj.is_a("IfcDistributionPort"):
                ports.append(obj)
    return ports


def connected_relation_count(port):
    seen = set()
    for rel in (getattr(port, "ConnectedTo", None) or []) + (getattr(port, "ConnectedFrom", None) or []):
        seen.add(rel.id())
    return len(seen)


def check_system(model):
    storeys = model.by_type("IfcBuildingStorey")
    if len(storeys) != 1 or clean_name(storeys[0].Name) != SPEC["storey_name"]:
        return False
    system = model.by_type("IfcDistributionSystem")
    if len(system) != 1 or clean_name(system[0].Name) != SPEC["system_name"]:
        return False
    rels = model.by_type("IfcRelAssignsToGroup")
    if len(rels) != 1 or rels[0].RelatingGroup.id() != system[0].id():
        return False
    related = {clean_name(obj.Name): obj for obj in rels[0].RelatedObjects}
    if set(related) != set(SPEC["products"]):
        return False
    for name, entity in related.items():
        if entity.is_a() != SPEC["products"][name][0]:
            return False
        if parent_storey(entity) is None or clean_name(parent_storey(entity).Name) != SPEC["storey_name"]:
            return False
    return True


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
        f.seek(0)
        headers = next(csv.reader(f), [])
    return headers, rows


def check_csv_export(root, model):
    headers, rows = read_csv(root / "result.csv")
    if headers != SPEC["csv_headers"] or len(rows) != len(SPEC["products"]):
        return False
    system = model.by_type("IfcDistributionSystem")[0]
    related = {clean_name(obj.Name): obj for rel in model.by_type("IfcRelAssignsToGroup") if rel.RelatingGroup.id() == system.id() for obj in rel.RelatedObjects}
    by_gid = {}
    for name, entity in related.items():
        ports = nested_ports(entity)
        by_gid[entity.GlobalId] = (entity.is_a(), name, clean_name(system.Name), len(ports), sum(connected_relation_count(p) for p in ports))
    if set(row.get("GlobalId", "") for row in rows) != set(by_gid):
        return False
    for row in rows:
        spec = by_gid.get(row.get("GlobalId", ""))
        if spec is None:
            return False
        if row.get("Class", "") != spec[0]:
            return False
        if clean_name(row.get("Name", "")) != spec[1]:
            return False
        if clean_name(row.get("SystemName", "")) != spec[2]:
            return False
        if int(row.get("PortCount", "")) != spec[3]:
            return False
        if int(row.get("ConnectedToCount", "")) != spec[4]:
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
        and check_system(model)
        and check_csv_export(result_dir, model)
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
