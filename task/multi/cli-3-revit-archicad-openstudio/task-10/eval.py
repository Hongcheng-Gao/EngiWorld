from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

CASE_ID = "multi-cli-3-revit-archicad-openstudio-task-10-windows"
SPACES = {
    "RECEPTION-L1": ("RECEPTION-L1-ZN", 45.24, "RECEPTION-PUBLIC-LOAD", 0.12, 8.0, 6.0, 8.0, "Level 1"),
    "STUDIO-L2": ("STUDIO-L2-ZN", 45.24, "STUDIO-HIGH-EQUIPMENT", 0.08, 12.0, 30.0, 10.0, "Level 2"),
    "ARCHIVE-L3": ("ARCHIVE-L3-ZN", 45.24, "ARCHIVE-LOW-LIGHTING", 0.01, 3.0, 1.0, 5.0, "Level 3"),
}
OSM_SCHEDULES = {
    "RECEPTION-L1": "RECEPTION-L1 ReceptionPublicLoad",
    "STUDIO-L2": "STUDIO-L2 StudioHighEquipment",
    "ARCHIVE-L3": "ARCHIVE-L3 ArchiveLowLighting",
}
OSM_SCHEDULE_VALUES = {
    "RECEPTION-L1": [(6, 0.05), (8, 0.35), (18, 1.00), (22, 0.20), (24, 0.05)],
    "STUDIO-L2": [(7, 0.10), (8, 0.50), (20, 1.00), (23, 0.25), (24, 0.10)],
    "ARCHIVE-L3": [(8, 0.01), (18, 0.10), (24, 0.01)],
}
WALL_IDS = {
    "1ofMKbkXL90x1LpPKmrjWL", "1ofMKbkXL90x1LpPKmrjWI", "1ofMKbkXL90x1LpPKmrjWJ", "1ofMKbkXL90x1LpPKmrjWG",
    "1ofMKbkXL90x1LpPKmrjWH", "1ofMKbkXL90x1LpPKmrjWU", "1ofMKbkXL90x1LpPKmrjWV", "1ofMKbkXL90x1LpPKmrjWS",
    "1ofMKbkXL90x1LpPKmrjWT", "1ofMKbkXL90x1LpPKmrjWQ", "1ofMKbkXL90x1LpPKmrjWR", "1ofMKbkXL90x1LpPKmrjWO",
}
SLAB_IDS = {"1ofMKbkXL90x1LpPKmrjW7", "1ofMKbkXL90x1LpPKmrjWE", "1ofMKbkXL90x1LpPKmrjW9"}
RETAINED_SPACE_IDS = {"RECEPTION-L1": "1ofMKbkXL90x1LpPKmrjdb", "STUDIO-L2": "1ofMKbkXL90x1LpPKmrjdZ", "ARCHIVE-L3": "1ofMKbkXL90x1LpPKmrjdX"}
STOREY_IDS = {"Level 1": "1ofMKbkXL90x1LpPKmrjLf", "Level 2": "1ofMKbkXL90x1LpPKmrjWN", "Level 3": "1ofMKbkXL90x1LpPKmrjWK"}
ROOF_ID = "2LzO4ZliP00xdSmna1lWP8"
TOTAL_AREA = 135.72
SPACE_BOUNDS = {
    "RECEPTION-L1": (0.1, 7.9, 0.1, 5.9, 0.0, 2.4384),
    "STUDIO-L2": (0.1, 7.9, 0.1, 5.9, 3.0, 5.4384),
    "ARCHIVE-L3": (0.1, 7.9, 0.1, 5.9, 6.0, 8.4384),
}
GEOMETRIC_CLASSES = (
    "IfcSpace", "IfcWall", "IfcSlab", "IfcRoof", "IfcDoor", "IfcWindow",
    "IfcOpeningElement",
)
IMMUTABLE = {
    "init.ifc": "ee206e12a660a5d45733c6ac6559d3508ddcc223292ff1becb204e98b0ef6160",
    "workflow_spec.json": "7b10a33f3df9f4b3e53c26a40e516d7bf8e5b8d1018c6f544320bce754f73907",
    "weather.epw": "369531a54a55856f411e63a80cb9e91a4b4dc2e9ee8e3623d24a809eb0becfc1",
    "archicad_ifc4_translator.json": "e1698beeeb82d9387f8576b660790be2a737e28da91220fc01a2a06a3a8153ce",
    "run_revit_stage.ps1": "a67bf4c81e43adabddcb7880009165df464c7d743d4b31302eac03780f736785",
    "EngiWorld.BimBridge.dll": "ae9c05d2cd3a45410ce3fb1f11f12d39dc3e353b8cdccb1bdad0b6e1592414b8",
    "EngiWorld.BimBridge.addin": "4a5450d6a0e45ffc10ef133503c6342078dc3ce0af8e45e1212d6d61da5851f6",
    "run_archicad_stage.ps1": "d9648cd8507d0ffeafe5a5ee783e97189073962e39d9825595e7f11aa5593728",
    "openstudio_ifc_to_energy.rb": "46594f431b9d1bb92fc7e253a385d517846d09f41629239e1c3434d6c4275645",
    "extract_ifc_space_geometry.py": "5142ee744bcdc26cec1a4a29e1fb9e3b332e4195b8148a57bf1ce3acfa99134a",
    "run_openstudio_stage.ps1": "64197da212e9b0584ff5846e26d405afb8d2a5c10b82100b938f47cd49b15246",
}
REQUIRED = list(IMMUTABLE) + [
    "stage1.ifc", "revit_handoff.json", "stage2.ifc", "archicad_handoff.json",
    "archicad_validation_report.json", "native_stage_log.json", "result.osm",
    "in.idf", "workflow.osw", "flow_report.json", "model_summary.csv",
    "energy_report.csv", "run/eplusout.sql", "run/eplusout.err",
]


def root_dir() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).resolve()
    desktop = Path(r"C:\Users\user\Desktop")
    return desktop if desktop.exists() else Path.cwd().resolve()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} is not an object")
    return value


