#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import trimesh


CASE_SPEC = {
    "case_id": "quant-cli-openscad-parametric-task-02-ubuntu",
    "token": "EWQSCAD02",
    "title": "wide electronics cover with a continuous protective panel and perimeter walls",
    "objective": "Maximize measured solid protective-panel coverage per material volume.",
    "metric_kind": "solid_panel_coverage_per_volume",
    "metric_description": "solid XY area measured through the protective panel at z=1.99 mm / material volume",
    "envelope_min_mm": [0.0, 0.0, 0.0],
    "envelope_max_mm": [90.0, 65.0, 18.0],
    "min_bbox_mm": [86.0, 61.0, 10.0],
    "min_volume_mm3": 22000.0,
    "max_volume_mm3": 46000.0,
    "grid_pitch_mm": 1.0,
    "panel_check_z_mm": 1.99,
    "wall_check_z_mm": 8.0,
    "min_panel_thickness_mm": 2.0,
    "min_panel_coverage_ratio": 0.90,
    "max_panel_open_ratio": 0.10,
    "min_contact_area_mm2": 5265.0,
    "mounting_zone_size_mm": 10.0,
    "min_mounting_zone_coverage_ratio": 0.90,
    "min_wall_thickness_mm": 2.0,
    "min_wall_edge_coverage_ratio": 0.90,
    "max_wall_open_ratio_per_edge": 0.10,
    "baseline_metrics": {
        "bbox_mm": [90.0, 65.0, 9.34],
        "volume_mm3": 44811.5616,
        "protected_solid_area_mm2": 5850.0,
        "panel_coverage_ratio": 1.0,
        "solid_panel_coverage_per_volume": 0.13054667,
    },
    "reference_metrics": {
        "bbox_mm": [90.0, 65.0, 16.0],
        "volume_mm3": 32598.0,
        "protected_solid_area_mm2": 5850.0,
        "panel_coverage_ratio": 1.0,
        "solid_panel_coverage_per_volume": 0.17945886,
    },
}

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
    """Count edge-connected surface shells without scipy."""
    faces = np.asarray(mesh.faces, dtype=np.int64)
    parent = np.arange(len(faces), dtype=np.int64)

    def find(item):
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return int(item)

    def union(a, b):
        ra, rb = find(int(a)), find(int(b))
        if ra != rb:
            parent[rb] = ra

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
    """Return the Z intersection of a vertical ray with one triangle."""
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


def solid_slice_mask(mesh, z):
    """Rasterize actual solid occupancy at a fixed Z plane by ray parity."""
    pitch = CASE_SPEC["grid_pitch_mm"]
    width, depth = CASE_SPEC["envelope_max_mm"][:2]
    xs = np.arange(0.5 * pitch, width, pitch)
    ys = np.arange(0.5 * pitch, depth, pitch)
    triangles = np.asarray(mesh.triangles, dtype=float)
    mask = np.zeros((len(ys), len(xs)), dtype=bool)
    for row, y in enumerate(ys):
        for column, x in enumerate(xs):
            mask[row, column] = point_is_solid(triangles, x, y, z)
    return mask


def planar_surface_mask(mesh, z):
    """Rasterize only triangles lying on the specified contact plane."""
    pitch = CASE_SPEC["grid_pitch_mm"]
    width, depth = CASE_SPEC["envelope_max_mm"][:2]
    xs = np.arange(0.5 * pitch, width, pitch)
    ys = np.arange(0.5 * pitch, depth, pitch)
    triangles = np.asarray(mesh.triangles, dtype=float)
    triangles = triangles[np.max(np.abs(triangles[:, :, 2] - z), axis=1) <= TOL]
    mask = np.zeros((len(ys), len(xs)), dtype=bool)
    for row, y in enumerate(ys):
        for column, x in enumerate(xs):
            for triangle in triangles:
                hit = vertical_hit_z(x, y, triangle)
                if hit is not None and abs(hit - z) <= TOL:
                    mask[row, column] = True
                    break
    return mask


def component_metrics(mask):
    visited = np.zeros_like(mask, dtype=bool)
    component_sizes = []
    height, width = mask.shape
    for row in range(height):
        for column in range(width):
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
                        0 <= next_row < height
                        and 0 <= next_column < width
                        and mask[next_row, next_column]
                        and not visited[next_row, next_column]
                    ):
                        visited[next_row, next_column] = True
                        stack.append((next_row, next_column))
            component_sizes.append(size)
    return len(component_sizes), max(component_sizes, default=0)


