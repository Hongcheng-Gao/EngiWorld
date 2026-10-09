#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import trimesh

CASE_SPEC = {'case_id': 'quant-cli-openscad-parametric-task-04-ubuntu', 'token': 'EWQSCAD04', 'title': 'open cable-comb organizer with tall fingers', 'objective': 'Maximize cable clearance and exposed side surface per material volume for a cable-comb organizer.', 'metric_kind': 'clearance_surface_mix', 'metric_description': '0.72 * surface_area/volume plus 0.28 * side-clearance-span/volume; taller separated cable fingers with less material score higher', 'reference_design': 'back spine with eight separated vertical cable fingers', 'envelope_mm': [100.0, 55.0, 32.0], 'min_bbox_mm': [94.0, 49.0, 26.0], 'min_volume_mm3': 38000.0, 'max_volume_mm3': 76000.0, 'base_thickness_mm': 3.0, 'starter_block_size': [92.0, 45.1, 12.16], 'starter_block_center': [50.0, 27.5, 9.08], 'optimized_boxes': [{'name': 'back_spine', 'size': [94.0, 4.0, 25.0], 'center': [50.0, 3.0, 15.5]}, {'name': 'comb_finger_1', 'size': [4.0, 50.0, 25.0], 'center': [8.0, 28.0, 15.5]}, {'name': 'comb_finger_2', 'size': [4.0, 50.0, 25.0], 'center': [20.0, 28.0, 15.5]}, {'name': 'comb_finger_3', 'size': [4.0, 50.0, 25.0], 'center': [32.0, 28.0, 15.5]}, {'name': 'comb_finger_4', 'size': [4.0, 50.0, 25.0], 'center': [44.0, 28.0, 15.5]}, {'name': 'comb_finger_5', 'size': [4.0, 50.0, 25.0], 'center': [56.0, 28.0, 15.5]}, {'name': 'comb_finger_6', 'size': [4.0, 50.0, 25.0], 'center': [68.0, 28.0, 15.5]}, {'name': 'comb_finger_7', 'size': [4.0, 50.0, 25.0], 'center': [80.0, 28.0, 15.5]}, {'name': 'comb_finger_8', 'size': [4.0, 50.0, 25.0], 'center': [92.0, 28.0, 15.5]}], 'hard_constraints': ['Produce the required open geometry output file rather than only reporting metrics.', 'Stay inside the stated bounding envelope and above the minimum useful spans.', 'Stay within the stated material-volume range.', 'Do not read ground_truth, edit eval.py, or fabricate score/metric files.'], 'invalid_conditions': ['Missing, unparsable, empty, or implausibly small STL geometry.', 'Bounding-box or volume hard-constraint violation.', 'Self-reported metrics without valid geometry.', 'Native project files used as the only deliverable.'], 'baseline_metrics': {'bbox_mm': [100.0, 55.0, 15.16], 'volume_mm3': 66954.272, 'surface_area_mm2': 23562.672, 'surface_per_volume': 0.35192186}, 'reference_metrics': {'bbox_mm': [100.0, 55.0, 28.0], 'volume_mm3': 64300.0, 'surface_area_mm2': 36030.0, 'surface_per_volume': 0.56034215}, 'reference_score': {'metric_kind': 'clearance_surface_mix', 'metric_value': 0.41015241, 'surface_per_volume': 0.56034215, 'raw_efficiency_score': 1.0, 'volume_factor': 1.0, 'height_factor': 0.875, 'score': 0.995}}
CASE_SPEC.update(
    {
        "envelope_min_mm": [0.0, 0.0, 0.0],
        "grid_pitch_mm": 1.0,
        "contact_z_mm": 0.0,
        "finger_probe_z_mm": 24.0,
        "min_contact_coverage_ratio": 0.80,
        "min_contact_component_ratio": 0.95,
        "min_probe_open_ratio": 0.35,
        "min_finger_count": 4,
        "max_finger_count": 16,
        "min_finger_thickness_mm": 2.0,
        "min_finger_gap_mm": 3.0,
    }
)
DESKTOP = Path(os.environ.get("ENGIWORLD_EVAL_DIR") or os.environ.get("OUTPUT_ROOT") or "/home/user/Desktop")
TOL = 0.15


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
    return mesh


