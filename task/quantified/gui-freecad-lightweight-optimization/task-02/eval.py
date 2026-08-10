#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import trimesh

CASE_SPEC = {'case_id': 'quant-gui-freecad-lightweight-task-02-ubuntu', 'token': 'EWQFCAD02', 'title': 'DIN rail equipment shelf', 'objective': 'Maximize support proxy per volume for a DIN rail equipment shelf carrying an offset load.', 'metric_kind': 'shelf_offset_load_per_volume', 'metric_description': 'offset shelf support proxy / volume; x-span and vertical depth matter more than unused width', 'envelope_mm': [120.0, 50.0, 42.0], 'min_bbox_mm': [112.0, 44.0, 22.0], 'min_volume_mm3': 15000.0, 'max_volume_mm3': 90000.0, 'baseline_height_mm': 20.0, 'base_thickness_mm': 4.0, 'zone_height_mm': 14.0, 'load_pad_height_mm': 18.0, 'nominal_load_n': 560.0, 'min_zone_points': 8, 'required_zones': [{'name': 'RAIL_HOOK_TOP', 'role': 'support', 'x_range_mm': [0.0, 20.0], 'y_range_mm': [4.0, 18.0]}, {'name': 'RAIL_HOOK_BOTTOM', 'role': 'support', 'x_range_mm': [0.0, 20.0], 'y_range_mm': [32.0, 46.0]}, {'name': 'DEVICE_LOAD', 'role': 'load', 'x_range_mm': [95.0, 120.0], 'y_range_mm': [15.0, 35.0]}], 'ribs': [{'size': [112.0, 4.5, 34.0], 'center': [60.0, 12.0, 19.0]}, {'size': [112.0, 4.5, 34.0], 'center': [60.0, 38.0, 19.0]}, {'size': [10.0, 42.0, 22.0], 'center': [66.0, 25.0, 15.0]}], 'hard_constraints': ['Produce the required open geometry output file rather than only reporting metrics.', 'Stay inside the stated bounding envelope and above the minimum useful spans.', 'Stay within the stated material-volume range.', 'Do not read ground_truth, edit eval.py, or fabricate score/metric files.'], 'invalid_conditions': ['Missing, unparsable, empty, or implausibly small STL geometry.', 'Bounding-box or volume hard-constraint violation.', 'Self-reported metrics without valid geometry.', 'Native project files used as the only deliverable.'], 'baseline_metrics': {'bbox_mm': [120.0, 50.0, 20.0], 'volume_mm3': 120000.0, 'surface_area_mm2': 18800.0, 'surface_per_volume': 0.15666667, 'metric_kind': 'shelf_offset_load_per_volume', 'metric_value': 0.0001458333, 'zone_point_counts': {'RAIL_HOOK_TOP': 1, 'RAIL_HOOK_BOTTOM': 1, 'DEVICE_LOAD': 2}, 'zone_factor': 0.125, 'height_factor': 0.0, 'span_factor': 1.0, 'load_capacity_proxy_n': 17.5, 'load_capacity_per_volume': 0.0001458333}, 'reference_metrics': {'bbox_mm': [120.0, 50.0, 36.0], 'volume_mm3': 84352.0, 'surface_area_mm2': 39992.0, 'surface_per_volume': 0.4741085, 'metric_kind': 'shelf_offset_load_per_volume', 'metric_value': 0.0051451062, 'zone_point_counts': {'RAIL_HOOK_TOP': 27, 'RAIL_HOOK_BOTTOM': 27, 'DEVICE_LOAD': 26}, 'zone_factor': 1.0, 'height_factor': 0.7, 'span_factor': 1.0, 'load_capacity_proxy_n': 434.0, 'load_capacity_per_volume': 0.0051451062, 'score': 1.0}}
CASE_SPEC["reference_metrics"] = {'bbox_mm': [120.0, 50.0, 36.0], 'height_factor': 0.7, 'load_capacity_per_volume': 0.0058117735, 'load_capacity_proxy_n': 434.0, 'metric_kind': 'shelf_offset_load_per_volume', 'metric_value': 0.0058117735, 'score': 1.0, 'span_factor': 1.0, 'surface_area_mm2': 31084.0, 'surface_per_volume': 0.41625154, 'volume_mm3': 74676.0, 'zone_factor': 1.0, 'zone_point_counts': {'DEVICE_LOAD': 64, 'RAIL_HOOK_BOTTOM': 64, 'RAIL_HOOK_TOP': 64}, 'zone_volume_coverage': {'DEVICE_LOAD': 1.0, 'RAIL_HOOK_BOTTOM': 1.0, 'RAIL_HOOK_TOP': 1.0}}
CASE_SPEC["hard_constraints"] = ["Produce the required open geometry output file rather than only reporting metrics.", "Stay inside the stated bounding envelope and above the minimum useful spans.", "Stay within the stated material-volume range.", "Export one connected, watertight, consistently oriented solid.", "Keep at least 95% sampled material coverage in each required support/load prism.", "Do not read ground_truth, edit eval.py, or fabricate score/metric files."]
CASE_SPEC["invalid_conditions"] = ["Missing, unparsable, empty, or implausibly small STL geometry.", "Bounding-box or volume hard-constraint violation.", "Disconnected, non-watertight, inconsistently oriented, or overlapping-shell geometry.", "Required-zone three-dimensional material coverage below 95%.", "Self-reported metrics without valid geometry.", "Native project files used as the only deliverable."]
DESKTOP = Path(os.environ.get("ENGIWORLD_EVAL_DIR") or os.environ.get("OUTPUT_ROOT") or "/home/user/Desktop")


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, float(value)))


