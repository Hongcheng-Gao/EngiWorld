#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
import statistics
from pathlib import Path

import ifcopenshell
import ifcopenshell.geom

CASE_SPEC = {'case_id': 'quant-gui-bonsai-task-05-ubuntu',
 'title': 'Learning room balanced window layout',
 'objective': 'Balance useful daylight between two learning rooms using several modest windows rather than one '
              'oversized opening.',
 'spaces': [{'name': 'CLASSROOM A',
             'storey': 'Level 1',
             'bbox': [0.2, 0.2, 0.2, 5.8, 5.8, 3.0],
             'weight': 0.48,
             'allowed_facades': ['north', 'south', 'west'],
             'ideal_wwr': 0.2,
             'max_wwr': 0.3,
             'max_windows': 5,
             'min_sill': 0.85,
             'max_head': 2.65},
            {'name': 'CLASSROOM B',
             'storey': 'Level 1',
             'bbox': [6.2, 0.2, 0.2, 11.8, 5.8, 3.0],
             'weight': 0.48,
             'allowed_facades': ['north', 'south', 'east'],
             'ideal_wwr': 0.2,
             'max_wwr': 0.3,
             'max_windows': 5,
             'min_sill': 0.85,
             'max_head': 2.65},
            {'name': 'STORAGE',
             'storey': 'Level 1',
             'bbox': [5.8, 0.2, 0.2, 6.2, 5.8, 3.0],
             'weight': 0.0,
             'allowed_facades': [],
             'ideal_wwr': 0.0,
             'max_wwr': 0.0,
             'max_windows': 0,
             'min_sill': 1.4,
             'max_head': 2.5}],
 'walls': [{'name': 'South Wall', 'facade': 'south', 'bbox': [0.0, 0.0, 0.0, 12.0, 0.2, 3.2], 'fixed': True},
           {'name': 'East Wall', 'facade': 'east', 'bbox': [11.8, 0.0, 0.0, 12.0, 6.0, 3.2], 'fixed': True},
           {'name': 'North Wall', 'facade': 'north', 'bbox': [0.0, 5.8, 0.0, 12.0, 6.0, 3.2], 'fixed': True},
           {'name': 'West Wall', 'facade': 'west', 'bbox': [0.0, 0.0, 0.0, 0.2, 6.0, 3.2], 'fixed': True},
           {'name': 'Learning Party Wall',
            'facade': 'internal',
            'bbox': [5.8, 0.2, 0.0, 6.2, 5.8, 3.2],
            'fixed': True}],
 'slabs': [{'name': 'Learning Ground Slab', 'bbox': [0.0, 0.0, 0.0, 12.0, 6.0, 0.18], 'fixed': True},
           {'name': 'Learning Roof Slab', 'bbox': [0.0, 0.0, 3.2, 12.0, 6.0, 3.38], 'fixed': True}],
 'doors': [{'name': 'CLASSROOM A DOOR', 'storey': 'Level 1', 'bbox': [1.9, 0.03, 0.0, 2.75, 0.17, 2.1]},
           {'name': 'CLASSROOM B DOOR', 'storey': 'Level 1', 'bbox': [9.25, 0.03, 0.0, 10.1, 0.17, 2.1]}],
 'obstructions': [{'name': 'SITE-OBSTRUCTION-SOUTH PLAYGROUND CANOPY', 'bbox': [6.0, -1.8, 0.0, 12.0, -1.55, 2.7]}],
 'site': {'case_id': 'quant-gui-bonsai-task-05-ubuntu',
          'orientation': 'Project north is +Y; south facade is -Y; east facade is +X.',
          'target_daylight_period': 'clear-sky working hours proxy, 09:00-15:00 local time',
          'orientation_weights': {'south': 0.88, 'east': 0.78, 'west': 0.7, 'north': 0.64, 'roof': 1.12},
          'external_obstructions': [{'name': 'SITE-OBSTRUCTION-SOUTH PLAYGROUND CANOPY',
                                     'bbox_m': [6.0, -1.8, 0.0, 12.0, -1.55, 2.7]}],
          'scoring_thresholds': {'daylight_threshold': 0.23,
                                 'useful_target': 0.52,
                                 'glare_threshold': 0.98,
                                 'minimum_effective_score': 0.35}},
 'scoring': {'daylight_threshold': 0.23,
             'useful_target': 0.52,
             'glare_threshold': 0.98,
             'minimum_effective_score': 0.35},
 'constraints': {'case_id': 'quant-gui-bonsai-task-05-ubuntu',
                 'title': 'Learning room balanced window layout',
                 'objective': 'Balance useful daylight between two learning rooms using several modest windows rather '
                              'than one oversized opening.',
                 'hard_constraints': ['Edit the model only through the Bonsai/Blender GUI.',
                                      'Preserve all IfcSpace, IfcWall, IfcSlab, and IfcDoor objects and their bounding '
                                      'boxes.',
                                      'Do not delete, move, or resize site obstruction walls whose names begin with '
                                      'SITE-OBSTRUCTION.',
                                      'Only IfcWindow and matching IfcOpeningElement geometry/relationships, plus '
                                      'optional IfcShadingDevice geometry, may be changed or added.',
                                      'Keep every window on an allowed facade for its room and within sill/head '
                                      'limits.',
                                      'Keep each room window-to-wall ratio at or below its max_wwr.',
                                      'Every IfcWindow and preserved IfcDoor must fill exactly one geometric '
                                      'IfcOpeningElement through IfcRelFillsElement, and each opening must void its '
                                      'actual host IfcWall through IfcRelVoidsElement.',
                                      'Do not use IfcBuildingElementProxy or visual-only mesh objects as replacements '
                                      'for BIM elements.'],
                 'invalid_conditions': ['Missing or unparsable optimized.ifc.',
                                        'Changed room count, room names, fixed wall/slab/door geometry, building '
                                        'envelope, or site obstruction geometry.',
                                        'Windows placed on forbidden/private facades or outside room boundaries.',
                                        'Over-limit room WWR, excessive window count, malformed windows, or oversized '
                                        'shading devices.',
                                        'Unhosted or floating windows/doors, missing opening geometry, or '
                                        'missing/incorrect fill and void relationships.',
                                        'A submission that only writes score/design_summary/preview files without a '
                                        'valid IFC.'],
                 'allowed_object_classes': ['IfcWindow', 'IfcShadingDevice', 'IfcOpeningElement'],
                 'required_output': '/home/user/Desktop/optimized.ifc',
                 'optional_outputs': ['/home/user/Desktop/design_summary.json', '/home/user/Desktop/preview.png'],
                 'geometry_tolerance_m': 0.45,
                 'fixed_bbox_tolerance_m': 0.08,
                 'max_total_windows': 10,
                 'max_shading_devices': 8,
                 'window_dimension_limits_m': {'min_width': 0.55,
                                               'max_width': 3.2,
                                               'min_height': 0.45,
                                               'max_height': 2.25,
                                               'max_thickness': 0.35},
                 'shading_dimension_limits_m': {'max_projection_or_length': 7.0, 'max_thickness': 0.35},
                 'rooms': [{'name': 'CLASSROOM A',
                            'allowed_facades': ['north', 'south', 'west'],
                            'ideal_wwr': 0.2,
                            'max_wwr': 0.3,
                            'max_windows': 5,
                            'min_sill_m': 0.85,
                            'max_head_m': 2.65,
                            'daylight_weight': 0.48},
                           {'name': 'CLASSROOM B',
                            'allowed_facades': ['north', 'south', 'east'],
                            'ideal_wwr': 0.2,
                            'max_wwr': 0.3,
                            'max_windows': 5,
                            'min_sill_m': 0.85,
                            'max_head_m': 2.65,
                            'daylight_weight': 0.48},
                           {'name': 'STORAGE',
                            'allowed_facades': [],
                            'ideal_wwr': 0.0,
                            'max_wwr': 0.0,
                            'max_windows': 0,
                            'min_sill_m': 1.4,
                            'max_head_m': 2.5,
                            'daylight_weight': 0.0}]}}
