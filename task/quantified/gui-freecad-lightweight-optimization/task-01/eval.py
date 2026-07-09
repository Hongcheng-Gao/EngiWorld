#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import trimesh

CASE_SPEC = {'case_id': 'quant-gui-freecad-lightweight-task-01-ubuntu', 'token': 'EWQFCAD01', 'title': 'sensor mast cantilever bracket', 'objective': 'Maximize load-capacity proxy per volume for a sensor mast cantilever bracket.', 'metric_kind': 'cantilever_load_per_volume', 'metric_description': 'cantilever load proxy / volume; long-span bracket height, footprint span, and required support/load-zone material improve score', 'envelope_mm': [100.0, 42.0, 34.0], 'min_bbox_mm': [94.0, 36.0, 18.0], 'min_volume_mm3': 12000.0, 'max_volume_mm3': 62000.0, 'baseline_height_mm': 18.0, 'base_thickness_mm': 3.5, 'zone_height_mm': 12.0, 'load_pad_height_mm': 16.0, 'nominal_load_n': 420.0, 'min_zone_points': 8, 'required_zones': [{'name': 'SUPPORT_A', 'role': 'support', 'x_range_mm': [0.0, 18.0], 'y_range_mm': [5.0, 17.0]}, {'name': 'SUPPORT_B', 'role': 'support', 'x_range_mm': [0.0, 18.0], 'y_range_mm': [25.0, 37.0]}, {'name': 'LOAD_PAD', 'role': 'load', 'x_range_mm': [82.0, 100.0], 'y_range_mm': [14.0, 28.0]}], 'ribs': [{'size': [92.0, 4.0, 27.0], 'center': [50.0, 12.0, 15.5]}, {'size': [92.0, 4.0, 27.0], 'center': [50.0, 30.0, 15.5]}, {'size': [8.0, 34.0, 20.0], 'center': [52.0, 21.0, 13.5]}], 'hard_constraints': ['Produce the required open geometry output file rather than only reporting metrics.', 'Stay inside the stated bounding envelope and above the minimum useful spans.', 'Stay within the stated material-volume range.', 'Do not read ground_truth, edit eval.py, or fabricate score/metric files.'], 'invalid_conditions': ['Missing, unparsable, empty, or implausibly small STL geometry.', 'Bounding-box or volume hard-constraint violation.', 'Self-reported metrics without valid geometry.', 'Native project files used as the only deliverable.'], 'baseline_metrics': {'bbox_mm': [100.0, 42.0, 18.0], 'volume_mm3': 75600.0, 'surface_area_mm2': 13512.0, 'surface_per_volume': 0.17873016, 'metric_kind': 'cantilever_load_per_volume', 'metric_value': 0.0001944444, 'zone_point_counts': {'SUPPORT_A': 1, 'SUPPORT_B': 1, 'LOAD_PAD': 2}, 'zone_factor': 0.125, 'height_factor': 0.0, 'span_factor': 1.0, 'load_capacity_proxy_n': 14.7, 'load_capacity_per_volume': 0.0001944444}, 'reference_metrics': {'bbox_mm': [100.0, 42.0, 29.0], 'volume_mm3': 49228.0, 'surface_area_mm2': 27290.0, 'surface_per_volume': 0.55435931, 'metric_kind': 'cantilever_load_per_volume', 'metric_value': 0.0066120907, 'zone_point_counts': {'SUPPORT_A': 27, 'SUPPORT_B': 27, 'LOAD_PAD': 26}, 'zone_factor': 1.0, 'height_factor': 0.6875, 'span_factor': 1.0, 'load_capacity_proxy_n': 325.5, 'load_capacity_per_volume': 0.0066120907, 'score': 1.0}}
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
    mesh = as_mesh(trimesh.load_mesh(str(path), file_type="stl", process=False))
    if mesh.vertices is None or len(mesh.vertices) < 8 or len(mesh.faces) < 12:
        raise ValueError("optimized.stl has too little mesh geometry")
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


def zone_coverage(mesh, zone):
    points = [np.asarray(mesh.vertices, dtype=float)]
    try:
        points.append(np.asarray(mesh.triangles_center, dtype=float))
    except Exception:
        pass
    pts = np.vstack(points)
    x0, x1 = zone["x_range_mm"]
    y0, y1 = zone["y_range_mm"]
    mask = (
        (pts[:, 0] >= x0 - 0.75) & (pts[:, 0] <= x1 + 0.75) &
        (pts[:, 1] >= y0 - 0.75) & (pts[:, 1] <= y1 + 0.75) &
        (pts[:, 2] >= -0.5)
    )
    return int(mask.sum())


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
    zone_counts = {zone["name"]: zone_coverage(mesh, zone) for zone in CASE_SPEC["required_zones"]}
    zone_factor = min(1.0, min(zone_counts.values()) / max(CASE_SPEC["min_zone_points"], 1))
    load_capacity_proxy, height_factor, span_factor = proxy_load(dims, zone_factor)
    efficiency = load_capacity_proxy / max(vol, 1e-9)
    baseline = CASE_SPEC["baseline_metrics"]["load_capacity_per_volume"]
    reference = CASE_SPEC["reference_metrics"]["load_capacity_per_volume"]
    raw = (efficiency - baseline) / max(reference - baseline, 1e-12)
    return base | {
        "metric_kind": CASE_SPEC["metric_kind"],
        "metric_value": round(efficiency, 10),
        "zone_point_counts": zone_counts,
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
        got = m["zone_point_counts"].get(zone["name"], 0)
        if got < CASE_SPEC["min_zone_points"]:
            errors.append(f"zone:{zone['name']}:insufficient_material_points:{got}")
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