def as_mesh(obj):
    if isinstance(obj, trimesh.Scene):
        meshes = [g for g in obj.geometry.values() if isinstance(g, trimesh.Trimesh)]
        if not meshes:
            raise ValueError("scene has no mesh geometry")
        return trimesh.util.concatenate(meshes)
    return obj


def load_stl(path: Path):
    if not path.is_file() or path.stat().st_size < 500:
        raise ValueError("optimized.stl missing or too small")
    mesh = as_mesh(trimesh.load_mesh(str(path), file_type="stl", process=True))
    if mesh.vertices is None or len(mesh.vertices) < 8 or len(mesh.faces) < 12:
        raise ValueError("optimized.stl has too little mesh geometry")
    if not np.isfinite(np.asarray(mesh.vertices, dtype=float)).all():
        raise ValueError("optimized.stl contains NaN or infinite coordinates")
    if not mesh.is_watertight or not mesh.is_winding_consistent:
        raise ValueError("optimized.stl must be a watertight consistently oriented solid")
    if len(mesh.split(only_watertight=False)) != 1:
        raise ValueError("optimized.stl must contain one connected solid")
    return mesh


def mesh_metrics(mesh):
    bounds = np.asarray(mesh.bounds, dtype=float)
    dims = (bounds[1] - bounds[0]).tolist()
    volume = abs(float(mesh.volume))
    area = float(mesh.area)
    return {
        "bbox_mm": [round(float(x), 4) for x in dims],
        "volume_mm3": round(volume, 4),
        "surface_area_mm2": round(area, 4),
        "surface_per_volume": round(area / max(volume, 1e-9), 8),
    }


def points_inside(mesh, points):
    triangles = np.asarray(mesh.triangles, dtype=float)
    edge_a = triangles[:, 1] - triangles[:, 0]
    edge_b = triangles[:, 2] - triangles[:, 0]
    votes = np.zeros(len(points), dtype=np.int8)
    directions = np.asarray(((1.0, 0.3713907, 0.129837), (0.173205, 1.0, 0.417), (0.241, 0.137, 1.0)))
    for direction in directions:
        direction = direction / np.linalg.norm(direction)
        h = np.cross(np.broadcast_to(direction, edge_b.shape), edge_b)
        determinant = np.einsum("ij,ij->i", edge_a, h)
        usable = np.abs(determinant) > 1e-10
        inverse = np.zeros(len(triangles), dtype=float)
        inverse[usable] = 1.0 / determinant[usable]
        for point_index, point in enumerate(points):
            offset = point - triangles[:, 0]
            u = inverse * np.einsum("ij,ij->i", offset, h)
            q = np.cross(offset, edge_a)
            v = inverse * np.einsum("ij,j->i", q, direction)
            distance = inverse * np.einsum("ij,ij->i", edge_b, q)
            hits = usable & (u > 1e-9) & (v > 1e-9) & (u + v < 1.0 - 1e-9) & (distance > 1e-9)
            votes[point_index] += int(int(hits.sum()) % 2 == 1)
    return votes >= 2


def zone_coverage(mesh, zone):
    x0, x1 = zone["x_range_mm"]
    y0, y1 = zone["y_range_mm"]
    height = CASE_SPEC["zone_height_mm"] if zone["role"] == "support" else CASE_SPEC["load_pad_height_mm"]
    grid = 4
    xs = x0 + (np.arange(grid) + 0.5) * (x1 - x0) / grid
    ys = y0 + (np.arange(grid) + 0.5) * (y1 - y0) / grid
    zs = (np.arange(grid) + 0.5) * height / grid
    points = np.asarray([(x, y, z) for x in xs for y in ys for z in zs], dtype=float)
    inside = points_inside(mesh, points)
    return {"inside": int(inside.sum()), "samples": len(points), "coverage": float(inside.mean())}