DESKTOP = Path(os.environ.get("ENGIWORLD_EVAL_DIR", "/home/user/Desktop"))
RESULT = DESKTOP / "optimized.ifc"
LEGACY_RESULT = DESKTOP / "result.ifc"
BASELINE = DESKTOP / "baseline.ifc"
LEGACY_INIT = DESKTOP / "init.ifc"


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, float(value)))


def norm(name):
    return " ".join(str(name or "").upper().replace("_", " ").split())


def spans(b):
    return (b[3] - b[0], b[4] - b[1], b[5] - b[2])


def center(b):
    return ((b[0] + b[3]) / 2.0, (b[1] + b[4]) / 2.0, (b[2] + b[5]) / 2.0)


def volume(b):
    dx, dy, dz = spans(b)
    return max(0.0, dx * dy * dz)


def bbox_close(a, b, tol):
    return all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))


SETTINGS = ifcopenshell.geom.settings()
try:
    SETTINGS.set(SETTINGS.USE_WORLD_COORDS, True)
except Exception:
    pass
FIXED_SETTINGS = ifcopenshell.geom.settings()
try:
    FIXED_SETTINGS.set(FIXED_SETTINGS.USE_WORLD_COORDS, True)
    FIXED_SETTINGS.set("disable-opening-subtractions", True)