def close(a: Any, b: Any, tolerance: float = 0.05) -> bool:
    try:
        return math.isclose(float(a), float(b), rel_tol=1e-7, abs_tol=tolerance)
    except (TypeError, ValueError):
        return False


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def named_spaces(model: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for space in model.by_type("IfcSpace"):
        for candidate in (getattr(space, "LongName", None), getattr(space, "Name", None)):
            if candidate in SPACES:
                result[str(candidate)] = space
    return result


def psets(entity: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    import ifcopenshell.util.element  # type: ignore
    return (
        ifcopenshell.util.element.get_psets(entity, psets_only=True),
        ifcopenshell.util.element.get_psets(entity, qtos_only=True),
    )


def bbox(entity: Any, settings: Any) -> tuple[float, ...]:
    import ifcopenshell.geom  # type: ignore
    shape = ifcopenshell.geom.create_shape(settings, entity)
    verts = list(shape.geometry.verts)
    points = [(float(verts[i]), float(verts[i + 1]), float(verts[i + 2])) for i in range(0, len(verts), 3)]
    if not points:
        raise ValueError("empty geometry")
    return tuple(round(v, 5) for v in (
        min(p[0] for p in points), max(p[0] for p in points),
        min(p[1] for p in points), max(p[1] for p in points),
        min(p[2] for p in points), max(p[2] for p in points),
    ))


def mesh_data(entity: Any, settings: Any, precision: int = 5) -> tuple[list[tuple[float, ...]], list[tuple[int, int, int]]]:
    import ifcopenshell.geom  # type: ignore
    shape = ifcopenshell.geom.create_shape(settings, entity)
    values = list(shape.geometry.verts)
    points = [tuple(round(float(values[i + j]), precision) for j in range(3)) for i in range(0, len(values), 3)]
    faces = list(shape.geometry.faces)
    triangles = [tuple(int(faces[i + j]) for j in range(3)) for i in range(0, len(faces), 3)]
    return points, triangles


def mesh_signature(entity: Any, settings: Any) -> tuple[tuple[tuple[float, ...], ...], tuple[tuple[tuple[float, ...], ...], ...]]:
    points, triangles = mesh_data(entity, settings, 4)
    resolved = [tuple(sorted((points[a], points[b], points[c]))) for a, b, c in triangles]
    return tuple(sorted(set(points))), tuple(sorted(resolved))


def mesh_metrics(entity: Any, settings: Any, precision: int = 5) -> dict[str, Any]:
    points, triangles = mesh_data(entity, settings, precision)
    if not points or not triangles:
        raise ValueError("empty mesh")
    edge_counts: Counter[tuple[int, int]] = Counter()
    volume6 = 0.0
    area = 0.0
    planes: dict[tuple[float, ...], list[tuple[tuple[int, int, int], float]]] = defaultdict(list)
    for indices in triangles:
        a, b, c = (points[index] for index in indices)
        u = tuple(b[i] - a[i] for i in range(3)); v = tuple(c[i] - a[i] for i in range(3))
        normal = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        length = math.sqrt(sum(value * value for value in normal))
        if length <= 1e-9:
            raise ValueError("degenerate triangle")
        unit = tuple(value / length for value in normal)
        first = next((value for value in unit if abs(value) > 1e-8), 1.0)
        if first < 0:
            unit = tuple(-value for value in unit)
        distance = sum(unit[i] * a[i] for i in range(3))
        plane = tuple(round(value, 5) for value in unit) + (round(distance, precision),)
        triangle_area = length / 2.0
        planes[plane].append((indices, triangle_area))
        area += triangle_area
        volume6 += a[0] * (b[1] * c[2] - b[2] * c[1]) + a[1] * (b[2] * c[0] - b[0] * c[2]) + a[2] * (b[0] * c[1] - b[1] * c[0])
        for left, right in ((indices[0], indices[1]), (indices[1], indices[2]), (indices[2], indices[0])):
            edge_counts[tuple(sorted((left, right)))] += 1
    canonical_faces = []
    for plane, entries in planes.items():
        plane_edges: Counter[tuple[tuple[float, ...], tuple[float, ...]]] = Counter()
        for indices, _ in entries:
            for left, right in ((indices[0], indices[1]), (indices[1], indices[2]), (indices[2], indices[0])):
                plane_edges[tuple(sorted((points[left], points[right])))] += 1
        boundary = tuple(sorted(edge for edge, count in plane_edges.items() if count % 2 == 1))
        adjacency: dict[tuple[float, ...], set[tuple[float, ...]]] = defaultdict(set)
        perimeter = 0.0
        for left, right in boundary:
            adjacency[left].add(right); adjacency[right].add(left)
            perimeter += math.dist(left, right)
        remaining = set(adjacency)
        loops = 0
        while remaining:
            loops += 1
            stack = [remaining.pop()]
            while stack:
                for neighbor in adjacency[stack.pop()]:
                    if neighbor in remaining:
                        remaining.remove(neighbor); stack.append(neighbor)
        boundary_ok = bool(boundary) and all(len(neighbors) == 2 for neighbors in adjacency.values())
        canonical_faces.append((
            plane,
            round(sum(value for _, value in entries), precision),
            round(perimeter, precision),
            loops,
            boundary_ok,
        ))
    return {
        "points": tuple(sorted(set(points))),
        "triangles": tuple(sorted(tuple(sorted((points[a], points[b], points[c]))) for a, b, c in triangles)),
        "triangle_count": len(triangles),
        "canonical_faces": tuple(sorted(canonical_faces)),
        "closed": bool(edge_counts) and all(count == 2 for count in edge_counts.values()),
        "edge_degrees": tuple(sorted(edge_counts.values())),
        "volume": round(abs(volume6) / 6.0, precision),
        "area": round(area, precision),
    }


def mesh_equivalent(a: Any, b: Any, settings: Any) -> bool:
    left, right = mesh_metrics(a, settings), mesh_metrics(b, settings)
    unmatched = list(right["canonical_faces"])
    faces_equal = True
    for face_a in left["canonical_faces"]:
        match = next((
            index for index, face_b in enumerate(unmatched)
            if all(close(x, y, 3e-5) for x, y in zip(face_a[0], face_b[0]))
            and close(face_a[1], face_b[1], 0.02)
            and close(face_a[2], face_b[2], 0.02)
            and face_a[3] == face_b[3]
        ), None)
        if match is None:
            faces_equal = False
            break
        unmatched.pop(match)
    return (
        bbox(a, settings) == bbox(b, settings)
        and left["closed"] and right["closed"]
        and close(left["volume"], right["volume"], 0.02)
        and close(left["area"], right["area"], 0.02)
        and len(left["canonical_faces"]) == len(right["canonical_faces"])
        and faces_equal and not unmatched
    )


def containing_storeys(entity: Any) -> set[str]:
    decomposed = {
        str(rel.RelatingObject.GlobalId) for rel in getattr(entity, "Decomposes", [])
        if getattr(rel, "RelatingObject", None) and rel.RelatingObject.is_a("IfcBuildingStorey")
    }
    contained = {
        str(rel.RelatingStructure.GlobalId) for rel in getattr(entity, "ContainedInStructure", [])
        if getattr(rel, "RelatingStructure", None) and rel.RelatingStructure.is_a("IfcBuildingStorey")
    }
    return decomposed | contained


def effective_storeys(entity: Any) -> set[str]:
    direct = containing_storeys(entity)
    if direct or not entity.is_a("IfcOpeningElement"):
        return direct
    return {
        guid
        for relation in getattr(entity, "VoidsElements", [])
        for guid in containing_storeys(relation.RelatingBuildingElement)
    }


def archicad_build(value: Any) -> int | None:
    match = re.search(r"Archicad\s+27\s+build\s+(\d+)", str(value), re.I)
    return int(match.group(1)) if match else None


def check_space_geometry(space: Any, name: str, settings: Any, label: str, errors: list[str]) -> None:
    expected = SPACE_BOUNDS[name]
    actual = bbox(space, settings)
    metrics = mesh_metrics(space, settings)
    width = actual[1] - actual[0]
    depth = actual[3] - actual[2]
    height = actual[5] - actual[4]
    expected_area = SPACES[name][1]
    add(errors, all(close(a, b, 0.002) for a, b in zip(actual, expected)), f"{label}:space_bbox:{name}")
    add(errors, close(width * depth, expected_area, 0.01) and close(height, 2.4384, 0.002), f"{label}:space_dimensions:{name}")
    add(errors, metrics["closed"], f"{label}:space_not_closed:{name}")
    add(errors, close(metrics["volume"], expected_area * height, 0.03), f"{label}:space_volume:{name}")
    horizontal = [face for face in metrics["canonical_faces"] if close(abs(face[0][2]), 1.0, 1e-5)]
    add(errors, len(horizontal) == 2 and all(close(face[1], expected_area, 0.02) for face in horizontal), f"{label}:space_floor_or_ceiling:{name}")


def wall_seed_shape_ok(entity: Any, seed: Any, openings: list[Any], wall: dict[str, Any], settings: Any) -> bool:
    points, triangles = mesh_signature(entity, settings)
    metrics = mesh_metrics(entity, settings)
    x1, y1, x2, y2 = (float(wall[k]) for k in ("x1_m", "y1_m", "x2_m", "y2_m"))
    if not points or not triangles:
        return False
    if close(y1, y2, 1e-6):
        permitted_a = {round(y1 - 0.1, 4), round(y1 + 0.1, 4)}
        axis_ok = all(p[1] in permitted_a and min(x1, x2) - 0.11 <= p[0] <= max(x1, x2) + 0.11 for p in points)
    else:
        permitted_a = {round(x1 - 0.1, 4), round(x1 + 0.1, 4)}
        axis_ok = all(p[0] in permitted_a and min(y1, y2) - 0.11 <= p[1] <= max(y1, y2) + 0.11 for p in points)
    seed_volume = mesh_metrics(seed, settings)["volume"]
    opening_volume = sum(mesh_metrics(opening, settings)["volume"] for opening in openings)
    z0 = {"Level 1": 0.0, "Level 2": 3.0, "Level 3": 6.0}.get(str(wall.get("storey")), -999.0)
    return axis_ok and all(z0 - 1e-4 <= p[2] <= z0 + 3.0001 for p in points) and metrics["closed"] and metrics["volume"] > 0 and close(metrics["volume"] + opening_volume, seed_volume, 0.01)


def check_ifc(path: Path, label: str, errors: list[str], require_revit: bool = False) -> tuple[Any, dict[str, Any]]:
    try:
        import ifcopenshell  # type: ignore
        model = ifcopenshell.open(str(path))
    except Exception as exc:
        errors.append(f"{label}:ifc_parse:{type(exc).__name__}")
        return None, {}
    add(errors, model.schema == "IFC4", f"{label}:schema_not_ifc4")
    text = path.read_text(encoding="utf-8", errors="ignore")
    if require_revit:
        add(errors, "Autodesk Revit 25." in text[:3000], f"{label}:not_revit_2025_export")
    roots = model.by_type("IfcRoot")
    root_ids = [str(item.GlobalId) for item in roots]
    add(errors, len(root_ids) == len(set(root_ids)), f"{label}:duplicate_root_guid")
    return model, {"text": text, "roots": {str(x.GlobalId): x.is_a() for x in roots}}


def check_stage1(init: Any, stage1: Any, spec: dict[str, Any], errors: list[str]) -> None:
    if init is None or stage1 is None:
        return
    expected_counts = {
        "IfcSpace": 3, "IfcWall": 12, "IfcSlab": 3, "IfcRoof": 1,
        "IfcDoor": 3, "IfcWindow": 3, "IfcOpeningElement": 6,
        "IfcRelVoidsElement": 6, "IfcRelFillsElement": 6,
    }
    for cls, expected in expected_counts.items():
        add(errors, len(stage1.by_type(cls)) == expected, f"stage1.ifc:count:{cls}")
    spaces = named_spaces(stage1)
    add(errors, set(spaces) == set(SPACES), "stage1.ifc:named_space_set")
    for name, guid in RETAINED_SPACE_IDS.items():
        add(errors, getattr(spaces.get(name), "GlobalId", None) == guid, f"stage1.ifc:retained_space_guid:{name}")
    areas = []
    property_map = {
        "ThermalZone": 0, "ScheduleCategory": 2, "PeoplePerM2": 3,
        "LightingPowerDensityWPerM2": 4, "EquipmentPowerDensityWPerM2": 5,
        "OutdoorAirLPerSPerson": 6,
    }
    for name, expected in SPACES.items():
        space = spaces.get(name)
        if space is None:
            continue
        add(errors, bool(space.Representation), f"stage1.ifc:space_no_geometry:{name}")
        add(errors, containing_storeys(space) == {STOREY_IDS[expected[7]]}, f"stage1.ifc:space_storey:{name}")
        ps, qt = psets(space)
        energy = ps.get("EngiWorld_EnergyHandoff", {})
        quantity = qt.get("Qto_SpaceBaseQuantities", {})
        area = quantity.get("GrossFloorArea")
        add(errors, close(area, expected[1]), f"stage1.ifc:area:{name}")
        if area is not None:
            areas.append(float(area))
        for key, index in property_map.items():
            wanted = expected[index]
            actual = energy.get(key)
            ok = close(actual, wanted, 1e-6) if isinstance(wanted, float) else str(actual) == str(wanted)
            add(errors, ok, f"stage1.ifc:energy_property:{name}:{key}")
    add(errors, close(sum(areas), TOTAL_AREA), "stage1.ifc:area_total")
    walls = {str(x.GlobalId): x for x in stage1.by_type("IfcWall")}
    slabs = {str(x.GlobalId): x for x in stage1.by_type("IfcSlab")}
    add(errors, set(walls) == WALL_IDS, "stage1.ifc:wall_guid_set")
    add(errors, set(slabs) == SLAB_IDS, "stage1.ifc:slab_guid_set")
    try:
        import ifcopenshell.geom  # type: ignore
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)
        seed_products = {str(x.GlobalId): x for x in init.by_type("IfcProduct") if getattr(x, "GlobalId", None)}
        wall_specs = {row["global_id"]: row for row in spec.get("seed_preservation", {}).get("walls", [])}
        wall_openings: dict[str, list[Any]] = defaultdict(list)
        for relation in stage1.by_type("IfcRelVoidsElement"):
            wall_openings[str(relation.RelatingBuildingElement.GlobalId)].append(relation.RelatedOpeningElement)
        for guid in sorted(WALL_IDS | SLAB_IDS):
            delivered = walls.get(guid) or slabs.get(guid)
            add(errors, delivered is not None and bool(delivered.Representation), f"stage1.ifc:seed_geometry:{guid}")
            if delivered is not None and guid in seed_products:
                add(errors, bbox(seed_products[guid], settings) == bbox(delivered, settings), f"stage1.ifc:seed_bbox_changed:{guid}")
                if guid in SLAB_IDS:
                    slab_metrics = mesh_metrics(delivered, settings)
                    add(errors, mesh_equivalent(seed_products[guid], delivered, settings) and slab_metrics["closed"] and close(slab_metrics["volume"], 14.4, 0.01), f"stage1.ifc:seed_slab_topology_changed:{guid}")
                else:
                    add(errors, guid in wall_specs and wall_seed_shape_ok(delivered, seed_products[guid], wall_openings.get(guid, []), wall_specs[guid], settings), f"stage1.ifc:seed_wall_shape:{guid}")
        for name, space in spaces.items():
            check_space_geometry(space, name, settings, "stage1.ifc", errors)
        roofs = stage1.by_type("IfcRoof")
        if len(roofs) == 1:
            bounds = bbox(roofs[0], settings)
            roof_metrics = mesh_metrics(roofs[0], settings)
            add(errors, str(roofs[0].GlobalId) == ROOF_ID and bounds == (0.0, 8.0, -0.0, 6.0, 9.0, 10.74), "stage1.ifc:roof_bounds_or_guid")
            sloped = [face for face in roof_metrics["canonical_faces"] if close(abs(face[0][2]), 0.894427, 0.002)]
            slope_sides = {(round(abs(face[0][1]), 3), round(face[0][3], 3)) for face in sloped}
            add(errors, len(sloped) == 4 and len(slope_sides) == 4, "stage1.ifc:roof_mesh_not_pitched")
            add(errors, roof_metrics["closed"] and close(roof_metrics["volume"], 11.52, 0.01), "stage1.ifc:roof_topology")
    except Exception as exc:
        errors.append(f"stage1.ifc:geometry_check:{type(exc).__name__}")
    doors = {str(x.GlobalId): x for x in stage1.by_type("IfcDoor")}
    windows = {str(x.GlobalId): x for x in stage1.by_type("IfcWindow")}
    openings = {str(x.GlobalId): x for x in stage1.by_type("IfcOpeningElement")}
    for cls in ("IfcWall", "IfcSlab", "IfcRoof", "IfcDoor", "IfcWindow", "IfcOpeningElement"):
        for entity in stage1.by_type(cls):
            if cls != "IfcOpeningElement":
                add(errors, len(effective_storeys(entity)) == 1 and effective_storeys(entity).issubset(set(STOREY_IDS.values())), f"stage1.ifc:product_storey:{cls}:{entity.GlobalId}")
    add(errors, all(bool(x.Representation) for x in [*doors.values(), *windows.values(), *openings.values()]), "stage1.ifc:filling_geometry")
    try:
        import ifcopenshell.geom  # type: ignore
        settings = ifcopenshell.geom.settings(); settings.set(settings.USE_WORLD_COORDS, True)
        for cls, entities in (("door", doors.values()), ("window", windows.values()), ("opening", openings.values())):
            for entity in entities:
                metrics = mesh_metrics(entity, settings)
                bounds = bbox(entity, settings)
                spans = (bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4])
                add(errors, metrics["closed"] and metrics["volume"] > 0 and all(span > 0.02 for span in spans), f"stage1.ifc:{cls}_solid:{entity.GlobalId}")
    except Exception as exc:
        errors.append(f"stage1.ifc:filling_geometry_check:{type(exc).__name__}")
    voids = [(str(r.RelatingBuildingElement.GlobalId), str(r.RelatedOpeningElement.GlobalId)) for r in stage1.by_type("IfcRelVoidsElement")]
    fills = [(str(r.RelatingOpeningElement.GlobalId), str(r.RelatedBuildingElement.GlobalId)) for r in stage1.by_type("IfcRelFillsElement")]
    add(errors, len(set(voids)) == 6 and {x[1] for x in voids} == set(openings), "stage1.ifc:void_graph")
    add(errors, len(set(fills)) == 6 and {x[0] for x in fills} == set(openings) and {x[1] for x in fills} == set(doors) | set(windows), "stage1.ifc:fill_graph")
    add(errors, all(host in WALL_IDS for host, _ in voids), "stage1.ifc:opening_host_not_seed_wall")
    try:
        import ifcopenshell.geom  # type: ignore
        settings = ifcopenshell.geom.settings(); settings.set(settings.USE_WORLD_COORDS, True)
        void_by_opening = {opening: host for host, opening in voids}
        fill_by_opening = {opening: filling for opening, filling in fills}
        wall_order = [row["global_id"] for row in spec.get("seed_preservation", {}).get("walls", [])]
        unmatched = set(openings)
        for kind, cls, rows in (("door", "IfcDoor", spec.get("door_geometries", [])), ("window", "IfcWindow", spec.get("window_geometries", []))):
            for row in rows:
                geometry = row.get("geometry", {})
                expected_bounds = tuple(round(float(geometry[key]), 5) for key in ("x_m", "x_m", "y_m", "y_m", "z_m", "z_m"))
                expected_bounds = (
                    expected_bounds[0], round(expected_bounds[1] + float(geometry["width_m"]), 5),
                    expected_bounds[2], round(expected_bounds[3] + float(geometry["depth_m"]), 5),
                    round(expected_bounds[4] + {"Level 1": 0.0, "Level 2": 3.0, "Level 3": 6.0}[row["storey"]], 5),
                    round(expected_bounds[5] + float(geometry["height_m"]) + {"Level 1": 0.0, "Level 2": 3.0, "Level 3": 6.0}[row["storey"]], 5),
                )
                matches = [guid for guid in unmatched if all(close(a, b, 0.002) for a, b in zip(bbox(openings[guid], settings), expected_bounds))]
                add(errors, len(matches) == 1, f"stage1.ifc:{kind}_opening_geometry:{row.get('name')}")
                if len(matches) != 1:
                    continue
                opening_guid = matches[0]; unmatched.remove(opening_guid)
                filling_guid = fill_by_opening.get(opening_guid, "")
                filling = (doors if cls == "IfcDoor" else windows).get(filling_guid)
                host_index = int(row.get("host_wall_index", -1))
                host_guid = wall_order[host_index] if 0 <= host_index < len(wall_order) else ""
                add(errors, filling is not None and void_by_opening.get(opening_guid) == host_guid, f"stage1.ifc:{kind}_host_or_fill:{row.get('name')}")
                if filling is not None:
                    unit_scale = 0.001 if float(filling.OverallWidth or 0) > 100 else 1.0
                    add(errors, close(float(filling.OverallWidth or 0) * unit_scale, row.get("overall_width_m"), 0.002) and close(float(filling.OverallHeight or 0) * unit_scale, geometry.get("height_m"), 0.002), f"stage1.ifc:{kind}_dimensions:{row.get('name')}")
        add(errors, not unmatched, "stage1.ifc:unmatched_opening_geometry")
    except Exception as exc:
        errors.append(f"stage1.ifc:filling_contract:{type(exc).__name__}")
    add(errors, len(stage1.by_type("IfcRelSpaceBoundary")) == 0 and len(stage1.by_type("IfcRelSpaceBoundary2ndLevel")) == 0, "stage1.ifc:fabricated_boundaries")
    exchange = spec.get("ifc_exchange", {})
    add(errors, exchange.get("space_boundary_policy") == "observe_validate_and_preserve_native_export_state" and "space_boundary_level" not in exchange, "workflow_spec.json:boundary_contract")
    roof_spec = spec.get("roof_geometry", {})
    add(errors, close(roof_spec.get("ridge_rise_m"), 1.5) and close(roof_spec.get("width_m"), 8.0) and close(roof_spec.get("depth_m"), 6.0) and close(roof_spec.get("thickness_m"), 0.24), "workflow_spec.json:roof_contract")