def wall_inner_probe_ratios(mesh):
    """Probe just inside the declared 2 mm wall thickness on all four edges."""
    pitch = CASE_SPEC["grid_pitch_mm"]
    width, depth = CASE_SPEC["envelope_max_mm"][:2]
    inset = CASE_SPEC["min_wall_thickness_mm"] - 0.01
    xs = np.arange(0.5 * pitch, width, pitch)
    ys = np.arange(0.5 * pitch, depth, pitch)
    triangles = np.asarray(mesh.triangles, dtype=float)
    z = CASE_SPEC["wall_check_z_mm"]
    return {
        "left": float(np.mean([point_is_solid(triangles, inset, y, z) for y in ys])),
        "right": float(np.mean([point_is_solid(triangles, width - inset, y, z) for y in ys])),
        "front": float(np.mean([point_is_solid(triangles, x, inset, z) for x in xs])),
        "back": float(np.mean([point_is_solid(triangles, x, depth - inset, z) for x in xs])),
    }


def coverage_metrics(mesh):
    pitch = CASE_SPEC["grid_pitch_mm"]
    total_cells = int(round(CASE_SPEC["envelope_max_mm"][0] / pitch)) * int(
        round(CASE_SPEC["envelope_max_mm"][1] / pitch)
    )
    contact_mask = planar_surface_mask(mesh, CASE_SPEC["envelope_min_mm"][2])
    panel_mask = solid_slice_mask(mesh, CASE_SPEC["panel_check_z_mm"])
    wall_mask = solid_slice_mask(mesh, CASE_SPEC["wall_check_z_mm"])

    panel_components, largest_panel_component = component_metrics(panel_mask)
    zone_cells = int(round(CASE_SPEC["mounting_zone_size_mm"] / pitch))
    mounting_ratios = [
        float(contact_mask[:zone_cells, :zone_cells].mean()),
        float(contact_mask[:zone_cells, -zone_cells:].mean()),
        float(contact_mask[-zone_cells:, :zone_cells].mean()),
        float(contact_mask[-zone_cells:, -zone_cells:].mean()),
    ]
    wall_cells = int(round(CASE_SPEC["min_wall_thickness_mm"] / pitch))
    wall_edge_ratios = {
        "left": float(wall_mask[:, :wall_cells].mean()),
        "right": float(wall_mask[:, -wall_cells:].mean()),
        "front": float(wall_mask[:wall_cells, :].mean()),
        "back": float(wall_mask[-wall_cells:, :].mean()),
    }
    wall_probe_ratios = wall_inner_probe_ratios(mesh)
    protected_area = float(panel_mask.sum()) * pitch * pitch
    panel_ratio = float(panel_mask.sum()) / max(total_cells, 1)
    contact_area = float(contact_mask.sum()) * pitch * pitch
    return {
        "mounting_contact_area_mm2": round(contact_area, 4),
        "mounting_contact_coverage_ratio": round(float(contact_mask.sum()) / max(total_cells, 1), 6),
        "mounting_zone_coverage_ratios": [round(value, 6) for value in mounting_ratios],
        "protected_solid_area_mm2": round(protected_area, 4),
        "panel_coverage_ratio": round(panel_ratio, 6),
        "panel_open_ratio": round(1.0 - panel_ratio, 6),
        "panel_component_count": panel_components,
        "largest_panel_component_ratio": round(largest_panel_component / max(int(panel_mask.sum()), 1), 6),
        "wall_edge_coverage_ratios": {name: round(value, 6) for name, value in wall_edge_ratios.items()},
        "wall_edge_open_ratios": {name: round(1.0 - value, 6) for name, value in wall_edge_ratios.items()},
        "wall_inner_probe_coverage_ratios": {name: round(value, 6) for name, value in wall_probe_ratios.items()},
    }


def metrics(mesh):
    bounds = np.asarray(mesh.bounds, dtype=float)
    dims = bounds[1] - bounds[0]
    volume = float(mesh.volume)
    result = {
        "bounds_min_mm": [round(float(value), 4) for value in bounds[0]],
        "bounds_max_mm": [round(float(value), 4) for value in bounds[1]],
        "bbox_mm": [round(float(value), 4) for value in dims],
        "volume_mm3": round(volume, 4),
        "surface_area_mm2": round(float(mesh.area), 4),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "connected_shell_count": connected_shell_count(mesh),
    }
    result.update(coverage_metrics(mesh))
    result["solid_panel_coverage_per_volume"] = round(
        result["protected_solid_area_mm2"] / max(volume, 1e-9), 8
    )
    return result


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
    efficiency = m["solid_panel_coverage_per_volume"]
    baseline = CASE_SPEC["baseline_metrics"]["solid_panel_coverage_per_volume"]
    reference = CASE_SPEC["reference_metrics"]["solid_panel_coverage_per_volume"]
    raw = (efficiency - baseline) / max(reference - baseline, 1e-9)
    volume_factor = clamp(
        (CASE_SPEC["max_volume_mm3"] - m["volume_mm3"])
        / max(CASE_SPEC["max_volume_mm3"] - CASE_SPEC["reference_metrics"]["volume_mm3"], 1.0),
        0.0,
        1.10,
    )
    height_factor = clamp(m["bbox_mm"][2] / CASE_SPEC["envelope_max_mm"][2], 0.75, 1.0)
    score = clamp(0.88 * raw + 0.08 * volume_factor + 0.04 * height_factor)
    return {
        "metric_kind": CASE_SPEC["metric_kind"],
        "metric_value": round(efficiency, 8),
        "raw_efficiency_score": round(clamp(raw), 6),
        "volume_factor": round(volume_factor, 6),
        "height_factor": round(height_factor, 6),
        "score": round(score, 6),
    }