except Exception:
    pass


def shape_bbox(entity):
    try:
        shape = ifcopenshell.geom.create_shape(SETTINGS, entity)
        if shape is None or getattr(shape, "geometry", None) is None:
            return None
    except Exception:
        return None
    verts = list(shape.geometry.verts)
    if not verts:
        return None
    xs, ys, zs = verts[0::3], verts[1::3], verts[2::3]
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def geometry_signature(entity):
    try:
        shape = ifcopenshell.geom.create_shape(FIXED_SETTINGS, entity)
        vertices = list(shape.geometry.verts)
        faces = list(shape.geometry.faces)
    except Exception:
        return None
    points = [tuple(round(float(vertices[index + axis]), 6) for axis in range(3)) for index in range(0, len(vertices), 3)]
    triangles = []
    for index in range(0, len(faces), 3):
        triangle = tuple(sorted((points[faces[index]], points[faces[index + 1]], points[faces[index + 2]])))
        triangles.append(triangle)
    return tuple(sorted(triangles))


def parent_signature(entity):
    parents = []
    for relation in getattr(entity, "ContainedInStructure", ()):
        parent = relation.RelatingStructure
        parents.append((parent.is_a(), getattr(parent, "GlobalId", ""), norm(getattr(parent, "Name", ""))))
    for relation in getattr(entity, "Decomposes", ()):
        parent = relation.RelatingObject
        parents.append((parent.is_a(), getattr(parent, "GlobalId", ""), norm(getattr(parent, "Name", ""))))
    return tuple(sorted(parents))


def fixed_records(model):
    records = {}
    for ifc_class in ("IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace", "IfcWall", "IfcSlab", "IfcDoor"):
        for entity in model.by_type(ifc_class):
            guid = getattr(entity, "GlobalId", "")
            records[guid] = (entity.is_a(), norm(getattr(entity, "Name", "")), parent_signature(entity), geometry_signature(entity))
    return records


def load_model(path):
    if not path.is_file() or path.stat().st_size < 1200:
        raise ValueError(f"{path.name} missing or too small")
    return ifcopenshell.open(str(path))


def result_path():
    return RESULT if RESULT.is_file() else LEGACY_RESULT


def baseline_path():
    return BASELINE if BASELINE.is_file() else LEGACY_INIT


def by_name(model, ifc_class):
    out = {}
    for entity in model.by_type(ifc_class):
        out[norm(getattr(entity, "Name", ""))] = entity
    return out


def boxes_by_name(model, classes):
    out = {}
    for ifc_class in classes:
        for entity in model.by_type(ifc_class):
            b = shape_bbox(entity)
            if b is not None:
                out[norm(getattr(entity, "Name", ""))] = b
    return out


def entity_counts(model):
    walls = model.by_type("IfcWall") + model.by_type("IfcWallStandardCase")
    return {
        "IfcProject": len(model.by_type("IfcProject")),
        "IfcSite": len(model.by_type("IfcSite")),
        "IfcBuilding": len(model.by_type("IfcBuilding")),
        "IfcBuildingStorey": len(model.by_type("IfcBuildingStorey")),
        "IfcSpace": len(model.by_type("IfcSpace")),
        "IfcWall": len(walls),
        "IfcSlab": len(model.by_type("IfcSlab")),
        "IfcDoor": len(model.by_type("IfcDoor")),
        "IfcWindow": len(model.by_type("IfcWindow")),
        "IfcOpeningElement": len(model.by_type("IfcOpeningElement")),
        "IfcRelFillsElement": len(model.by_type("IfcRelFillsElement")),
        "IfcRelVoidsElement": len(model.by_type("IfcRelVoidsElement")),
        "IfcShadingDevice": len(model.by_type("IfcShadingDevice")),
        "IfcBuildingElementProxy": len(model.by_type("IfcBuildingElementProxy")),
    }