def graph(model: Any) -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    return (
        {(str(r.RelatingBuildingElement.GlobalId), str(r.RelatedOpeningElement.GlobalId)) for r in model.by_type("IfcRelVoidsElement")},
        {(str(r.RelatingOpeningElement.GlobalId), str(r.RelatedBuildingElement.GlobalId)) for r in model.by_type("IfcRelFillsElement")},
    )


def check_stage2(stage1: Any, stage2: Any, roots1: dict[str, str], roots2: dict[str, str], errors: list[str]) -> None:
    if stage1 is None or stage2 is None:
        return
    add(errors, roots1 == roots2, "stage2.ifc:root_set_or_class_changed")
    add(errors, graph(stage1) == graph(stage2), "stage2.ifc:filling_graph_rewired")
    for cls in ("IfcSpace", "IfcWall", "IfcSlab", "IfcRoof", "IfcDoor", "IfcWindow", "IfcOpeningElement", "IfcRelVoidsElement", "IfcRelFillsElement"):
        add(errors, len(stage1.by_type(cls)) == len(stage2.by_type(cls)), f"stage2.ifc:count_changed:{cls}")
    add(errors, len(stage2.by_type("IfcRelSpaceBoundary")) == 0 and len(stage2.by_type("IfcRelSpaceBoundary2ndLevel")) == 0, "stage2.ifc:boundary_state_changed")
    for cls in GEOMETRIC_CLASSES:
        for entity in stage2.by_type(cls):
            if cls != "IfcOpeningElement":
                add(errors, len(effective_storeys(entity)) == 1 and effective_storeys(entity).issubset(set(STOREY_IDS.values())), f"stage2.ifc:product_storey:{cls}:{entity.GlobalId}")
    spaces1, spaces2 = named_spaces(stage1), named_spaces(stage2)
    for name in SPACES:
        if name not in spaces1 or name not in spaces2:
            continue
        add(errors, str(spaces1[name].GlobalId) == str(spaces2[name].GlobalId), f"stage2.ifc:space_guid:{name}")
        add(errors, containing_storeys(spaces2[name]) == {STOREY_IDS[SPACES[name][7]]}, f"stage2.ifc:space_storey:{name}")
        ps1, qt1 = psets(spaces1[name]); ps2, qt2 = psets(spaces2[name])
        energy_keys = ("ThermalZone", "ScheduleCategory", "PeoplePerM2", "LightingPowerDensityWPerM2", "EquipmentPowerDensityWPerM2", "OutdoorAirLPerSPerson")
        quantity_keys = ("GrossFloorArea", "NetFloorArea")
        semantic_equal = all(str(ps1.get("EngiWorld_EnergyHandoff", {}).get(k)) == str(ps2.get("EngiWorld_EnergyHandoff", {}).get(k)) for k in energy_keys)
        semantic_equal = semantic_equal and all(close(qt1.get("Qto_SpaceBaseQuantities", {}).get(k), qt2.get("Qto_SpaceBaseQuantities", {}).get(k), 1e-6) for k in quantity_keys)
        add(errors, semantic_equal, f"stage2.ifc:space_semantics:{name}")
    try:
        import ifcopenshell.geom  # type: ignore
        settings = ifcopenshell.geom.settings(); settings.set(settings.USE_WORLD_COORDS, True)
        required1 = {str(x.GlobalId): x for cls in GEOMETRIC_CLASSES for x in stage1.by_type(cls)}
        required2 = {str(x.GlobalId): x for cls in GEOMETRIC_CLASSES for x in stage2.by_type(cls)}
        add(errors, set(required1) == set(required2), "stage2.ifc:required_product_set_changed")
        add(errors, all(bool(x.Representation) for x in required1.values()), "stage1.ifc:required_representation_missing")
        add(errors, all(bool(x.Representation) for x in required2.values()), "stage2.ifc:required_representation_missing")
        for name, space in spaces2.items():
            check_space_geometry(space, name, settings, "stage2.ifc", errors)
        for guid in set(required1) & set(required2):
            add(errors, mesh_equivalent(required1[guid], required2[guid], settings), f"stage2.ifc:product_mesh:{guid}")
    except Exception as exc:
        errors.append(f"stage2.ifc:geometry_check:{type(exc).__name__}")


