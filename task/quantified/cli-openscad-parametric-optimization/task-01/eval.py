#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import trimesh


CASE_SPEC = {
    "case_id": "quant-cli-openscad-parametric-task-01-ubuntu",
    "token": "EWQSCAD01",
    "title": "compact controller heat sink with straight external airflow channels",
    "objective": (
        "Maximize externally exposed geometric surface area per material volume. "
        "This is a geometry-only proxy, not a thermal simulation."
    ),
    "metric_kind": "external_surface_per_volume",
    "metric_description": (
        "(single connected exterior-shell area minus the base contact area) / material volume"
    ),
    "envelope_min_mm": [0.0, 0.0, 0.0],
    "envelope_max_mm": [80.0, 50.0, 28.0],
    "min_bbox_mm": [76.0, 46.0, 24.0],
    "min_volume_mm3": 14500.0,
    "max_volume_mm3": 54000.0,
    "base_thickness_mm": 4.0,
    "min_contact_area_mm2": 3800.0,
    "min_contact_span_mm": [76.0, 46.0],
    "min_fin_thickness_mm": 1.5,
    "min_fin_gap_mm": 3.0,
    "min_fin_count": 6,
    "max_fin_count": 16,
    "min_fin_run_mm": 44.0,
    "min_fin_top_z_mm": 24.0,
    "baseline_metrics": {
        "bbox_mm": [80.0, 50.0, 14.64],
        "volume_mm3": 48107.264,
        "external_surface_area_mm2": 7478.688,
        "external_surface_per_volume": 0.15545860,
    },
    "reference_metrics": {
        "bbox_mm": [80.0, 50.0, 28.0],
        "volume_mm3": 36644.8,
        "external_surface_area_mm2": 30225.6,
        "external_surface_per_volume": 0.82482644,
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
    """Count edge-connected surface shells without depending on scipy."""
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
        a, b, c = (int(x) for x in face)
        for edge in ((a, b), (b, c), (c, a)):
            key = tuple(sorted(edge))
            if key in edge_owner:
                union(face_index, edge_owner[key])
            else:
                edge_owner[key] = face_index
    return len({find(index) for index in range(len(faces))})


def projected_xy_area(triangles):
    if len(triangles) == 0:
        return 0.0
    edge_a = triangles[:, 1, :2] - triangles[:, 0, :2]
    edge_b = triangles[:, 2, :2] - triangles[:, 0, :2]
    return float(0.5 * np.abs(edge_a[:, 0] * edge_b[:, 1] - edge_a[:, 1] * edge_b[:, 0]).sum())


def projected_area(triangles, axes):
    if len(triangles) == 0:
        return 0.0
    points = triangles[:, :, axes]
    edge_a = points[:, 1] - points[:, 0]
    edge_b = points[:, 2] - points[:, 0]
    return float(0.5 * np.abs(edge_a[:, 0] * edge_b[:, 1] - edge_a[:, 1] * edge_b[:, 0]).sum())


def base_contact_metrics(mesh):
    triangles = np.asarray(mesh.triangles, dtype=float)
    bounds = np.asarray(mesh.bounds, dtype=float)
    min_z = float(bounds[0][2])
    bottom_mask = np.max(np.abs(triangles[:, :, 2] - min_z), axis=1) <= TOL
    bottom = triangles[bottom_mask]
    if len(bottom) == 0:
        return {
            "base_contact_area_mm2": 0.0,
            "base_contact_span_mm": [0.0, 0.0],
            "base_x_edge_wall_area_mm2": 0.0,
            "base_y_edge_wall_area_mm2": 0.0,
        }
    xy = bottom[:, :, :2].reshape((-1, 2))
    spans = np.max(xy, axis=0) - np.min(xy, axis=0)
    base_top = min_z + CASE_SPEC["base_thickness_mm"] + TOL
    near_base = np.max(triangles[:, :, 2], axis=1) <= base_top
    at_x_edge = (
        (np.max(np.abs(triangles[:, :, 0] - bounds[0][0]), axis=1) <= TOL)
        | (np.max(np.abs(triangles[:, :, 0] - bounds[1][0]), axis=1) <= TOL)
    )
    at_y_edge = (
        (np.max(np.abs(triangles[:, :, 1] - bounds[0][1]), axis=1) <= TOL)
        | (np.max(np.abs(triangles[:, :, 1] - bounds[1][1]), axis=1) <= TOL)
    )
    return {
        "base_contact_area_mm2": round(projected_xy_area(bottom), 4),
        "base_contact_span_mm": [round(float(x), 4) for x in spans],
        "base_x_edge_wall_area_mm2": round(projected_area(triangles[near_base & at_x_edge], [1, 2]), 4),
        "base_y_edge_wall_area_mm2": round(projected_area(triangles[near_base & at_y_edge], [0, 2]), 4),
    }


def straight_fin_metrics(mesh):
    """Measure paired, long Y-facing sides of straight fins above the base."""
    triangles = np.asarray(mesh.triangles, dtype=float)
    normals = np.asarray(mesh.face_normals, dtype=float)
    planes = {}
    for tri, normal in zip(triangles, normals):
        if abs(float(normal[0])) < 0.98 or np.ptp(tri[:, 0]) > TOL:
            continue
        y_span = float(np.ptp(tri[:, 1]))
        z_span = float(np.ptp(tri[:, 2]))
        if y_span < CASE_SPEC["min_fin_run_mm"] - TOL or z_span < 18.0:
            continue
        x = round(float(np.mean(tri[:, 0])), 3)
        entry = planes.setdefault(x, {"area_yz": 0.0, "y_min": 1e9, "y_max": -1e9, "z_min": 1e9, "z_max": -1e9})
        edge_a = tri[1, 1:] - tri[0, 1:]
        edge_b = tri[2, 1:] - tri[0, 1:]
        entry["area_yz"] += 0.5 * abs(float(edge_a[0] * edge_b[1] - edge_a[1] * edge_b[0]))
        entry["y_min"] = min(entry["y_min"], float(np.min(tri[:, 1])))
        entry["y_max"] = max(entry["y_max"], float(np.max(tri[:, 1])))
        entry["z_min"] = min(entry["z_min"], float(np.min(tri[:, 2])))
        entry["z_max"] = max(entry["z_max"], float(np.max(tri[:, 2])))

    valid_planes = []
    for x, data in planes.items():
        if (
            data["area_yz"] >= 700.0
            and data["y_max"] - data["y_min"] >= CASE_SPEC["min_fin_run_mm"] - TOL
            and data["z_min"] <= CASE_SPEC["base_thickness_mm"] + TOL
            and data["z_max"] >= CASE_SPEC["min_fin_top_z_mm"] - TOL
        ):
            valid_planes.append(x)
    valid_planes.sort()

    thicknesses = []
    gaps = []
    if len(valid_planes) % 2 == 0:
        thicknesses = [valid_planes[i + 1] - valid_planes[i] for i in range(0, len(valid_planes), 2)]
        gaps = [valid_planes[i + 2] - valid_planes[i + 1] for i in range(0, len(valid_planes) - 2, 2)]
    return {
        "fin_count": len(thicknesses),
        "fin_thicknesses_mm": [round(float(x), 4) for x in thicknesses],
        "fin_gaps_mm": [round(float(x), 4) for x in gaps],
        "fin_side_plane_count": len(valid_planes),
    }


def metrics(mesh):
    bounds = np.asarray(mesh.bounds, dtype=float)
    dims = bounds[1] - bounds[0]
    volume = float(mesh.volume)
    contact = base_contact_metrics(mesh)
    external_area = float(mesh.area) - contact["base_contact_area_mm2"]
    result = {
        "bounds_min_mm": [round(float(x), 4) for x in bounds[0]],
        "bounds_max_mm": [round(float(x), 4) for x in bounds[1]],
        "bbox_mm": [round(float(x), 4) for x in dims],
        "volume_mm3": round(volume, 4),
        "exterior_shell_area_mm2": round(float(mesh.area), 4),
        "external_surface_area_mm2": round(external_area, 4),
        "external_surface_per_volume": round(external_area / max(volume, 1e-9), 8),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "connected_shell_count": connected_shell_count(mesh),
    }
    result.update(contact)
    result.update(straight_fin_metrics(mesh))
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
    eff = m["external_surface_per_volume"]
    baseline = CASE_SPEC["baseline_metrics"]["external_surface_per_volume"]
    reference = CASE_SPEC["reference_metrics"]["external_surface_per_volume"]
    raw = (eff - baseline) / max(reference - baseline, 1e-9)
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
        "metric_value": round(eff, 8),
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
        errors.append(f"solid:must_have_one_connected_exterior_shell:got_{m['connected_shell_count']}")
    if m["base_contact_area_mm2"] < CASE_SPEC["min_contact_area_mm2"]:
        errors.append(f"base_contact_area:too_small:{m['base_contact_area_mm2']}")
    for axis, (got, minimum) in enumerate(zip(m["base_contact_span_mm"], CASE_SPEC["min_contact_span_mm"])):
        if got < minimum - TOL:
            errors.append(f"base_contact_span_axis_{axis}:too_small:{got}<{minimum}")
    min_x_walls = 2.0 * CASE_SPEC["min_contact_span_mm"][1] * CASE_SPEC["base_thickness_mm"]
    min_y_walls = 2.0 * CASE_SPEC["min_contact_span_mm"][0] * CASE_SPEC["base_thickness_mm"]
    if m["base_x_edge_wall_area_mm2"] < min_x_walls - 1.0:
        errors.append(f"base_thickness:x_edge_walls_too_small:{m['base_x_edge_wall_area_mm2']}")
    if m["base_y_edge_wall_area_mm2"] < min_y_walls - 1.0:
        errors.append(f"base_thickness:y_edge_walls_too_small:{m['base_y_edge_wall_area_mm2']}")
    if not (CASE_SPEC["min_fin_count"] <= m["fin_count"] <= CASE_SPEC["max_fin_count"]):
        errors.append(f"fin_count:outside_range:{m['fin_count']}")
    if any(value < CASE_SPEC["min_fin_thickness_mm"] - TOL for value in m["fin_thicknesses_mm"]):
        errors.append(f"fin_thickness:below_{CASE_SPEC['min_fin_thickness_mm']}_mm")
    if any(value < CASE_SPEC["min_fin_gap_mm"] - TOL for value in m["fin_gaps_mm"]):
        errors.append(f"fin_gap:below_{CASE_SPEC['min_fin_gap_mm']}_mm")
    if m["external_surface_area_mm2"] <= 0 or m["external_surface_per_volume"] <= 0:
        errors.append("external_surface_metric:non_positive")
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
        errors = design_summary_errors() + hard_errors(m)
        score_bits = score_from_metrics(m)
        result = {
            "case_id": CASE_SPEC["case_id"],
            "valid": not errors,
            "score": 0.0 if errors else score_bits["score"],
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
