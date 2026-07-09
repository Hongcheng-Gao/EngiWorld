#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import trimesh

CASE_SPEC = {'case_id': 'quant-cli-openscad-parametric-task-01-ubuntu', 'token': 'EWQSCAD01', 'title': 'compact controller heat sink with dense straight fins', 'objective': 'Maximize exposed cooling surface per material volume for a compact controller heat sink.', 'metric_kind': 'surface_per_volume', 'metric_description': 'surface_area_mm2 / volume_mm3; higher exposed cooling area per material volume receives a higher score', 'reference_design': 'dense straight-fin heat sink with a thin base plate', 'envelope_mm': [80.0, 50.0, 28.0], 'min_bbox_mm': [76.0, 46.0, 24.0], 'min_volume_mm3': 14500.0, 'max_volume_mm3': 54000.0, 'base_thickness_mm': 4.0, 'starter_block_size': [73.6, 41.0, 10.64], 'starter_block_center': [40.0, 25.0, 9.32], 'optimized_boxes': [{'name': 'fin_1', 'size': [1.7, 46.0, 24.0], 'center': [5.85, 25.0, 16.0]}, {'name': 'fin_2', 'size': [1.7, 46.0, 24.0], 'center': [12.68, 25.0, 16.0]}, {'name': 'fin_3', 'size': [1.7, 46.0, 24.0], 'center': [19.51, 25.0, 16.0]}, {'name': 'fin_4', 'size': [1.7, 46.0, 24.0], 'center': [26.340000000000003, 25.0, 16.0]}, {'name': 'fin_5', 'size': [1.7, 46.0, 24.0], 'center': [33.17, 25.0, 16.0]}, {'name': 'fin_6', 'size': [1.7, 46.0, 24.0], 'center': [40.00000000000001, 25.0, 16.0]}, {'name': 'fin_7', 'size': [1.7, 46.0, 24.0], 'center': [46.830000000000005, 25.0, 16.0]}, {'name': 'fin_8', 'size': [1.7, 46.0, 24.0], 'center': [53.66000000000001, 25.0, 16.0]}, {'name': 'fin_9', 'size': [1.7, 46.0, 24.0], 'center': [60.49000000000001, 25.0, 16.0]}, {'name': 'fin_10', 'size': [1.7, 46.0, 24.0], 'center': [67.32000000000001, 25.0, 16.0]}, {'name': 'fin_11', 'size': [1.7, 46.0, 24.0], 'center': [74.15, 25.0, 16.0]}], 'hard_constraints': ['Produce the required open geometry output file rather than only reporting metrics.', 'Stay inside the stated bounding envelope and above the minimum useful spans.', 'Stay within the stated material-volume range.', 'Do not read ground_truth, edit eval.py, or fabricate score/metric files.'], 'invalid_conditions': ['Missing, unparsable, empty, or implausibly small STL geometry.', 'Bounding-box or volume hard-constraint violation.', 'Self-reported metrics without valid geometry.', 'Native project files used as the only deliverable.'], 'baseline_metrics': {'bbox_mm': [80.0, 50.0, 14.64], 'volume_mm3': 48107.264, 'surface_area_mm2': 17513.888, 'surface_per_volume': 0.36405912}, 'reference_metrics': {'bbox_mm': [80.0, 50.0, 28.0], 'volume_mm3': 36644.8, 'surface_area_mm2': 34225.6, 'surface_per_volume': 0.93398245}, 'reference_score': {'metric_kind': 'surface_per_volume', 'metric_value': 0.93398245, 'surface_per_volume': 0.93398245, 'raw_efficiency_score': 1.0, 'volume_factor': 1.0, 'height_factor': 1.0, 'score': 1.0}}
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


def metrics(mesh):
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


def metric_value(m):
    dims = m["bbox_mm"]
    vol = max(m["volume_mm3"], 1e-9)
    surface = m["surface_area_mm2"]
    kind = CASE_SPEC["metric_kind"]
    if kind == "surface_per_volume":
        return surface / vol
    if kind == "footprint_per_volume":
        return (dims[0] * dims[1]) / vol
    if kind == "span_height_per_volume":
        return (dims[0] * dims[2]) / vol
    if kind == "clearance_surface_mix":
        return 0.72 * (surface / vol) + 0.28 * ((dims[1] * dims[2]) / vol)
    if kind == "low_profile_surface_density":
        return (surface / vol) * clamp(1.0 - 0.35 * max(0.0, dims[2] - CASE_SPEC["target_height_mm"]) / max(CASE_SPEC["envelope_mm"][2] - CASE_SPEC["target_height_mm"], 1.0), 0.65, 1.05)
    raise ValueError("unknown metric_kind: " + str(kind))


def design_summary_errors():
    path = DESKTOP / "design_summary.json"
    if not path.is_file():
        return ["design_summary:missing"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"design_summary:unreadable:{exc}"]
    errors = []
    if data.get("case_id") != CASE_SPEC["case_id"]:
        errors.append("design_summary:case_id_mismatch")
    if data.get("token") != CASE_SPEC["token"]:
        errors.append("design_summary:token_mismatch")
    if not isinstance(data.get("design"), str) or not data["design"].strip():
        errors.append("design_summary:missing_design_text")
    return errors


def score_from_metrics(m):
    eff = metric_value(m)
    baseline = metric_value(CASE_SPEC["baseline_metrics"])
    reference = metric_value(CASE_SPEC["reference_metrics"])
    raw = (eff - baseline) / max(reference - baseline, 1e-9)
    vol = m["volume_mm3"]
    volume_factor = clamp((CASE_SPEC["max_volume_mm3"] - vol) / max(CASE_SPEC["max_volume_mm3"] - CASE_SPEC["reference_metrics"]["volume_mm3"], 1.0), 0.0, 1.10)
    height_factor = clamp(m["bbox_mm"][2] / max(CASE_SPEC["envelope_mm"][2], 1e-9), 0.75, 1.0)
    score = clamp(0.88 * raw + 0.08 * volume_factor + 0.04 * height_factor)
    return {
        "metric_kind": CASE_SPEC["metric_kind"],
        "metric_value": round(eff, 8),
        "surface_per_volume": round(m["surface_area_mm2"] / max(m["volume_mm3"], 1e-9), 8),
        "raw_efficiency_score": round(clamp(raw), 6),
        "volume_factor": round(volume_factor, 6),
        "height_factor": round(height_factor, 6),
        "score": round(score, 6),
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
    if m["surface_area_mm2"] <= 0 or m["surface_per_volume"] <= 0:
        errors.append("surface_metric:non_positive")
    return errors


def write_result(result):
    for name in ("score.json", "quant_metrics.json"):
        try:
            (DESKTOP / name).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        except Exception:
            pass
    print("True" if result.get("valid") else "False")


def main():
    errors = []
    try:
        m = metrics(load_stl(DESKTOP / "optimized.stl"))
        errors.extend(design_summary_errors())
        errors.extend(hard_errors(m))
        score_bits = score_from_metrics(m)
        score = 0.0 if errors else score_bits["score"]
        result = {
            "case_id": CASE_SPEC["case_id"],
            "valid": not errors,
            "score": round(score, 6),
            "errors": errors,
            "metrics": m | score_bits,
            "baseline_metrics": CASE_SPEC["baseline_metrics"],
            "reference_metrics": CASE_SPEC["reference_metrics"],
        }
    except Exception as exc:
        result = {"case_id": CASE_SPEC["case_id"], "valid": False, "score": 0.0, "errors": [str(exc)], "metrics": {}}
    write_result(result)


if __name__ == "__main__":
    main()
