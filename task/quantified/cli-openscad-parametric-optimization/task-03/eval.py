#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import trimesh


CASE_SPEC = {
    "case_id": "quant-cli-openscad-parametric-task-03-ubuntu",
    "token": "EWQSCAD03",
    "title": "long lightweight cable-tray bridge under a defined bending load case",
    "objective": "Maximize calculated vertical bending stiffness per material volume.",
    "metric_kind": "calculated_stiffness_per_volume",
    "metric_description": "Euler-Bernoulli center-load stiffness 48*E*I_min/L^3 divided by material volume",
    "envelope_min_mm": [0.0, 0.0, 0.0],
    "envelope_max_mm": [130.0, 38.0, 45.0],
    "min_bbox_mm": [124.0, 32.0, 36.0],
    "min_volume_mm3": 52000.0,
    "max_volume_mm3": 98000.0,
    "material": {
        "model": "isotropic linear elastic geometry proxy",
        "youngs_modulus_n_per_mm2": 2000.0,
        "allowable_bending_stress_mpa": 12.0,
    },
    "load_case": {
        "support_x_mm": [2.0, 128.0],
        "span_mm": 126.0,
        "center_load_n": 100.0,
        "load_direction": "negative Z",
        "support_z_mm": 0.0,
        "support_zone_x_mm": [[0.0, 5.0], [125.0, 130.0]],
        "min_support_contact_area_each_mm2": 170.0,
        "load_patch_x_mm": [62.0, 68.0],
        "load_patch_y_mm": [[5.0, 9.0], [29.0, 33.0]],
        "min_load_area_each_mm2": 20.0,
        "min_load_surface_z_mm": 40.0,
    },
    "section_pitch_mm": 1.0,
    "section_x_samples_mm": [round(float(value), 2) for value in np.arange(5.0, 125.01, 2.5)],
    "min_effective_I_y_mm4": 75000.0,
    "max_predicted_deflection_mm": 0.03,
    "baseline_metrics": {
        "bbox_mm": [130.0, 38.0, 21.1],
        "volume_mm3": 83487.1923,
        "effective_I_y_mm4": 202.6667,
        "calculated_stiffness_n_per_mm": 9.726171,
        "calculated_stiffness_per_volume": 0.00011650,
    },
    "reference_metrics": {
        "bbox_mm": [130.0, 38.0, 42.0],
        "volume_mm3": 73024.0,
        "effective_I_y_mm4": 81472.0,
        "predicted_center_deflection_mm": 0.02557596,
        "predicted_max_bending_stress_mpa": 1.005253,
        "calculated_stiffness_n_per_mm": 3909.920935,
        "calculated_stiffness_per_volume": 0.05354296,
    },
}

DESKTOP = Path(os.environ.get("ENGIWORLD_EVAL_DIR") or os.environ.get("OUTPUT_ROOT") or "/home/user/Desktop")
TOL = 0.15


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, float(value)))


def as_mesh(obj):
    if isinstance(obj, trimesh.Scene):
        meshes = [geometry for geometry in obj.geometry.values() if isinstance(geometry, trimesh.Trimesh)]
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


def projected_xy_hit(x, y, triangle):
    a, b, c = triangle
    v0 = c[:2] - a[:2]
    v1 = b[:2] - a[:2]
    v2 = np.asarray([x, y], dtype=float) - a[:2]
    denominator = v0[0] * v1[1] - v1[0] * v0[1]
    if abs(float(denominator)) < 1e-10:
        return False
    u = (v2[0] * v1[1] - v1[0] * v2[1]) / denominator
    v = (v0[0] * v2[1] - v2[0] * v0[1]) / denominator
    return bool(u >= -1e-9 and v >= -1e-9 and u + v <= 1.0 + 1e-9)