def connected_shell_count(mesh):
    faces = np.asarray(mesh.faces, dtype=np.int64)
    parent = np.arange(len(faces), dtype=np.int64)

    def find(item):
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return int(item)

    def union(a, b):
        root_a, root_b = find(int(a)), find(int(b))
        if root_a != root_b:
            parent[root_b] = root_a

    edge_owner = {}
    for face_index, face in enumerate(faces):
        a, b, c = (int(value) for value in face)
        for edge in ((a, b), (b, c), (c, a)):
            key = tuple(sorted(edge))
            if key in edge_owner:
                union(face_index, edge_owner[key])
            else:
                edge_owner[key] = face_index
    return len({find(index) for index in range(len(faces))})


def vertical_hit_z(x, y, triangle):
    a, b, c = triangle
    v0 = c[:2] - a[:2]
    v1 = b[:2] - a[:2]
    v2 = np.asarray([x, y], dtype=float) - a[:2]
    denominator = v0[0] * v1[1] - v1[0] * v0[1]
    if abs(float(denominator)) < 1e-10:
        return None
    u = (v2[0] * v1[1] - v1[0] * v2[1]) / denominator
    v = (v0[0] * v2[1] - v2[0] * v0[1]) / denominator
    if u < -1e-9 or v < -1e-9 or u + v > 1.0 + 1e-9:
        return None
    return float(a[2] + u * (c[2] - a[2]) + v * (b[2] - a[2]))


def point_is_solid(triangles, x, y, z):
    hits = []
    for triangle in triangles:
        hit = vertical_hit_z(x, y, triangle)
        if hit is None or hit <= z + 1e-7:
            continue
        if all(abs(hit - previous) > 1e-6 for previous in hits):
            hits.append(hit)
    return len(hits) % 2 == 1


def raster_mask(mesh, z, planar_only=False):
    pitch = CASE_SPEC["grid_pitch_mm"]
    width, depth = CASE_SPEC["envelope_mm"][:2]
    xs = np.arange(0.5 * pitch, width, pitch)
    ys = np.arange(0.5 * pitch, depth, pitch)
    triangles = np.asarray(mesh.triangles, dtype=float)
    if planar_only:
        triangles = triangles[np.max(np.abs(triangles[:, :, 2] - z), axis=1) <= TOL]
    mask = np.zeros((len(ys), len(xs)), dtype=bool)
    for row, y in enumerate(ys):
        for column, x in enumerate(xs):
            if planar_only:
                mask[row, column] = any(
                    (hit := vertical_hit_z(x, y, triangle)) is not None and abs(hit - z) <= TOL
                    for triangle in triangles
                )
            else:
                mask[row, column] = point_is_solid(triangles, x, y, z)
    return mask


def component_sizes(mask):
    visited = np.zeros_like(mask, dtype=bool)
    sizes = []
    rows, columns = mask.shape
    for row in range(rows):
        for column in range(columns):
            if not mask[row, column] or visited[row, column]:
                continue
            stack = [(row, column)]
            visited[row, column] = True
            size = 0
            while stack:
                current_row, current_column = stack.pop()
                size += 1
                for next_row, next_column in (
                    (current_row - 1, current_column),
                    (current_row + 1, current_column),
                    (current_row, current_column - 1),
                    (current_row, current_column + 1),
                ):
                    if (
                        0 <= next_row < rows
                        and 0 <= next_column < columns
                        and mask[next_row, next_column]
                        and not visited[next_row, next_column]
                    ):
                        visited[next_row, next_column] = True
                        stack.append((next_row, next_column))
            sizes.append(size)
    return sizes


def line_runs(line):
    runs = []
    start = None
    for index, occupied in enumerate(np.asarray(line, dtype=bool)):
        if occupied and start is None:
            start = index
        elif not occupied and start is not None:
            runs.append((start, index - 1))
            start = None
    if start is not None:
        runs.append((start, len(line) - 1))
    return runs


def separated_feature_metrics(mask):
    pitch = CASE_SPEC["grid_pitch_mm"]
    candidates = []
    for line in list(mask) + list(mask.T):
        runs = line_runs(line)
        if not runs:
            continue
        widths = [(end - start + 1) * pitch for start, end in runs]
        gaps = [(runs[index + 1][0] - runs[index][1] - 1) * pitch for index in range(len(runs) - 1)]
        candidates.append(
            {
                "count": len(runs),
                "min_width": min(widths),
                "min_gap": min(gaps, default=0.0),
            }
        )
    best = max(candidates, key=lambda item: (item["count"], item["min_gap"], item["min_width"]))
    return best