def proxy_load(dims, zone_factor):
    height_factor = clamp((dims[2] - CASE_SPEC["min_bbox_mm"][2]) / max(CASE_SPEC["envelope_mm"][2] - CASE_SPEC["min_bbox_mm"][2], 1e-9))
    span_x = clamp(dims[0] / CASE_SPEC["envelope_mm"][0], 0.0, 1.0)
    span_y = clamp(dims[1] / CASE_SPEC["envelope_mm"][1], 0.0, 1.0)
    span_factor = (span_x + span_y) / 2.0
    kind = CASE_SPEC["metric_kind"]
    if kind == "cantilever_load_per_volume":
        proxy = CASE_SPEC["nominal_load_n"] * (0.28 + 0.72 * height_factor) * (0.35 + 0.65 * span_factor) * zone_factor
    elif kind == "shelf_offset_load_per_volume":
        proxy = CASE_SPEC["nominal_load_n"] * (0.45 + 0.55 * span_x) * (0.25 + 0.75 * height_factor) * zone_factor
    elif kind == "tall_gusset_load_per_volume":
        proxy = CASE_SPEC["nominal_load_n"] * (0.12 + 0.88 * height_factor) * (0.45 + 0.55 * span_x) * zone_factor
    elif kind == "clamp_bridge_load_per_volume":
        proxy = CASE_SPEC["nominal_load_n"] * (0.30 + 0.70 * span_y) * (0.35 + 0.65 * height_factor) * zone_factor
    elif kind == "hinge_strip_load_per_volume":
        proxy = CASE_SPEC["nominal_load_n"] * (0.58 + 0.42 * span_x) * (0.50 + 0.50 * zone_factor) * (0.62 + 0.38 * height_factor)
    else:
        raise ValueError("unknown metric_kind: " + str(kind))
    return proxy, height_factor, span_factor


def metrics(mesh):
    base = mesh_metrics(mesh)
    dims = base["bbox_mm"]
    vol = base["volume_mm3"]
    zone_results = {zone["name"]: zone_coverage(mesh, zone) for zone in CASE_SPEC["required_zones"]}
    zone_counts = {name: result["inside"] for name, result in zone_results.items()}
    zone_coverages = {name: result["coverage"] for name, result in zone_results.items()}
    zone_factor = min(zone_coverages.values())
    load_capacity_proxy, height_factor, span_factor = proxy_load(dims, zone_factor)
    efficiency = load_capacity_proxy / max(vol, 1e-9)
    baseline = CASE_SPEC["baseline_metrics"]["load_capacity_per_volume"]
    reference = CASE_SPEC["reference_metrics"]["load_capacity_per_volume"]
    raw = (efficiency - baseline) / max(reference - baseline, 1e-12)
    return base | {
        "metric_kind": CASE_SPEC["metric_kind"],
        "metric_value": round(efficiency, 10),
        "zone_point_counts": zone_counts,
        "zone_volume_coverage": {name: round(value, 6) for name, value in zone_coverages.items()},
        "zone_factor": round(zone_factor, 6),
        "height_factor": round(height_factor, 6),
        "span_factor": round(span_factor, 6),
        "load_capacity_proxy_n": round(load_capacity_proxy, 6),
        "load_capacity_per_volume": round(efficiency, 10),
        "score": round(clamp(raw), 6),
    }


def hard_errors(m):
    errors = []
    dims = m["bbox_mm"]
    for i, (got, max_allowed) in enumerate(zip(dims, CASE_SPEC["envelope_mm"])):
        if got > max_allowed + 1.0:
            errors.append(f"bbox_axis_{i}:too_large:{got}>{max_allowed}")
    for i, (got, min_allowed) in enumerate(zip(dims, CASE_SPEC["min_bbox_mm"])):
        if got < min_allowed - 1.0:
            errors.append(f"bbox_axis_{i}:too_small:{got}<{min_allowed}")
    if not (CASE_SPEC["min_volume_mm3"] <= m["volume_mm3"] <= CASE_SPEC["max_volume_mm3"]):
        errors.append(f"volume:outside_range:{m['volume_mm3']}")
    for zone in CASE_SPEC["required_zones"]:
        got = m["zone_volume_coverage"].get(zone["name"], 0.0)
        if got < 0.95:
            errors.append(f"zone:{zone['name']}:material_coverage_below_0.95:{got}")
    return errors


def write_result(result):
    for name in ("score.json", "quant_metrics.json"):
        try:
            (DESKTOP / name).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        except Exception:
            pass
    print("True" if result.get("valid") else "False")


def main():
    try:
        m = metrics(load_stl(DESKTOP / "optimized.stl"))
        errors = hard_errors(m)
        score = 0.0 if errors else m["score"]
        result = {
            "case_id": CASE_SPEC["case_id"],
            "valid": not errors,
            "score": round(score, 6),
            "errors": errors,
            "metrics": m,
            "baseline_metrics": CASE_SPEC["baseline_metrics"],
            "reference_metrics": CASE_SPEC["reference_metrics"],
        }
    except Exception as exc:
        result = {"case_id": CASE_SPEC["case_id"], "valid": False, "score": 0.0, "errors": [str(exc)], "metrics": {}}
    write_result(result)


if __name__ == "__main__":
    main()