def hard_errors(m):
    errors = []
    for axis, (got, expected) in enumerate(zip(m["bounds_min_mm"], CASE_SPEC["envelope_min_mm"])):
        if abs(got - expected) > TOL:
            errors.append(f"bounds_min_axis_{axis}:must_be_{expected}:got_{got}")
    for axis, (got, maximum) in enumerate(zip(m["bounds_max_mm"], CASE_SPEC["envelope_max_mm"])):
        if got > maximum + TOL:
            errors.append(f"bounds_max_axis_{axis}:too_large:{got}>{maximum}")
    for axis, (got, minimum) in enumerate(zip(m["bbox_mm"], CASE_SPEC["min_bbox_mm"])):
        if got < minimum - TOL:
            errors.append(f"bbox_axis_{axis}:too_small:{got}<{minimum}")
    if not (CASE_SPEC["min_volume_mm3"] <= m["volume_mm3"] <= CASE_SPEC["max_volume_mm3"]):
        errors.append(f"volume:outside_range:{m['volume_mm3']}")
    if not m["watertight"] or not m["winding_consistent"] or m["volume_mm3"] <= 0:
        errors.append("solid:must_be_watertight_positive_and_winding_consistent")
    if m["connected_shell_count"] != 1:
        errors.append(f"solid:must_have_one_edge_connected_shell:got_{m['connected_shell_count']}")
    if m["mounting_contact_area_mm2"] < CASE_SPEC["min_contact_area_mm2"]:
        errors.append(f"mounting_contact_area:too_small:{m['mounting_contact_area_mm2']}")
    for index, ratio in enumerate(m["mounting_zone_coverage_ratios"]):
        if ratio < CASE_SPEC["min_mounting_zone_coverage_ratio"]:
            errors.append(f"mounting_zone_{index}:coverage_too_low:{ratio}")
    if m["panel_coverage_ratio"] < CASE_SPEC["min_panel_coverage_ratio"]:
        errors.append(f"protective_panel:coverage_too_low:{m['panel_coverage_ratio']}")
    if m["panel_open_ratio"] > CASE_SPEC["max_panel_open_ratio"] + 1e-9:
        errors.append(f"protective_panel:open_ratio_too_high:{m['panel_open_ratio']}")
    if m["panel_component_count"] != 1 or m["largest_panel_component_ratio"] < 0.999:
        errors.append("protective_panel:must_be_one_continuous_component")
    for edge, ratio in m["wall_edge_coverage_ratios"].items():
        if ratio < CASE_SPEC["min_wall_edge_coverage_ratio"]:
            errors.append(f"perimeter_wall_{edge}:coverage_or_thickness_too_low:{ratio}")
    for edge, ratio in m["wall_edge_open_ratios"].items():
        if ratio > CASE_SPEC["max_wall_open_ratio_per_edge"] + 1e-9:
            errors.append(f"perimeter_wall_{edge}:open_ratio_too_high:{ratio}")
    for edge, ratio in m["wall_inner_probe_coverage_ratios"].items():
        if ratio < CASE_SPEC["min_wall_edge_coverage_ratio"]:
            errors.append(f"perimeter_wall_{edge}:fails_1.99_mm_thickness_probe:{ratio}")
    if m["protected_solid_area_mm2"] <= 0 or m["solid_panel_coverage_per_volume"] <= 0:
        errors.append("solid_panel_metric:non_positive")
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
        measured = metrics(load_stl(DESKTOP / "optimized.stl"))
        errors = design_summary_errors() + hard_errors(measured)
        score_bits = score_from_metrics(measured)
        result = {
            "case_id": CASE_SPEC["case_id"],
            "valid": not errors,
            "score": 0.0 if errors else score_bits["score"],
            "errors": errors,
            "metrics": measured | score_bits,
            "baseline_metrics": CASE_SPEC["baseline_metrics"],
            "reference_metrics": CASE_SPEC["reference_metrics"],
        }
    except Exception as exc:
        result = {"case_id": CASE_SPEC["case_id"], "valid": False, "score": 0.0, "errors": [str(exc)], "metrics": {}}
    write_result(result)


if __name__ == "__main__":
    main()