def face_area_for_facade(b, facade):
    dx, dy, dz = spans(b)
    if facade in ("south", "north"):
        return max(0.0, dx * dz)
    if facade in ("east", "west"):
        return max(0.0, dy * dz)
    if facade == "roof":
        return max(0.0, dx * dy)
    dims = sorted([abs(dx), abs(dy), abs(dz)], reverse=True)
    return dims[0] * dims[1] if len(dims) >= 2 else 0.0


def window_area(b, facade):
    return face_area_for_facade(b, facade)


def infer_facade(room, window):
    rb = room["bbox"]
    wb = window
    cx, cy, _ = center(wb)
    tol = CASE_SPEC["constraints"]["geometry_tolerance_m"]
    candidates = []
    if abs(cy - rb[1]) <= tol and max(wb[0], rb[0]) < min(wb[3], rb[3]):
        candidates.append(("south", abs(cy - rb[1])))
    if abs(cy - rb[4]) <= tol and max(wb[0], rb[0]) < min(wb[3], rb[3]):
        candidates.append(("north", abs(cy - rb[4])))
    if abs(cx - rb[0]) <= tol and max(wb[1], rb[1]) < min(wb[4], rb[4]):
        candidates.append(("west", abs(cx - rb[0])))
    if abs(cx - rb[3]) <= tol and max(wb[1], rb[1]) < min(wb[4], rb[4]):
        candidates.append(("east", abs(cx - rb[3])))
    if abs(wb[2] - rb[5]) <= tol and max(wb[0], rb[0]) < min(wb[3], rb[3]) and max(wb[1], rb[1]) < min(wb[4], rb[4]):
        candidates.append(("roof", abs(wb[2] - rb[5])))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item[1])[0][0]


def match_window(wbox):
    matches = []
    wz0, wz1 = wbox[2], wbox[5]
    for room in CASE_SPEC["spaces"]:
        rb = room["bbox"]
        if wz1 <= rb[2] + 0.05 or wz0 >= rb[5] + 0.15:
            continue
        facade = infer_facade(room, wbox)
        if facade is None:
            continue
        matches.append((room["name"], facade))
    if not matches:
        return None
    return matches[0]


def obstruction_factor(facade, wbox):
    factor = 1.0
    for obstruction in CASE_SPEC.get("obstructions", []):
        ob = obstruction["bbox"]
        overlap = 0.0
        dist = 999.0
        if facade in ("south", "north"):
            width = max(0.001, wbox[3] - wbox[0])
            overlap = max(0.0, min(wbox[3], ob[3]) - max(wbox[0], ob[0])) / width
            if facade == "south" and ob[4] <= wbox[1]:
                dist = wbox[1] - ob[4]
            elif facade == "north" and ob[1] >= wbox[4]:
                dist = ob[1] - wbox[4]
            else:
                continue
        elif facade in ("east", "west"):
            width = max(0.001, wbox[4] - wbox[1])
            overlap = max(0.0, min(wbox[4], ob[4]) - max(wbox[1], ob[1])) / width
            if facade == "west" and ob[3] <= wbox[0]:
                dist = wbox[0] - ob[3]
            elif facade == "east" and ob[0] >= wbox[3]:
                dist = ob[0] - wbox[3]
            else:
                continue
        vertical = max(0.0, min(wbox[5], ob[5]) - max(wbox[2], ob[2])) / max(0.001, wbox[5] - wbox[2])
        blocking = clamp(overlap * vertical) * math.exp(-dist / 5.0)
        factor *= 1.0 - 0.50 * blocking
    return clamp(factor, 0.35, 1.0)


def shade_coverage_for_window(facade, wbox, shade_boxes):
    if not shade_boxes:
        return 0.0
    coverage = 0.0
    for sb in shade_boxes:
        if facade in ("south", "north"):
            horizontal_overlap = max(0.0, min(wbox[3], sb[3]) - max(wbox[0], sb[0])) / max(0.001, wbox[3] - wbox[0])
            near = (facade == "south" and sb[4] <= wbox[1] + 0.25) or (facade == "north" and sb[1] >= wbox[4] - 0.25)
        elif facade in ("east", "west"):
            horizontal_overlap = max(0.0, min(wbox[4], sb[4]) - max(wbox[1], sb[1])) / max(0.001, wbox[4] - wbox[1])
            near = (facade == "west" and sb[3] <= wbox[0] + 0.25) or (facade == "east" and sb[0] >= wbox[3] - 0.25)
        else:
            horizontal_overlap = 0.0
            near = False
        above = sb[2] >= wbox[5] - 0.15 and sb[2] <= wbox[5] + 0.55
        if near and above:
            coverage += horizontal_overlap
    return clamp(coverage)