def functional_metrics(mesh):
    contact = raster_mask(mesh, CASE_SPEC["contact_z_mm"], planar_only=True)
    probe = raster_mask(mesh, CASE_SPEC["finger_probe_z_mm"])
    contact_sizes = component_sizes(contact)
    features = separated_feature_metrics(probe)
    return {
        "contact_coverage_ratio": round(float(contact.mean()), 6),
        "largest_contact_component_ratio": round(
            max(contact_sizes, default=0) / max(int(contact.sum()), 1), 6
        ),
        "finger_probe_z_mm": CASE_SPEC["finger_probe_z_mm"],
        "finger_run_count": features["count"],
        "min_finger_run_width_mm": round(features["min_width"], 4),
        "min_finger_clear_gap_mm": round(features["min_gap"], 4),
        "finger_probe_open_ratio": round(1.0 - float(probe.mean()), 6),
    }


def metrics(mesh):
    bounds = np.asarray(mesh.bounds, dtype=float)
    dims = (bounds[1] - bounds[0]).tolist()
    volume = float(mesh.volume)
    area = float(mesh.area)
    result = {
        "bounds_min_mm": [round(float(x), 4) for x in bounds[0]],
        "bounds_max_mm": [round(float(x), 4) for x in bounds[1]],
        "bbox_mm": [round(float(x), 4) for x in dims],
        "volume_mm3": round(volume, 4),
        "surface_area_mm2": round(area, 4),
        "surface_per_volume": round(area / max(volume, 1e-9), 8),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "is_volume": bool(mesh.is_volume),
        "connected_shell_count": connected_shell_count(mesh),
    }
    result.update(functional_metrics(mesh))
    return result


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
    for axis, (got, minimum) in enumerate(zip(m["bounds_min_mm"], CASE_SPEC["envelope_min_mm"])):
        if got < minimum - TOL:
            errors.append(f"bounds_min_axis_{axis}:below_envelope:{got}<{minimum}")
    for axis, (got, maximum) in enumerate(zip(m["bounds_max_mm"], CASE_SPEC["envelope_mm"])):
        if got > maximum + TOL:
            errors.append(f"bounds_max_axis_{axis}:above_envelope:{got}>{maximum}")
    for i, (got, max_allowed) in enumerate(zip(dims, CASE_SPEC["envelope_mm"])):
        if got > max_allowed + TOL:
            errors.append(f"bbox_axis_{i}:too_large:{got}>{max_allowed}")
    for i, (got, min_allowed) in enumerate(zip(dims, CASE_SPEC["min_bbox_mm"])):
        if got < min_allowed - TOL:
            errors.append(f"bbox_axis_{i}:too_small:{got}<{min_allowed}")
    if not (CASE_SPEC["min_volume_mm3"] <= m["volume_mm3"] <= CASE_SPEC["max_volume_mm3"]):
        errors.append(f"volume:outside_range:{m['volume_mm3']}")
    if not m["watertight"] or not m["winding_consistent"] or not m["is_volume"]:
        errors.append("solid:must_be_watertight_positive_and_winding_consistent")
    if m["connected_shell_count"] != 1:
        errors.append(f"solid:must_have_one_edge_connected_shell:got_{m['connected_shell_count']}")
    if m["contact_coverage_ratio"] < CASE_SPEC["min_contact_coverage_ratio"]:
        errors.append(f"base_contact:coverage_too_low:{m['contact_coverage_ratio']}")
    if m["largest_contact_component_ratio"] < CASE_SPEC["min_contact_component_ratio"]:
        errors.append(f"base_contact:largest_component_too_small:{m['largest_contact_component_ratio']}")
    if not (CASE_SPEC["min_finger_count"] <= m["finger_run_count"] <= CASE_SPEC["max_finger_count"]):
        errors.append(f"fingers:count_outside_range:{m['finger_run_count']}")
    if m["min_finger_run_width_mm"] < CASE_SPEC["min_finger_thickness_mm"]:
        errors.append(f"fingers:thickness_too_small:{m['min_finger_run_width_mm']}")
    if m["min_finger_clear_gap_mm"] < CASE_SPEC["min_finger_gap_mm"]:
        errors.append(f"fingers:clear_gap_too_small:{m['min_finger_clear_gap_mm']}")
    if m["finger_probe_open_ratio"] < CASE_SPEC["min_probe_open_ratio"]:
        errors.append(f"fingers:open_ratio_too_low:{m['finger_probe_open_ratio']}")
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