def projected_yz_hit_x(y, z, triangle):
    a, b, c = triangle
    v0 = c[1:] - a[1:]
    v1 = b[1:] - a[1:]
    v2 = np.asarray([y, z], dtype=float) - a[1:]
    denominator = v0[0] * v1[1] - v1[0] * v0[1]
    if abs(float(denominator)) < 1e-10:
        return None
    u = (v2[0] * v1[1] - v1[0] * v2[1]) / denominator
    v = (v0[0] * v2[1] - v2[0] * v0[1]) / denominator
    if u < -1e-9 or v < -1e-9 or u + v > 1.0 + 1e-9:
        return None
    return float(a[0] + u * (c[0] - a[0]) + v * (b[0] - a[0]))


def raster_xy_surface(mesh, selector):
    pitch = CASE_SPEC["section_pitch_mm"]
    width, depth = CASE_SPEC["envelope_max_mm"][:2]
    xs = np.arange(0.5 * pitch, width, pitch)
    ys = np.arange(0.5 * pitch, depth, pitch)
    triangles = np.asarray(mesh.triangles, dtype=float)
    normals = np.asarray(mesh.face_normals, dtype=float)
    selected = [triangle for triangle, normal in zip(triangles, normals) if selector(triangle, normal)]
    mask = np.zeros((len(ys), len(xs)), dtype=bool)
    for row, y in enumerate(ys):
        for column, x in enumerate(xs):
            mask[row, column] = any(projected_xy_hit(x, y, triangle) for triangle in selected)
    return mask


def boundary_contact_metrics(mesh):
    pitch = CASE_SPEC["section_pitch_mm"]
    bottom = raster_xy_surface(
        mesh,
        lambda triangle, normal: normal[2] < -0.9
        and np.max(np.abs(triangle[:, 2] - CASE_SPEC["load_case"]["support_z_mm"])) <= TOL,
    )
    top = raster_xy_surface(
        mesh,
        lambda triangle, normal: normal[2] > 0.9
        and np.ptp(triangle[:, 2]) <= TOL
        and np.mean(triangle[:, 2]) >= CASE_SPEC["load_case"]["min_load_surface_z_mm"] - TOL,
    )
    support_areas = []
    for low, high in CASE_SPEC["load_case"]["support_zone_x_mm"]:
        first, last = int(round(low / pitch)), int(round(high / pitch))
        support_areas.append(float(bottom[:, first:last].sum()) * pitch * pitch)
    load_areas = []
    x_low, x_high = CASE_SPEC["load_case"]["load_patch_x_mm"]
    x_first, x_last = int(round(x_low / pitch)), int(round(x_high / pitch))
    for y_low, y_high in CASE_SPEC["load_case"]["load_patch_y_mm"]:
        y_first, y_last = int(round(y_low / pitch)), int(round(y_high / pitch))
        load_areas.append(float(top[y_first:y_last, x_first:x_last].sum()) * pitch * pitch)
    return {
        "support_contact_areas_mm2": [round(value, 4) for value in support_areas],
        "load_patch_areas_mm2": [round(value, 4) for value in load_areas],
    }


def yz_ray_hits(mesh):
    """Compute X crossings once for every Y-Z cell; reuse them for all sections."""
    pitch = CASE_SPEC["section_pitch_mm"]
    depth, height = CASE_SPEC["envelope_max_mm"][1], CASE_SPEC["envelope_max_mm"][2]
    ys = np.arange(0.5 * pitch, depth, pitch)
    zs = np.arange(0.5 * pitch, height, pitch)
    triangles = np.asarray(mesh.triangles, dtype=float)
    hit_grid = [[None for _ in ys] for _ in zs]
    for z_index, z in enumerate(zs):
        for y_index, y in enumerate(ys):
            hits = []
            for triangle in triangles:
                hit = projected_yz_hit_x(y, z, triangle)
                if hit is not None and all(abs(hit - previous) > 1e-6 for previous in hits):
                    hits.append(hit)
            hit_grid[z_index][y_index] = sorted(hits)
    return ys, zs, hit_grid