def room_facade_area(room, facade):
    rb = room["bbox"]
    height = rb[5] - rb[2]
    if facade in ("south", "north"):
        return (rb[3] - rb[0]) * height
    if facade in ("east", "west"):
        return (rb[4] - rb[1]) * height
    if facade == "roof":
        return (rb[3] - rb[0]) * (rb[4] - rb[1])
    return 0.0


def sample_points(room):
    rb = room["bbox"]
    dx, dy, _ = spans(rb)
    nx = max(3, min(8, int(math.ceil(dx / 1.1))))
    ny = max(3, min(8, int(math.ceil(dy / 1.1))))
    points = []
    for ix in range(nx):
        x = rb[0] + (ix + 0.5) * dx / nx
        for iy in range(ny):
            y = rb[1] + (iy + 0.5) * dy / ny
            points.append((x, y, rb[2] + 0.8))
    return points


def daylight_from_window(room, facade, wbox, point, shade_boxes):
    rb = room["bbox"]
    wx, wy, wz = center(wbox)
    px, py, pz = point
    if facade == "south":
        depth = max(0.0, py - wy)
        lateral = abs(px - wx)
        room_depth = max(0.1, rb[4] - rb[1])
        width = max(0.1, wbox[3] - wbox[0])
    elif facade == "north":
        depth = max(0.0, wy - py)
        lateral = abs(px - wx)
        room_depth = max(0.1, rb[4] - rb[1])
        width = max(0.1, wbox[3] - wbox[0])
    elif facade == "west":
        depth = max(0.0, px - wx)
        lateral = abs(py - wy)
        room_depth = max(0.1, rb[3] - rb[0])
        width = max(0.1, wbox[4] - wbox[1])
    elif facade == "east":
        depth = max(0.0, wx - px)
        lateral = abs(py - wy)
        room_depth = max(0.1, rb[3] - rb[0])
        width = max(0.1, wbox[4] - wbox[1])
    else:
        depth = abs(pz - wz)
        lateral = math.hypot(px - wx, py - wy)
        room_depth = max(0.1, max(rb[3] - rb[0], rb[4] - rb[1]))
        width = math.sqrt(max(0.1, (wbox[3] - wbox[0]) * (wbox[4] - wbox[1])))
    area = window_area(wbox, facade)
    room_area = max(1.0, (rb[3] - rb[0]) * (rb[4] - rb[1]))
    orient = CASE_SPEC["site"]["orientation_weights"].get(facade, 0.65)
    shade_cov = shade_coverage_for_window(facade, wbox, shade_boxes)
    obstruction = obstruction_factor(facade, wbox)
    distance_factor = math.exp(-0.82 * depth / room_depth)
    spread_factor = math.exp(-0.20 * lateral / max(width, 0.25))
    vertical_factor = math.exp(-0.10 * abs(pz - wz))
    shade_transmission = 1.0 - 0.16 * shade_cov
    return orient * obstruction * shade_transmission * area / room_area * 10.0 * distance_factor * spread_factor * vertical_factor


def percentile(values, pct):
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * pct))))
    return ordered[idx]