def check_handoffs(paths: dict[str, Path], stage1: Any, stage2: Any, errors: list[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    revit, arch = load_json(paths["revit_handoff.json"]), load_json(paths["archicad_handoff.json"])
    for data, label, source, expected_stage in ((revit, "revit_handoff.json", paths["stage1.ifc"], "revit"), (arch, "archicad_handoff.json", paths["stage2.ifc"], "archicad")):
        add(errors, data.get("case_id") == CASE_ID and data.get("software_stage") == expected_stage, f"{label}:identity")
        add(errors, str(data.get("source_sha256", "")).lower() == sha(source), f"{label}:source_hash")
        rows = data.get("spaces", [])
        add(errors, isinstance(rows, list) and len(rows) == 3, f"{label}:space_rows")
        by_name = {row.get("name"): row for row in rows if isinstance(row, dict)}
        add(errors, set(by_name) == set(SPACES), f"{label}:space_names")
        model_spaces = named_spaces(stage1 if expected_stage == "revit" else stage2)
        for name, expected in SPACES.items():
            row = by_name.get(name, {})
            checks = [
                str(row.get("ifc_guid")) == str(getattr(model_spaces.get(name), "GlobalId", "")),
                row.get("thermal_zone") == expected[0], close(row.get("area_m2"), expected[1]),
                row.get("schedule_category") == expected[2], close(row.get("people_per_m2"), expected[3], 1e-6),
                close(row.get("lighting_w_per_m2"), expected[4], 1e-6), close(row.get("equipment_w_per_m2"), expected[5], 1e-6),
                close(row.get("outdoor_air_l_per_s_person"), expected[6], 1e-6),
                row.get("storey") == expected[7],
            ]
            add(errors, all(checks), f"{label}:space_semantics:{name}")
    add(errors, str(revit.get("input_seed_sha256", "")).lower() == sha(paths["init.ifc"]), "revit_handoff.json:seed_hash")
    add(errors, str(arch.get("stage1_sha256", "")).lower() == sha(paths["stage1.ifc"]), "archicad_handoff.json:stage1_hash")
    add(errors, str(arch.get("revit_handoff_sha256", "")).lower() == sha(paths["revit_handoff.json"]), "archicad_handoff.json:revit_handoff_hash")
    add(errors, close(arch.get("building_area_m2"), TOTAL_AREA), "archicad_handoff.json:building_area")
    return revit, arch


def check_archicad_report(path: Path, stage1: Any, stage2: Any, paths: dict[str, Path], errors: list[str]) -> None:
    report = load_json(path)
    add(errors, report.get("case_id") == CASE_ID and report.get("software_stage") == "archicad", "archicad_report:identity")
    add(errors, report.get("source_file") == "stage1.ifc" and report.get("source_sha256") == sha(paths["stage1.ifc"]), "archicad_report:source")
    add(errors, report.get("output_file") == "stage2.ifc" and report.get("output_sha256") == sha(paths["stage2.ifc"]), "archicad_report:output")
    add(errors, sha(paths["stage1.ifc"]) != sha(paths["stage2.ifc"]), "archicad_report:no_native_reserialization")
    stage2_header = paths["stage2.ifc"].read_text(encoding="utf-8", errors="ignore")[:1000]
    add(errors, "The EXPRESS Data Manager Version" in stage2_header and "Autodesk Revit 25." in stage2_header, "stage2.ifc:not_compatible_archicad_edm_save")
    add(errors, report.get("validation_result") is None and report.get("blocking_errors") == [], "archicad_report:validation")
    counts = report.get("entity_counts", {}); live = report.get("live_entity_counts", {})
    for cls in ("IfcSpace", "IfcWall", "IfcSlab", "IfcRoof", "IfcDoor", "IfcWindow", "IfcOpeningElement", "IfcRelVoidsElement", "IfcRelFillsElement"):
        actual = len(stage2.by_type(cls)) if stage2 else -1
        add(errors, counts.get(cls) == actual and live.get(cls) == actual, f"archicad_report:count:{cls}")
    audit = report.get("global_id_audit", {})
    add(errors, audit.get("missing_ids") == [] and audit.get("duplicate_ids") == [] and audit.get("preserved_count") == len(stage1.by_type("IfcRoot")), "archicad_report:guid_audit")
    boundaries = report.get("space_boundaries", {})
    add(errors, all(boundaries.get(k) == 0 for k in ("stage1_relationship_count", "stage2_relationship_count", "stage1_second_level_count", "stage2_second_level_count")), "archicad_report:boundaries")
    provenance = report.get("native_provenance", {})
    transcript = provenance.get("rpc_transcript", [])
    methods = [row.get("request", {}).get("method") for row in transcript if isinstance(row, dict)]
    build = archicad_build(provenance.get("product_version"))
    add(errors, build is not None and build >= 6000, "archicad_report:version")
    expected_get_classes = ["IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace", "IfcWall", "IfcSlab", "IfcRoof", "IfcDoor", "IfcWindow", "IfcOpeningElement", "IfcRelVoidsElement", "IfcRelFillsElement", "IfcRelSpaceBoundary", "IfcRelSpaceBoundary2ndLevel"]
    expected_methods = ["Model.LoadFile", "Macro.ValidateIfcModel"] + ["Entity.Get"] * 15 + ["Entity.GetAttribute"] * 9 + ["Model.SaveFile"]
    add(errors, methods == expected_methods and len(transcript) == 27, "archicad_report:rpc_sequence")
    add(errors, "IFCCommandServerApp.exe" in str(provenance.get("exe")) and "--m EW3B10-RUN" in str(provenance.get("command_line")) and provenance.get("model_name") == "EW3B10-RUN", "archicad_report:provenance")
    if len(transcript) == 27:
        load, validate, save = transcript[0], transcript[1], transcript[-1]
        add(errors, str(load.get("request", {}).get("params", {}).get("Location", "")).lower().endswith(r"engiworld-task-10-work\stage1.ifc") and load.get("response", {}).get("result") == "stage1.ifc", "archicad_report:load_rpc")
        add(errors, validate.get("request", {}).get("params") == {} and validate.get("response", {}).get("result") is None, "archicad_report:validate_rpc")
        add(errors, str(save.get("request", {}).get("params", {}).get("Location", "")).lower().endswith(r"engiworld-task-10-work\stage2.ifc") and save.get("response", {}).get("result") is None, "archicad_report:save_rpc")
        get_rows = transcript[2:17]
        classes = [next(iter(row.get("request", {}).get("params", {}).get("Select", {})), "") for row in get_rows]
        add(errors, classes == expected_get_classes, "archicad_report:get_class_sequence")
        actual_counts = {cls: len(stage2.by_type(cls)) for cls in expected_get_classes}
        live_refs: dict[str, list[str]] = {}
        for cls, row in zip(classes, get_rows):
            value = row.get("response", {}).get("result")
            refs = [] if value is None else ([str(x) for x in value] if isinstance(value, list) else [str(value)])
            live_refs[cls] = refs
            add(errors, len(refs) == actual_counts[cls] and len(refs) == len(set(refs)), f"archicad_report:live_refs:{cls}")
        attr_rows = transcript[17:26]
        expected_attrs = [(str(row.get("ref_id")), attr) for row in report.get("live_spaces", []) for attr in ("GlobalId", "Name", "LongName")]
        actual_attrs = [(str(row.get("request", {}).get("params", {}).get("Select")), row.get("request", {}).get("params", {}).get("Attribute")) for row in attr_rows]
        add(errors, actual_attrs == expected_attrs and set(live_refs.get("IfcSpace", [])) == {x[0] for x in expected_attrs}, "archicad_report:space_attribute_queries")
        stage2_spaces = {str(x.GlobalId): x for x in stage2.by_type("IfcSpace")}
        for live in report.get("live_spaces", []):
            entity = stage2_spaces.get(str(live.get("ifc_guid")))
            add(errors, entity is not None and str(entity.Name) == str(live.get("name")) and str(entity.LongName) == str(live.get("long_name")), f"archicad_report:live_space:{live.get('long_name')}")
        for row in attr_rows:
            params, response = row.get("request", {}).get("params", {}), row.get("response", {}).get("result", {})
            attr = params.get("Attribute")
            matching = next((x for x in report.get("live_spaces", []) if str(x.get("ref_id")) == str(params.get("Select"))), {})
            expected_value = matching.get({"GlobalId": "ifc_guid", "Name": "name", "LongName": "long_name"}.get(attr, ""))
            add(errors, isinstance(response, dict) and response.get(attr) == expected_value, f"archicad_report:attribute_response:{params.get('Select')}:{attr}")


def osm_objects(text: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for match in re.finditer(r"(?ms)^\s*(OS:[A-Z0-9:]+)\s*,(.*?;\s*!-[^\r\n]*)", text, re.I):
        fields: dict[str, Any] = {}
        for raw in match.group(2).splitlines():
            data, _, comment = raw.partition("!-")
            label = re.sub(r"\s+\{[^}]+\}$", "", comment.strip())
            value = data.strip().rstrip(",;").strip()
            if not label:
                continue
            if label.startswith("X,Y,Z Vertex "):
                fields.setdefault("Vertices", []).append(tuple(float(x.strip()) for x in value.split(",")))
            else:
                fields[label] = value
        result.append({"type": match.group(1).upper(), "fields": fields, "body": match.group(2)})
    return result


def handle_value(value: Any) -> str:
    match = re.fullmatch(r"\{([^{}]+)\}", str(value).strip())
    return match.group(1).lower() if match else ""


def osm_index(objects: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    handles: dict[str, dict[str, Any]] = {}
    by_type: dict[str, list[dict[str, Any]]] = {}
    for obj in objects:
        by_type.setdefault(obj["type"], []).append(obj)
        handle = handle_value(obj["fields"].get("Handle"))
        if handle:
            handles[handle] = obj
    return handles, by_type


def named_osm(by_type: dict[str, list[dict[str, Any]]], cls: str) -> dict[str, dict[str, Any]]:
    return {str(obj["fields"].get("Name")): obj for obj in by_type.get(cls, [])}


def resolved(handles: dict[str, dict[str, Any]], obj: dict[str, Any], field: str, cls: str) -> dict[str, Any] | None:
    target = handles.get(handle_value(obj["fields"].get(field)))
    return target if target and target["type"] == cls else None


def check_osm(text: str, spec: dict[str, Any], paths: dict[str, Path], errors: list[str]) -> None:
    objects = osm_objects(text)
    handles, by_type = osm_index(objects)
    all_handles = [handle_value(x["fields"].get("Handle")) for x in objects]
    add(errors, len(objects) >= 100 and len(handles) == len(objects) and len(all_handles) == len(set(all_handles)), "result.osm:handle_uniqueness")
    for obj in objects:
        for label, value in obj["fields"].items():
            if label == "Handle" or label == "Vertices":
                continue
            handle = handle_value(value)
            if handle:
                add(errors, handle in handles, f"result.osm:dangling_handle:{obj['type']}:{label}")
    exact_counts = {
        "OS:BUILDINGSTORY": 3, "OS:SPACE": 3, "OS:SURFACE": 18, "OS:THERMALZONE": 3,
        "OS:THERMOSTATSETPOINT:DUALSETPOINT": 3, "OS:PEOPLE": 3,
        "OS:PEOPLE:DEFINITION": 3, "OS:LIGHTS": 3, "OS:LIGHTS:DEFINITION": 3,
        "OS:ELECTRICEQUIPMENT": 3, "OS:ELECTRICEQUIPMENT:DEFINITION": 3,
        "OS:DESIGNSPECIFICATION:OUTDOORAIR": 3,
    }
    for cls, count in exact_counts.items():
        add(errors, len(by_type.get(cls, [])) == count, f"result.osm:object_count:{cls}")
    spaces = named_osm(by_type, "OS:SPACE")
    zones = named_osm(by_type, "OS:THERMALZONE")
    schedules = named_osm(by_type, "OS:SCHEDULE:RULESET")
    add(errors, set(spaces) == set(SPACES), "result.osm:space_names")
    add(errors, set(SPACES[name][0] for name in SPACES) == set(zones), "result.osm:zone_names")
    used: dict[str, set[str]] = {k: set() for k in ("zones", "oa", "thermostats", "people", "lights", "equipment", "people_defs", "light_defs", "equipment_defs")}
    geometry_specs = {row["name"]: row["energy_geometry"] for row in spec.get("spaces", [])}
    surfaces = by_type.get("OS:SURFACE", [])
    for name, expected in SPACES.items():
        space = spaces.get(name)
        if not space:
            continue
        space_handle = handle_value(space["fields"].get("Handle"))
        story = resolved(handles, space, "Building Story Name", "OS:BUILDINGSTORY")
        zone = resolved(handles, space, "Thermal Zone Name", "OS:THERMALZONE")
        oa = resolved(handles, space, "Design Specification Outdoor Air Object Name", "OS:DESIGNSPECIFICATION:OUTDOORAIR")
        add(errors, zone is not None and zone["fields"].get("Name") == expected[0], f"result.osm:space_zone:{name}")
        add(errors, story is not None and story["fields"].get("Name") == expected[7], f"result.osm:space_story:{name}")
        add(errors, oa is not None and oa["fields"].get("Name") == f"{name} Outdoor Air" and oa["fields"].get("Outdoor Air Method") == "Sum" and close(oa["fields"].get("Outdoor Air Flow per Person"), expected[6] / 1000.0, 1e-7), f"result.osm:space_oa:{name}")
        if zone:
            used["zones"].add(handle_value(zone["fields"].get("Handle")))
            thermostat = resolved(handles, zone, "Thermostat Name", "OS:THERMOSTATSETPOINT:DUALSETPOINT")
            add(errors, zone["fields"].get("Use Ideal Air Loads") == "Yes" and thermostat is not None and thermostat["fields"].get("Name") == f"{name} Thermostat", f"result.osm:zone_thermostat:{name}")
            if thermostat:
                used["thermostats"].add(handle_value(thermostat["fields"].get("Handle")))
                heat = resolved(handles, thermostat, "Heating Setpoint Temperature Schedule Name", "OS:SCHEDULE:RULESET")
                cool = resolved(handles, thermostat, "Cooling Setpoint Temperature Schedule Name", "OS:SCHEDULE:RULESET")
                add(errors, bool(heat and heat["fields"].get("Name") == "Heating Setpoint 20.0C" and cool and cool["fields"].get("Name") == "Cooling Setpoint 26.0C"), f"result.osm:setpoint_schedules:{name}")
        if oa:
            used["oa"].add(handle_value(oa["fields"].get("Handle")))
        load_schedule = schedules.get(OSM_SCHEDULES[name])
        add(errors, load_schedule is not None, f"result.osm:load_schedule:{name}")
        if load_schedule:
            day = resolved(handles, load_schedule, "Default Day Schedule Name", "OS:SCHEDULE:DAY")
            pairs = []
            if day:
                f = day["fields"]
                index = 1
                while f.get(f"Hour {index}"):
                    pairs.append((int(float(f[f"Hour {index}"])), float(f[f"Value Until Time {index}"])))
                    index += 1
            expected_pairs = OSM_SCHEDULE_VALUES[name]
            add(errors, len(pairs) == len(expected_pairs) and all(a[0] == b[0] and close(a[1], b[1], 1e-8) for a, b in zip(pairs, expected_pairs)), f"result.osm:schedule_profile:{name}")
        load_specs = (
            ("OS:PEOPLE", "People Definition Name", "OS:PEOPLE:DEFINITION", "People per Space Floor Area", expected[3], "people", "people_defs", "Number of People Schedule Name"),
            ("OS:LIGHTS", "Lights Definition Name", "OS:LIGHTS:DEFINITION", "Watts per Space Floor Area", expected[4], "lights", "light_defs", "Schedule Name"),
            ("OS:ELECTRICEQUIPMENT", "Electric Equipment Definition Name", "OS:ELECTRICEQUIPMENT:DEFINITION", "Watts per Space Floor Area", expected[5], "equipment", "equipment_defs", "Schedule Name"),
        )
        for cls, def_field, def_cls, value_field, wanted, used_key, def_key, schedule_field in load_specs:
            candidates = [x for x in by_type.get(cls, []) if handle_value(x["fields"].get("Space or SpaceType Name")) == space_handle]
            add(errors, len(candidates) == 1, f"result.osm:{used_key}_space_link:{name}")
            if len(candidates) != 1:
                continue
            load = candidates[0]
            definition = resolved(handles, load, def_field, def_cls)
            schedule = resolved(handles, load, schedule_field, "OS:SCHEDULE:RULESET")
            add(errors, definition is not None and close(definition["fields"].get(value_field), wanted, 1e-7), f"result.osm:{def_key}_value:{name}")
            add(errors, schedule is load_schedule, f"result.osm:{used_key}_schedule:{name}")
            used[used_key].add(handle_value(load["fields"].get("Handle")))
            if definition:
                used[def_key].add(handle_value(definition["fields"].get("Handle")))
            if cls == "OS:PEOPLE":
                activity = resolved(handles, load, "Activity Level Schedule Name", "OS:SCHEDULE:RULESET")
                add(errors, activity is not None and activity["fields"].get("Name") == "Occupant Activity 120W", f"result.osm:activity_schedule:{name}")
        owned = [x for x in surfaces if handle_value(x["fields"].get("Space Name")) == space_handle]
        counts = Counter(x["fields"].get("Surface Type") for x in owned)
        add(errors, len(owned) == 6 and counts == Counter({"Wall": 4, "Floor": 1, "RoofCeiling": 1}), f"result.osm:surface_set:{name}")
        geom = geometry_specs.get(name, {})
        x, y, z = (float(geom.get(k, -999)) for k in ("x_m", "y_m", "z_m"))
        width, depth, height = (float(geom.get(k, -999)) for k in ("width_m", "depth_m", "height_m"))
        expected_corners = {(round(px, 4), round(py, 4), round(pz, 4)) for px in (x, x + width) for py in (y, y + depth) for pz in (z, z + height)}
        actual_vertices = {tuple(round(float(v), 4) for v in p) for surface in owned for p in surface["fields"].get("Vertices", [])}
        add(errors, all(len(surface["fields"].get("Vertices", [])) == 4 for surface in owned) and actual_vertices == expected_corners, f"result.osm:space_geometry:{name}")
    for key in ("zones", "oa", "thermostats", "people", "lights", "equipment", "people_defs", "light_defs", "equipment_defs"):
        add(errors, len(used[key]) == 3, f"result.osm:one_to_one:{key}")
    for token in (CASE_ID, sha(paths["stage2.ifc"]), sha(paths["archicad_handoff.json"]), "EW3B10-ConstructionSet"):
        add(errors, token in text, f"result.osm:metadata:{token[:18]}")


def sql_facts(path: Path, errors: list[str], label: str) -> dict[str, Any]:
    facts: dict[str, Any] = {}
    try:
        db = sqlite3.connect(str(path))
        integrity = db.execute("PRAGMA integrity_check").fetchone()
        add(errors, integrity == ("ok",) and db.execute("PRAGMA foreign_key_check").fetchall() == [], f"{label}:integrity")
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
        required = {"Simulations", "Zones", "Errors", "Time", "ReportData", "ReportDataDictionary", "TabularDataWithStrings", "Surfaces", "NominalPeople", "NominalLighting", "NominalElectricEquipment", "NominalVentilation"}
        add(errors, required.issubset(tables), f"{label}:standard_tables")
        sim = db.execute("SELECT EnergyPlusVersion,NumTimestepsPerHour FROM Simulations ORDER BY SimulationIndex DESC LIMIT 1").fetchone()
        add(errors, sim is not None and "25.1.0-1c11a3d85f" in str(sim[0]) and sim[1] == 4, f"{label}:simulation_record")
        zones = {str(row[0]).upper(): float(row[1]) for row in db.execute("SELECT ZoneName,FloorArea FROM Zones WHERE IsPartOfTotalArea=1")}
        expected_zones = {value[0]: value[1] for value in SPACES.values()}
        add(errors, set(zones) == set(expected_zones) and all(close(zones[k], v, 1e-5) for k, v in expected_zones.items()), f"{label}:zones")
        error_rows = db.execute("SELECT ErrorType,Count,ErrorMessage FROM Errors").fetchall()
        add(errors, error_rows and not any(int(row[0]) > 0 or re.search(r"\b(severe|fatal)\b", str(row[2]), re.I) for row in error_rows), f"{label}:severe_errors")
        time_rows = db.execute("SELECT COUNT(*),COUNT(DISTINCT printf('%04d-%02d-%02d-%02d-%02d',Year,Month,Day,Hour,Minute)),SUM(CASE WHEN COALESCE(WarmupFlag,0)=0 THEN 1 ELSE 0 END) FROM Time").fetchone()
        add(errors, time_rows == (8760, 8760, 8760), f"{label}:annual_time_series")
        dictionary = db.execute("SELECT ReportDataDictionaryIndex,IsMeter,Type,IndexGroup,KeyValue,Name,ReportingFrequency,Units FROM ReportDataDictionary").fetchall()
        add(errors, len(dictionary) == 1 and tuple(dictionary[0][1:]) in ((1, "Sum", "Facility:Electricity", "", "Electricity:Facility", "Hourly", "J"), (1, "Sum", "Facility:Electricity", None, "Electricity:Facility", "Hourly", "J")), f"{label}:meter_dictionary")
        if dictionary:
            meter = db.execute("SELECT COUNT(*),MIN(Value),MAX(Value),SUM(Value),MIN(TimeIndex),MAX(TimeIndex) FROM ReportData WHERE ReportDataDictionaryIndex=?", (dictionary[0][0],)).fetchone()
            add(errors, meter is not None and meter[0] == 8760 and meter[1] > 0 and meter[4:] == (1, 8760), f"{label}:meter_series")
            facts["meter"] = tuple(float(x) if isinstance(x, float) else x for x in meter)
        row = db.execute("""SELECT CAST(Value AS REAL) FROM TabularDataWithStrings WHERE ReportName='AnnualBuildingUtilityPerformanceSummary' AND TableName='Site and Source Energy' AND RowName='Total Site Energy' AND ColumnName='Total Energy' AND Units='GJ' LIMIT 1""").fetchone()
        site_kwh = float(row[0]) * 277.7777777778 if row and row[0] is not None else 0.0
        add(errors, site_kwh > 0, f"{label}:no_energy")
        facts["site_kwh"] = site_kwh
        facts["zones"] = zones
        facts["errors"] = [(int(row[0]), int(row[1])) for row in error_rows]
        facts["surfaces"] = sorted((str(row[0]).upper(), str(row[1]), round(float(row[2]), 6)) for row in db.execute("SELECT z.ZoneName,s.ClassName,s.Area FROM Surfaces s JOIN Zones z USING(ZoneIndex)"))
        facts["nominal"] = {}
        for table, value_column in (("NominalPeople", "NumberOfPeople"), ("NominalLighting", "DesignLevel"), ("NominalElectricEquipment", "DesignLevel"), ("NominalVentilation", "DesignLevel")):
            rows = sorted((str(row[0]).upper(), str(row[1]).upper(), round(float(row[2]), 8)) for row in db.execute(f"SELECT z.ZoneName,n.ObjectName,n.{value_column} FROM {table} n JOIN Zones z USING(ZoneIndex)"))
            add(errors, len(rows) == 3, f"{label}:{table}")
            facts["nominal"][table] = rows
        db.close()
    except Exception as exc:
        errors.append(f"{label}:parse:{type(exc).__name__}")
    return facts


def check_energy(paths: dict[str, Path], arch: dict[str, Any], spec: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    osm = paths["result.osm"].read_text(encoding="utf-8", errors="ignore")
    idf = paths["in.idf"].read_text(encoding="utf-8", errors="ignore")
    check_osm(osm, spec, paths, errors)
    for name, expected in SPACES.items():
        add(errors, name.upper() in idf.upper() and expected[0].upper() in idf.upper(), f"in.idf:space_or_zone:{name}")
    add(errors, "HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM" in idf.upper(), "in.idf:no_ideal_loads")
    add(errors, idf.upper().count("ZONE,") >= 3, "in.idf:zone_count")
    err = paths["run/eplusout.err"].read_text(encoding="utf-8", errors="ignore")
    add(errors, "EnergyPlus Completed Successfully" in err and "0 Severe Errors" in err and not re.search(r"\*\*\s+(Severe|Fatal)\s+\*\*", err, re.I), "eplusout.err:not_successful")
    metrics = sql_facts(paths["run/eplusout.sql"], errors, "eplusout.sql")
    with paths["energy_report.csv"].open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    add(errors, len(rows) == 1, "energy_report.csv:row_count")
    if rows:
        row = rows[0]
        add(errors, row.get("case_id") == CASE_ID and close(row.get("building_area_m2"), TOTAL_AREA) and row.get("space_count") == "3" and row.get("thermal_zone_count") == "3", "energy_report.csv:identity")
        add(errors, str(row.get("source_stage2_sha256", "")).lower() == sha(paths["stage2.ifc"]) and str(row.get("source_handoff_sha256", "")).lower() == sha(paths["archicad_handoff.json"]), "energy_report.csv:hashes")
        reported = float(row.get("total_site_energy_kwh", 0) or 0)
        add(errors, reported > 0 and close(reported, metrics.get("site_kwh"), 1.0), "energy_report.csv:energy")
        add(errors, close(row.get("eui_kwh_m2"), reported / TOTAL_AREA, 0.01), "energy_report.csv:eui")
        metrics["reported_site_kwh"] = reported
    with paths["model_summary.csv"].open(newline="", encoding="utf-8-sig") as stream:
        summary = list(csv.DictReader(stream))
    add(errors, len(summary) == 3 and {r.get("space_name") for r in summary} == set(SPACES), "model_summary.csv:space_rows")
    for row in summary:
        name = row.get("space_name")
        if name in SPACES:
            add(errors, row.get("thermal_zone") == SPACES[name][0] and close(row.get("area_m2"), SPACES[name][1]) and row.get("source_stage2_sha256") == sha(paths["stage2.ifc"]), f"model_summary.csv:{name}")
    return metrics


def check_reports(paths: dict[str, Path], metrics: dict[str, Any], errors: list[str]) -> None:
    flow, osw, log = load_json(paths["flow_report.json"]), load_json(paths["workflow.osw"]), load_json(paths["native_stage_log.json"])
    add(errors, flow.get("case_id") == CASE_ID and flow.get("software_chain") == ["revit", "archicad", "openstudio", "energyplus"], "flow_report.json:identity")
    add(errors, str(flow.get("openstudio_version", "")).startswith("3.10.0") and "25.1.0-1c11a3d85f" in str(flow.get("energyplus_version")), "flow_report.json:versions")
    add(errors, flow.get("forward_translator_errors") == [] and flow.get("stage2_sha256") == sha(paths["stage2.ifc"]), "flow_report.json:translation_or_hash")
    add(errors, flow.get("osm_sha256") == sha(paths["result.osm"]) and flow.get("idf_sha256") == sha(paths["in.idf"]) and flow.get("eplusout_sql_sha256") == sha(paths["run/eplusout.sql"]), "flow_report.json:artifact_hashes")
    add(errors, flow.get("simulation", {}).get("status") == "EnergyPlus Completed Successfully" and close(flow.get("simulation", {}).get("total_site_energy_kwh"), metrics.get("reported_site_kwh"), 0.01), "flow_report.json:simulation")
    add(errors, osw.get("name") == CASE_ID and osw.get("osw_version") == "3.10" and osw.get("seed_file") == "result.osm" and osw.get("weather_file") == "weather.epw", "workflow.osw:identity")
    add(errors, osw.get("source_stage2_sha256") == sha(paths["stage2.ifc"]) and osw.get("source_handoff_sha256") == sha(paths["archicad_handoff.json"]), "workflow.osw:hashes")
    stages = log.get("stages", [])
    add(errors, [s.get("stage") for s in stages] == ["revit", "archicad", "openstudio"], "native_stage_log.json:order")
    if len(stages) == 3:
        add(errors, str(stages[0].get("product_version", "")).startswith("25.1") and stages[0].get("output_sha256") == sha(paths["stage1.ifc"]), "native_stage_log.json:revit")
        build = archicad_build(stages[1].get("product_version"))
        add(errors, build is not None and build >= 6000 and stages[1].get("output_sha256") == sha(paths["stage2.ifc"]), "native_stage_log.json:archicad")
        add(errors, str(stages[2].get("product_version", "")).startswith("3.10.0") and "25.1.0-1c11a3d85f" in str(stages[2].get("energyplus_version")) and stages[2].get("output_sha256") == sha(paths["result.osm"]), "native_stage_log.json:openstudio")
        add(errors, stages[0].get("input_sha256") == sha(paths["init.ifc"]) and stages[1].get("input_sha256") == sha(paths["stage1.ifc"]) and stages[1].get("input_handoff_sha256") == sha(paths["revit_handoff.json"]) and stages[2].get("input_sha256") == sha(paths["stage2.ifc"]) and stages[2].get("input_handoff_sha256") == sha(paths["archicad_handoff.json"]), "native_stage_log.json:input_chain")
        revit = stages[0]
        normalize_win = lambda value: re.sub(r"\\+", r"\\", str(value)).lower()
        add(errors, normalize_win(revit.get("executable")) == normalize_win(r"C:\Program Files\Autodesk\Revit 2025\Revit.exe") and revit.get("product_version") == "25.1.0.44" and revit.get("product_build") == "20240516_1515(x64)", "native_stage_log.json:revit_version_or_executable")
        add(errors, normalize_win(revit.get("automation_entry")) == normalize_win(r"C:\ProgramData\Autodesk\Revit\Addins\2025\EngiWorld.BimBridge.addin") and str(revit.get("command", "")).startswith("Revit.exe /language ENU /nosplash (ENGIWORLD_BIM_STAGE=revit)"), "native_stage_log.json:revit_automation")
        add(errors, revit.get("exit_code") == 0 and revit.get("input_file") == "init.ifc" and revit.get("output_file") == "stage1.ifc" and revit.get("handoff_file") == "revit_handoff.json", "native_stage_log.json:revit_completion")
        add(errors, revit.get("output_sha256") == sha(paths["stage1.ifc"]) and revit.get("handoff_sha256") == sha(paths["revit_handoff.json"]), "native_stage_log.json:revit_hashes")
        try:
            times = [(datetime.fromisoformat(s["started_utc"].replace("Z", "+00:00")), datetime.fromisoformat(s["finished_utc"].replace("Z", "+00:00"))) for s in stages]
            add(errors, all(a <= b for a, b in times) and times[0][1] <= times[1][0] <= times[1][1] <= times[2][0] <= times[2][1], "native_stage_log.json:timestamps")
            completed = datetime.fromisoformat(load_json(paths["revit_handoff.json"])["native_provenance"]["completed_utc"].replace("Z", "+00:00"))
            add(errors, times[0][0] <= completed and abs((completed - times[0][1]).total_seconds()) <= 1.0, "native_stage_log.json:revit_completion_time")
        except Exception:
            errors.append("native_stage_log.json:timestamps")


def canonical_idf(path: Path) -> list[tuple[str, tuple[str, ...]]]:
    text = re.sub(r"!.*", "", path.read_text(encoding="utf-8", errors="ignore"))
    objects = []
    for block in text.split(";"):
        fields = tuple(re.sub(r"\s+", " ", value.strip()).upper() for value in block.split(","))
        if fields and fields[0]:
            objects.append((fields[0], fields[1:]))
    return sorted(objects)


def forward_translate(paths: dict[str, Path], errors: list[str]) -> None:
    executable = Path(r"C:\openstudio-3.10.0\bin\openstudio.exe")
    if not executable.is_file():
        if os.name == "nt":
            errors.append("openstudio_forward_translate:executable_missing")
        return
    with tempfile.TemporaryDirectory(prefix="ew3b10-ft-") as temp:
        temp_path = Path(temp)
        script = temp_path / "translate.rb"
        regenerated = temp_path / "regenerated.idf"
        summary = temp_path / "summary.json"
        ruby = """require 'openstudio'\nrequire 'json'\nosm, idf, out = ARGV\nvt = OpenStudio::OSVersion::VersionTranslator.new\nloaded = vt.loadModel(OpenStudio::Path.new(osm))\nraise 'VersionTranslator could not load result.osm' if loaded.empty?\nft = OpenStudio::EnergyPlus::ForwardTranslator.new\nworkspace = ft.translateModel(loaded.get)\nraise 'ForwardTranslator could not save IDF' unless workspace.save(OpenStudio::Path.new(idf), true)\nFile.write(out, JSON.pretty_generate({'version'=>OpenStudio.openStudioVersion,'errors'=>ft.errors.map(&:logMessage),'warnings'=>ft.warnings.map(&:logMessage)}))\n"""
        script.write_text(ruby, encoding="utf-8")
        result = subprocess.run([str(executable), str(script), str(paths["result.osm"]), str(regenerated), str(summary)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120)
        add(errors, result.returncode == 0 and regenerated.is_file() and summary.is_file(), "openstudio_forward_translate:failed")
        if summary.is_file():
            data = load_json(summary)
            add(errors, str(data.get("version", "")).startswith("3.10.0") and data.get("errors") == [], "openstudio_forward_translate:errors_or_version")
        if regenerated.is_file():
            add(errors, canonical_idf(regenerated) == canonical_idf(paths["in.idf"]), "openstudio_forward_translate:idf_mismatch")


def rerun_energyplus(paths: dict[str, Path], submitted: dict[str, Any], errors: list[str]) -> None:
    candidates = [
        Path(r"C:\openstudio-3.10.0\EnergyPlus\energyplus.exe"),
        Path(r"C:\openstudio-3.10.0\energyplus.exe"),
    ]
    executable = next((p for p in candidates if p.is_file()), None)
    if executable is None:
        if os.name == "nt":
            errors.append("energyplus_rerun:executable_missing")
        return
    with tempfile.TemporaryDirectory(prefix="ew3b10-eplus-") as temp:
        temp_path = Path(temp)
        input_idf = temp_path / "submitted.idf"
        weather = temp_path / "weather.epw"
        shutil.copy2(paths["in.idf"], input_idf)
        shutil.copy2(paths["weather.epw"], weather)
        result = subprocess.run([str(executable), "-x", "-w", str(weather), "-d", str(temp_path), str(input_idf)], cwd=str(temp_path), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120)
        add(errors, result.returncode == 0, "energyplus_rerun:exit_code")
        err_path = Path(temp) / "eplusout.err"
        add(errors, err_path.is_file() and "EnergyPlus Completed Successfully" in err_path.read_text(errors="ignore"), "energyplus_rerun:not_successful")
        sql_path = Path(temp) / "eplusout.sql"
        if sql_path.is_file():
            rerun = sql_facts(sql_path, errors, "energyplus_rerun.sql")
            add(errors, close(rerun.get("site_kwh"), submitted.get("site_kwh"), 0.5), "energyplus_rerun:energy_mismatch")
            add(errors, rerun.get("zones") == submitted.get("zones"), "energyplus_rerun:zones_mismatch")
            add(errors, rerun.get("surfaces") == submitted.get("surfaces"), "energyplus_rerun:surfaces_mismatch")
            add(errors, rerun.get("nominal") == submitted.get("nominal"), "energyplus_rerun:nominal_mismatch")
            sm, rm = submitted.get("meter"), rerun.get("meter")
            add(errors, bool(sm and rm and sm[0] == rm[0] and close(sm[2], rm[2], 1.0) and close(sm[3], rm[3], 10.0)), "energyplus_rerun:meter_mismatch")


def evaluate(root: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    paths = {name: root / name for name in REQUIRED}
    for name, path in paths.items():
        add(errors, path.is_file() and path.stat().st_size > 0, f"missing_or_empty:{name}")
    if errors:
        return False, errors
    for name, expected in IMMUTABLE.items():
        add(errors, sha(paths[name]) == expected, f"immutable_hash:{name}")
    spec, translator = load_json(paths["workflow_spec.json"]), load_json(paths["archicad_ifc4_translator.json"])
    add(errors, spec.get("case_id") == CASE_ID and spec.get("revision") == "EW3B10", "workflow_spec.json:identity")
    add(errors, spec.get("fixed_software", {}).get("revit", {}).get("major_version") == 2025 and spec.get("fixed_software", {}).get("archicad", {}).get("major_version") == 27 and spec.get("fixed_software", {}).get("openstudio", {}).get("version") == "3.10.0", "workflow_spec.json:versions")
    add(errors, spec.get("fixed_software", {}).get("openstudio", {}).get("energyplus_version") == "25.1.0", "workflow_spec.json:energyplus_version")
    add(errors, {x.get("name") for x in spec.get("spaces", [])} == set(SPACES), "workflow_spec.json:space_set")
    add(errors, translator.get("archicad_major_version") == 27 and translator.get("minimum_build", 0) >= 6000 and translator.get("schema") == "IFC4", "archicad_ifc4_translator.json:contract")
    init, _ = check_ifc(paths["init.ifc"], "init.ifc", errors)
    stage1, info1 = check_ifc(paths["stage1.ifc"], "stage1.ifc", errors, require_revit=True)
    stage2, info2 = check_ifc(paths["stage2.ifc"], "stage2.ifc", errors)
    check_stage1(init, stage1, spec, errors)
    check_stage2(stage1, stage2, info1.get("roots", {}), info2.get("roots", {}), errors)
    _, arch = check_handoffs(paths, stage1, stage2, errors)
    check_archicad_report(paths["archicad_validation_report.json"], stage1, stage2, paths, errors)
    metrics = check_energy(paths, arch, spec, errors)
    check_reports(paths, metrics, errors)
    if not errors:
        forward_translate(paths, errors)
        rerun_energyplus(paths, metrics, errors)
    return not errors, errors


def main() -> None:
    root = root_dir()
    try:
        ok, errors = evaluate(root)
    except Exception as exc:
        ok, errors = False, [f"exception:{type(exc).__name__}:{exc}"]
    try:
        (root / "multi_metrics.json").write_text(json.dumps({"ok": ok, "case_id": CASE_ID, "policy": "instruction_rules_no_gt_hash_comparison", "errors": errors}, indent=2), encoding="utf-8")
    except Exception:
        pass
    print("True" if ok else "False")


if __name__ == "__main__":
    main()