def section_mask_at_x(hit_grid, x):
    height = len(hit_grid)
    width = len(hit_grid[0]) if height else 0
    mask = np.zeros((height, width), dtype=bool)
    for row in range(height):
        for column in range(width):
            mask[row, column] = sum(hit > x + 1e-7 for hit in hit_grid[row][column]) % 2 == 1
    return mask


def component_count(mask):
    visited = np.zeros_like(mask, dtype=bool)
    count = 0
    rows, columns = mask.shape
    for row in range(rows):
        for column in range(columns):
            if not mask[row, column] or visited[row, column]:
                continue
            count += 1
            visited[row, column] = True
            stack = [(row, column)]
            while stack:
                current_row, current_column = stack.pop()
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
    return count


def section_structural_metrics(mesh):
    pitch = CASE_SPEC["section_pitch_mm"]
    ys, zs, hit_grid = yz_ray_hits(mesh)
    z_grid = np.repeat(zs[:, None], len(ys), axis=1)
    sections = []
    supports = CASE_SPEC["load_case"]["support_x_mm"]
    load = CASE_SPEC["load_case"]["center_load_n"]
    for x in CASE_SPEC["section_x_samples_mm"]:
        mask = section_mask_at_x(hit_grid, x)
        area = float(mask.sum()) * pitch * pitch
        if area <= 0:
            sections.append({"x": x, "area": 0.0, "I": 0.0, "stress": 1e30, "components": 0})
            continue
        occupied_z = z_grid[mask]
        centroid_z = float(np.mean(occupied_z))
        inertia = float(np.sum((occupied_z - centroid_z) ** 2 + pitch * pitch / 12.0) * pitch * pitch)
        z_min = float(np.min(occupied_z) - 0.5 * pitch)
        z_max = float(np.max(occupied_z) + 0.5 * pitch)
        extreme_distance = max(centroid_z - z_min, z_max - centroid_z)
        moment = 0.5 * load * min(max(x - supports[0], 0.0), max(supports[1] - x, 0.0))
        stress = moment * extreme_distance / max(inertia, 1e-9)
        sections.append(
            {
                "x": x,
                "area": area,
                "centroid_z": centroid_z,
                "I": inertia,
                "stress": stress,
                "components": component_count(mask),
            }
        )
    effective_I = min(section["I"] for section in sections)
    minimum_area = min(section["area"] for section in sections)
    maximum_stress = max(section["stress"] for section in sections)
    maximum_components = max(section["components"] for section in sections)
    E = CASE_SPEC["material"]["youngs_modulus_n_per_mm2"]
    span = CASE_SPEC["load_case"]["span_mm"]
    load = CASE_SPEC["load_case"]["center_load_n"]
    stiffness = 48.0 * E * effective_I / (span**3)
    deflection = load / max(stiffness, 1e-9)
    governing_I_section = min(sections, key=lambda section: section["I"])
    governing_stress_section = max(sections, key=lambda section: section["stress"])
    return {
        "section_sample_count": len(sections),
        "minimum_section_area_mm2": round(minimum_area, 4),
        "effective_I_y_mm4": round(effective_I, 4),
        "governing_I_section_x_mm": governing_I_section["x"],
        "maximum_section_component_count": maximum_components,
        "predicted_center_deflection_mm": round(deflection, 8),
        "predicted_max_bending_stress_mpa": round(maximum_stress, 6),
        "governing_stress_section_x_mm": governing_stress_section["x"],
        "calculated_stiffness_n_per_mm": round(stiffness, 6),
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
    result.update(boundary_contact_metrics(mesh))
    result.update(section_structural_metrics(mesh))
    result["calculated_stiffness_per_volume"] = round(
        result["calculated_stiffness_n_per_mm"] / max(volume, 1e-9), 8
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


def score_from_metrics(measured):
    efficiency = measured["calculated_stiffness_per_volume"]
    baseline = CASE_SPEC["baseline_metrics"]["calculated_stiffness_per_volume"]
    reference = CASE_SPEC["reference_metrics"]["calculated_stiffness_per_volume"]
    raw = (efficiency - baseline) / max(reference - baseline, 1e-9)
    volume_factor = clamp(
        (CASE_SPEC["max_volume_mm3"] - measured["volume_mm3"])
        / max(CASE_SPEC["max_volume_mm3"] - CASE_SPEC["reference_metrics"]["volume_mm3"], 1.0),
        0.0,
        1.10,
    )
    height_factor = clamp(measured["bbox_mm"][2] / CASE_SPEC["envelope_max_mm"][2], 0.75, 1.0)
    score = clamp(0.88 * raw + 0.08 * volume_factor + 0.04 * height_factor)
    return {
        "metric_kind": CASE_SPEC["metric_kind"],
        "metric_value": round(efficiency, 8),
        "raw_efficiency_score": round(clamp(raw), 6),
        "volume_factor": round(volume_factor, 6),
        "height_factor": round(height_factor, 6),
        "score": round(score, 6),
    }


def hard_errors(measured):
    errors = []
    for axis, (got, expected) in enumerate(zip(measured["bounds_min_mm"], CASE_SPEC["envelope_min_mm"])):
        if abs(got - expected) > TOL:
            errors.append(f"bounds_min_axis_{axis}:must_be_{expected}:got_{got}")
    for axis, (got, maximum) in enumerate(zip(measured["bounds_max_mm"], CASE_SPEC["envelope_max_mm"])):
        if got > maximum + TOL:
            errors.append(f"bounds_max_axis_{axis}:too_large:{got}>{maximum}")
    for axis, (got, minimum) in enumerate(zip(measured["bbox_mm"], CASE_SPEC["min_bbox_mm"])):
        if got < minimum - TOL:
            errors.append(f"bbox_axis_{axis}:too_small:{got}<{minimum}")
    if not (CASE_SPEC["min_volume_mm3"] <= measured["volume_mm3"] <= CASE_SPEC["max_volume_mm3"]):
        errors.append(f"volume:outside_range:{measured['volume_mm3']}")
    if not measured["watertight"] or not measured["winding_consistent"] or measured["volume_mm3"] <= 0:
        errors.append("solid:must_be_watertight_positive_and_winding_consistent")
    if measured["connected_shell_count"] != 1:
        errors.append(f"solid:must_have_one_edge_connected_shell:got_{measured['connected_shell_count']}")
    for index, area in enumerate(measured["support_contact_areas_mm2"]):
        if area < CASE_SPEC["load_case"]["min_support_contact_area_each_mm2"]:
            errors.append(f"support_{index}:contact_area_too_small:{area}")
    for index, area in enumerate(measured["load_patch_areas_mm2"]):
        if area < CASE_SPEC["load_case"]["min_load_area_each_mm2"]:
            errors.append(f"load_patch_{index}:bearing_area_too_small:{area}")
    if measured["maximum_section_component_count"] != 1:
        errors.append(f"load_path:cross_sections_must_be_connected:got_{measured['maximum_section_component_count']}")
    if measured["effective_I_y_mm4"] < CASE_SPEC["min_effective_I_y_mm4"]:
        errors.append(f"effective_I_y:too_small:{measured['effective_I_y_mm4']}")
    if measured["predicted_center_deflection_mm"] > CASE_SPEC["max_predicted_deflection_mm"]:
        errors.append(f"predicted_deflection:too_large:{measured['predicted_center_deflection_mm']}")
    if measured["predicted_max_bending_stress_mpa"] > CASE_SPEC["material"]["allowable_bending_stress_mpa"]:
        errors.append(f"predicted_bending_stress:too_large:{measured['predicted_max_bending_stress_mpa']}")
    if measured["calculated_stiffness_per_volume"] <= 0:
        errors.append("calculated_stiffness_metric:non_positive")
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