def evaluate_daylight(window_records, shade_boxes):
    scoring = CASE_SPEC["scoring"]
    room_results = []
    room_scores = []
    total_weight = 0.0
    weighted = {"coverage": 0.0, "mean_daylight": 0.0, "uniformity": 0.0, "wwr_fit": 0.0, "glare": 0.0}
    for room in CASE_SPEC["spaces"]:
        if room.get("weight", 0.0) <= 0:
            continue
        points = sample_points(room)
        values = []
        room_windows = [w for w in window_records if w["room"] == room["name"]]
        for point in points:
            value = 0.015
            for win in room_windows:
                value += daylight_from_window(room, win["facade"], win["bbox"], point, shade_boxes)
            values.append(value)
        mean = statistics.fmean(values) if values else 0.0
        p20 = percentile(values, 0.20)
        coverage = sum(1 for value in values if value >= scoring["daylight_threshold"]) / max(1, len(values))
        mean_norm = clamp(mean / scoring["useful_target"])
        uniformity = clamp(p20 / mean) if mean > 0 else 0.0
        overlit = sum(1 for value in values if value > scoring["glare_threshold"]) / max(1, len(values))
        wwr = room_window_to_wall_ratio(room, room_windows)
        sigma = max(0.025, room["ideal_wwr"] * 0.32 + 0.02)
        wwr_fit = math.exp(-0.5 * ((wwr - room["ideal_wwr"]) / sigma) ** 2) if room["ideal_wwr"] > 0 else 1.0
        room_score = clamp(0.45 * coverage + 0.22 * mean_norm + 0.18 * uniformity + 0.15 * wwr_fit - 0.20 * overlit)
        weight = float(room["weight"])
        total_weight += weight
        weighted["coverage"] += coverage * weight
        weighted["mean_daylight"] += mean_norm * weight
        weighted["uniformity"] += uniformity * weight
        weighted["wwr_fit"] += wwr_fit * weight
        weighted["glare"] += overlit * weight
        room_scores.append(room_score)
        room_results.append(
            {
                "name": room["name"],
                "sample_count": len(values),
                "window_count": len(room_windows),
                "wwr": round(wwr, 6),
                "coverage_ratio": round(coverage, 6),
                "mean_daylight": round(mean, 6),
                "normalized_mean_daylight": round(mean_norm, 6),
                "uniformity": round(uniformity, 6),
                "overlit_ratio": round(overlit, 6),
                "wwr_fit": round(wwr_fit, 6),
                "room_score": round(room_score, 6),
            }
        )
    if total_weight <= 0:
        return {}, []
    for key in weighted:
        weighted[key] /= total_weight
    balance = min(room_scores) / max(room_scores) if room_scores and max(room_scores) > 0 else 0.0
    raw = (
        0.42 * weighted["coverage"]
        + 0.20 * weighted["mean_daylight"]
        + 0.16 * weighted["uniformity"]
        + 0.12 * weighted["wwr_fit"]
        + 0.10 * balance
    )
    glare_penalty = 0.18 * weighted["glare"]
    return (
        {
            "coverage_ratio": round(weighted["coverage"], 6),
            "normalized_mean_daylight": round(weighted["mean_daylight"], 6),
            "uniformity": round(weighted["uniformity"], 6),
            "wwr_fit": round(weighted["wwr_fit"], 6),
            "room_balance": round(balance, 6),
            "glare_penalty": round(glare_penalty, 6),
            "raw_score": round(raw, 6),
            "room_metrics": room_results,
        },
        [raw, glare_penalty],
    )


def room_window_to_wall_ratio(room, room_windows):
    allowed = room.get("allowed_facades", [])
    wall_area = sum(room_facade_area(room, facade) for facade in allowed)
    if wall_area <= 0:
        return 0.0
    area = sum(window_area(win["bbox"], win["facade"]) for win in room_windows)
    return area / wall_area


def validate_structure(model, baseline):
    failures = []
    counts = entity_counts(model)
    base_counts = entity_counts(baseline)
    if not str(getattr(model, "schema", "")).upper().startswith("IFC4"):
        failures.append("schema_not_ifc4")
    for cls in ("IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace", "IfcWall", "IfcSlab", "IfcDoor", "IfcWindow"):
        if counts.get(cls, 0) <= 0:
            failures.append(f"missing_required_class:{cls}")
    if counts["IfcBuildingElementProxy"] > 0:
        failures.append("contains_visual_or_proxy_bim_replacement")
    for cls in ("IfcSpace", "IfcWall", "IfcSlab", "IfcDoor"):
        if counts.get(cls, 0) != base_counts.get(cls, 0):
            failures.append(f"fixed_class_count_changed:{cls}")
    if counts["IfcWindow"] > CASE_SPEC["constraints"]["max_total_windows"]:
        failures.append("too_many_windows")
    if counts["IfcShadingDevice"] > CASE_SPEC["constraints"]["max_shading_devices"]:
        failures.append("too_many_shading_devices")
    return failures, counts, base_counts


def validate_fixed_bboxes(model):
    failures = []
    tol = CASE_SPEC["constraints"]["fixed_bbox_tolerance_m"]
    boxes = boxes_by_name(model, ("IfcSpace", "IfcWall", "IfcWallStandardCase", "IfcSlab", "IfcDoor"))
    for group in ("spaces", "walls", "slabs", "doors", "obstructions"):
        for item in CASE_SPEC.get(group, []):
            if group == "obstructions":
                expected_class = ("IfcWall", "IfcWallStandardCase")
            else:
                expected_class = None
            name = norm(item["name"])
            actual = boxes.get(name)
            if actual is None and expected_class is not None:
                actual = boxes_by_name(model, expected_class).get(name)
            if actual is None:
                failures.append(f"missing_fixed_object:{item['name']}")
                continue
            if not bbox_close(actual, item["bbox"], tol):
                failures.append(f"fixed_bbox_changed:{item['name']}")
    return failures


def validate_fixed_identity_and_geometry(model, baseline):
    failures = []
    actual = fixed_records(model)
    expected = fixed_records(baseline)
    if set(actual) != set(expected):
        failures.append("fixed_object_guid_set_changed")
    for guid in sorted(set(actual) & set(expected)):
        if actual[guid] != expected[guid]:
            failures.append(f"fixed_object_identity_container_or_geometry_changed:{guid}")
    return failures


def validate_feature_semantics(model):
    failures = []
    features = list(model.by_type("IfcWindow")) + list(model.by_type("IfcDoor"))
    openings = list(model.by_type("IfcOpeningElement"))
    if len(openings) != len(features):
        failures.append("opening_count_does_not_match_windows_and_doors")
    if len(model.by_type("IfcRelFillsElement")) != len(features):
        failures.append("fill_relation_count_does_not_match_windows_and_doors")
    if len(model.by_type("IfcRelVoidsElement")) != len(features):
        failures.append("void_relation_count_does_not_match_windows_and_doors")
    wall_facades = {norm(item["name"]): item.get("facade") for item in CASE_SPEC.get("walls", [])}
    for feature in features:
        label = getattr(feature, "GlobalId", "")
        fills = list(getattr(feature, "FillsVoids", ()))
        if len(fills) != 1:
            failures.append(f"feature_does_not_fill_exactly_one_opening:{label}")
            continue
        opening = fills[0].RelatingOpeningElement
        voids = list(getattr(opening, "VoidsElements", ()))
        if len(voids) != 1:
            failures.append(f"opening_does_not_void_exactly_one_host:{label}")
            continue
        host = voids[0].RelatingBuildingElement
        if not host.is_a("IfcWall"):
            failures.append(f"opening_host_is_not_wall:{label}")
            continue
        feature_box, opening_box, host_box = shape_bbox(feature), shape_bbox(opening), shape_bbox(host)
        if feature_box is None or opening_box is None or host_box is None:
            failures.append(f"feature_opening_or_host_missing_geometry:{label}")
            continue
        host_spans = spans(host_box)
        thin_axis = 0 if host_spans[0] <= host_spans[1] else 1
        long_axis = 1 - thin_axis
        if opening_box[thin_axis] > host_box[thin_axis] + 0.03 or opening_box[thin_axis + 3] < host_box[thin_axis + 3] - 0.03:
            failures.append(f"opening_does_not_cross_host_wall:{label}")
        for axis in (long_axis, 2):
            if opening_box[axis] > feature_box[axis] + 0.03 or opening_box[axis + 3] < feature_box[axis + 3] - 0.03:
                failures.append(f"opening_does_not_cover_filling:{label}")
                break
            if (opening_box[axis + 3] - opening_box[axis]) > (feature_box[axis + 3] - feature_box[axis]) + 0.25:
                failures.append(f"opening_is_oversized_for_filling:{label}")
                break
        if feature.is_a("IfcWindow"):
            match = match_window(feature_box)
            host_facade = wall_facades.get(norm(getattr(host, "Name", "")))
            if match is None or host_facade != match[1]:
                failures.append(f"window_host_wall_does_not_match_facade:{label}")
    return failures


def validate_windows_and_shades(model):
    failures = []
    windows = []
    room_counts = {room["name"]: 0 for room in CASE_SPEC["spaces"]}
    dims = CASE_SPEC["constraints"]["window_dimension_limits_m"]
    for window in model.by_type("IfcWindow"):
        b = shape_bbox(window)
        if b is None or volume(b) <= 0:
            failures.append(f"window_missing_geometry:{getattr(window, 'Name', '')}")
            continue
        match = match_window(b)
        if match is None:
            failures.append(f"window_not_on_allowed_room_boundary:{getattr(window, 'Name', '')}")
            continue
        room_name, facade = match
        room = next(room for room in CASE_SPEC["spaces"] if room["name"] == room_name)
        if facade not in room.get("allowed_facades", []):
            failures.append(f"window_on_forbidden_facade:{getattr(window, 'Name', '')}:{room_name}:{facade}")
            continue
        dx, dy, dz = spans(b)
        length = dx if facade in ("south", "north") else dy if facade in ("east", "west") else math.sqrt(dx * dy)
        thickness = dy if facade in ("south", "north") else dx if facade in ("east", "west") else dz
        finished_floor = room["bbox"][2] - 0.2
        sill = b[2] - finished_floor
        head = b[5] - finished_floor
        if length < dims["min_width"] or length > dims["max_width"]:
            failures.append(f"window_width_out_of_range:{getattr(window, 'Name', '')}")
        if dz < dims["min_height"] or dz > dims["max_height"]:
            failures.append(f"window_height_out_of_range:{getattr(window, 'Name', '')}")
        if thickness > dims["max_thickness"]:
            failures.append(f"window_too_thick:{getattr(window, 'Name', '')}")
        if sill + 1e-6 < room["min_sill"] or head - 1e-6 > room["max_head"]:
            failures.append(f"window_sill_or_head_out_of_range:{getattr(window, 'Name', '')}")
        room_counts[room_name] += 1
        windows.append({"name": getattr(window, "Name", ""), "bbox": b, "room": room_name, "facade": facade, "area": window_area(b, facade)})
    for room in CASE_SPEC["spaces"]:
        if room_counts[room["name"]] > room["max_windows"]:
            failures.append(f"too_many_windows_in_room:{room['name']}")
        room_windows = [w for w in windows if w["room"] == room["name"]]
        wwr = room_window_to_wall_ratio(room, room_windows)
        if wwr > room["max_wwr"] + 1e-6:
            failures.append(f"wwr_exceeds_hard_limit:{room['name']}")
        if not room.get("allowed_facades") and room_counts[room["name"]] > 0:
            failures.append(f"privacy_or_service_room_has_window:{room['name']}")
    shade_boxes = []
    shade_limits = CASE_SPEC["constraints"]["shading_dimension_limits_m"]
    for shade in model.by_type("IfcShadingDevice"):
        b = shape_bbox(shade)
        if b is None or volume(b) <= 0:
            failures.append(f"shade_missing_geometry:{getattr(shade, 'Name', '')}")
            continue
        dx, dy, dz = spans(b)
        if max(dx, dy) > shade_limits["max_projection_or_length"] or dz > shade_limits["max_thickness"]:
            failures.append(f"shade_geometry_out_of_range:{getattr(shade, 'Name', '')}")
        shade_boxes.append(b)
    return failures, windows, shade_boxes, room_counts


def evaluate():
    result = {
        "case_id": CASE_SPEC["case_id"],
        "valid": False,
        "score": 0.0,
        "threshold_pass": False,
        "hard_failures": [],
        "metrics": {},
    }
    try:
        model = load_model(result_path())
        baseline = load_model(baseline_path())
        failures, counts, base_counts = validate_structure(model, baseline)
        failures.extend(validate_fixed_identity_and_geometry(model, baseline))
        failures.extend(validate_fixed_bboxes(model))
        failures.extend(validate_feature_semantics(model))
        window_failures, windows, shade_boxes, room_counts = validate_windows_and_shades(model)
        failures.extend(window_failures)
        daylight_metrics, score_terms = evaluate_daylight(windows, shade_boxes)
        if score_terms:
            raw, glare_penalty = score_terms
            score = 0.0 if failures else clamp(raw - glare_penalty)
        else:
            score = 0.0
            failures.append("no_daylight_metrics")
        result.update(
            {
                "valid": not failures,
                "score": round(score, 6),
                "threshold_pass": bool((not failures) and score >= CASE_SPEC["scoring"]["minimum_effective_score"]),
                "hard_failures": failures,
                "metrics": {
                    "counts": counts,
                    "baseline_counts": base_counts,
                    "window_count_by_room": room_counts,
                    "window_records": [
                        {
                            "name": w["name"],
                            "room": w["room"],
                            "facade": w["facade"],
                            "area": round(w["area"], 6),
                            "bbox": [round(v, 6) for v in w["bbox"]],
                        }
                        for w in windows
                    ],
                    "shading_device_count": len(shade_boxes),
                    "daylight": daylight_metrics,
                    "failure_count": len(failures),
                },
            }
        )
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        if "optimized.ifc missing or too small" in str(exc) or "result.ifc missing or too small" in str(exc):
            result["hard_failures"] = ["missing_optimized_ifc"]
        elif "baseline.ifc missing or too small" in str(exc) or "init.ifc missing or too small" in str(exc):
            result["hard_failures"] = ["missing_baseline_ifc"]
        else:
            result["hard_failures"] = ["evaluation_exception"]
        result["error"] = message
    for name in ("score.json", "quant_metrics.json"):
        try:
            (DESKTOP / name).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        except Exception:
            pass
    print("True" if result.get("valid") else "False")


if __name__ == "__main__":
    evaluate()
