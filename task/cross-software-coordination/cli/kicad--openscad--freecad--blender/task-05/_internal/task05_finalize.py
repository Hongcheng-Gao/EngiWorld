#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "task-05"
TP_REFS = ("TP1", "TP2", "TP3", "TP4")
ACCESS_REFS = (*TP_REFS, "J1")
SOFTWARE_SEQUENCE = ["KiCad", "OpenSCAD", "FreeCAD", "Blender"]
REQUIRED_ARTIFACTS = [
    "01_kicad_board.kicad_pcb",
    "01_kicad_export.json",
    "01_kicad_board.step",
    "01_kicad_mechanical_map.csv",
    "01_kicad_parameters.scad",
    "02_openscad_enclosure.scad",
    "02_openscad_enclosure.stl",
    "02_openscad_parameters.json",
    "03_freecad_assembly.step",
    "03_freecad_assembly.obj",
    "03_freecad_clearance_report.json",
    "04_blender_review.blend",
    "04_blender_review.obj",
    "04_blender_review.mtl",
    "04_blender_review.png",
    "04_blender_scene_report.json",
    "toolchain_invocation_log.json",
    "final_release_package.json",
]
HASHED_ARTIFACTS = REQUIRED_ARTIFACTS[:-1]
FREECAD_REQUIRED_FIELDS = [
    "access_checks",
    "component_top_clearances_mm",
    "decision",
    "enclosure_bbox_mm",
    "enclosure_mass_g",
    "enclosure_volume_mm3",
    "lid_mass_g",
    "lid_separation_mm",
    "lid_volume_mm3",
    "minimum_side_clearance_mm",
    "minimum_top_clearance_mm",
    "side_clearances_mm",
    "standoff_checks",
    "tray_mass_g",
    "tray_volume_mm3",
    "unintended_interference_volume_mm3",
]
BLENDER_COPIED_FREECAD_FIELDS = [
    "enclosure_volume_mm3",
    "enclosure_mass_g",
    "minimum_side_clearance_mm",
    "minimum_top_clearance_mm",
    "standoff_checks",
    "access_checks",
    "unintended_interference_volume_mm3",
    "decision",
]


def json_dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def version(command: list[str]) -> str:
    completed = subprocess.run(command, text=True, capture_output=True, timeout=60, check=False)
    output = (completed.stdout + "\n" + completed.stderr).strip()
    if completed.returncode != 0:
        raise RuntimeError(
            f"version command failed ({completed.returncode}): {shlex.join(command)}\n{output}"
        )
    lines = [line.strip() for line in output.splitlines() if line.strip() and not line.strip().endswith("%")]
    if not lines:
        raise RuntimeError(f"version command returned no usable output: {shlex.join(command)}")
    return lines[0]


def number(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def close_number(actual: object, expected: float, tolerance: float) -> bool:
    value = number(actual)
    return value is not None and abs(value - expected) <= tolerance


def close_vector(actual: object, expected: list[float], tolerance: float) -> bool:
    return (
        isinstance(actual, list)
        and len(actual) == len(expected)
        and all(close_number(value, target, tolerance) for value, target in zip(actual, expected))
    )


def at_least(actual: object, minimum: float, tolerance: float = 0.0) -> bool:
    value = number(actual)
    return value is not None and value + tolerance >= minimum


def at_most(actual: object, maximum: float, tolerance: float = 0.0) -> bool:
    value = number(actual)
    return value is not None and value <= maximum + tolerance


def mass_matches(
    volume_mm3: object,
    mass_g: object,
    density_g_cm3: float,
    relative_tolerance: float,
) -> bool:
    volume = number(volume_mm3)
    mass = number(mass_g)
    if volume is None or mass is None or volume <= 0.0:
        return False
    expected = volume * density_g_cm3 / 1000.0
    return abs(mass - expected) <= max(0.001, abs(expected) * relative_tolerance)


def records_by_name(raw: object, name_key: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    if isinstance(raw, dict):
        for name, item in raw.items():
            if isinstance(item, dict):
                result[str(name).upper()] = item
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and item.get(name_key):
                result[str(item[name_key]).upper()] = item
    return result


def top_access_passes(
    entry: dict[str, Any],
    connector: dict[str, str],
    component: dict[str, Any],
    requirements: dict[str, Any],
) -> bool:
    geometry_tolerance = float(requirements["geometry_tolerance_mm"])
    axis_tolerance = float(requirements["axis_tolerance_mm"])
    volume_tolerance = float(requirements["interference_volume_tolerance_mm3"])
    guard = float(requirements["minimum_access_guard_mm"])
    expected_cutter = [float(value) for value in requirements["pogo_access"]["lid_bore_cutter_z_bounds_mm"]]
    expected_path = [float(value) for value in requirements["pogo_access"]["continuous_path_z_bounds_mm"]]
    return (
        entry.get("access_type") == "top_bore"
        and entry.get("direction") == "Z_PLUS"
        and entry.get("through") is True
        and entry.get("minimum_guard_material_present") is True
        and at_most(entry.get("residual_material_volume_mm3"), volume_tolerance)
        and at_most(entry.get("axis_error_mm"), axis_tolerance, geometry_tolerance)
        and at_most(entry.get("diameter_error_mm"), geometry_tolerance)
        and at_least(entry.get("minimum_guard_mm"), guard, geometry_tolerance)
        and close_number(entry.get("finished_diameter_mm"), float(connector["finished_diameter_mm"]), geometry_tolerance)
        and close_number(entry.get("x_mm"), float(component["x_mm"]), axis_tolerance)
        and close_number(entry.get("y_mm"), float(component["y_mm"]), axis_tolerance)
        and close_vector(entry.get("cutter_z_bounds_mm"), expected_cutter, geometry_tolerance)
        and close_vector(entry.get("path_z_bounds_mm"), expected_path, geometry_tolerance)
    )


def side_access_passes(
    entry: dict[str, Any],
    connector: dict[str, str],
    requirements: dict[str, Any],
) -> bool:
    geometry_tolerance = float(requirements["geometry_tolerance_mm"])
    volume_tolerance = float(requirements["interference_volume_tolerance_mm3"])
    guard = float(requirements["minimum_access_guard_mm"])
    bounds = [
        float(connector["cutter_x_min_mm"]),
        float(connector["cutter_y_min_mm"]),
        float(connector["cutter_z_min_mm"]),
        float(connector["cutter_x_max_mm"]),
        float(connector["cutter_y_max_mm"]),
        float(connector["cutter_z_max_mm"]),
    ]
    return (
        entry.get("access_type") == "side_window"
        and entry.get("direction") == "Y_PLUS"
        and entry.get("through") is True
        and entry.get("minimum_guard_material_present") is True
        and at_most(entry.get("residual_material_volume_mm3"), volume_tolerance)
        and at_most(entry.get("center_error_mm"), float(requirements["access_center_tolerance_mm"]), geometry_tolerance)
        and at_most(entry.get("width_error_mm"), geometry_tolerance)
        and at_most(entry.get("height_error_mm"), geometry_tolerance)
        and at_least(entry.get("minimum_guard_mm"), guard, geometry_tolerance)
        and close_number(entry.get("finished_width_mm"), float(connector["finished_width_mm"]), geometry_tolerance)
        and close_number(entry.get("finished_height_mm"), float(connector["finished_height_mm"]), geometry_tolerance)
        and close_vector(entry.get("bounds_mm"), bounds, geometry_tolerance)
        and bounds[5] - bounds[2] < float(requirements["tray_outer_top_z_mm"]) - geometry_tolerance
    )


def standoffs_pass(
    raw: object,
    mounting_holes: list[dict[str, Any]],
    requirements: dict[str, Any],
) -> bool:
    checks = records_by_name(raw, "ref")
    expected = {str(item["ref"]).upper(): item for item in mounting_holes}
    if set(checks) != set(expected) or len(checks) != 4:
        return False
    geometry_tolerance = float(requirements["geometry_tolerance_mm"])
    axis_tolerance = float(requirements["axis_tolerance_mm"])
    volume_tolerance = float(requirements["interference_volume_tolerance_mm3"])
    z_min = float(requirements["base_thickness_mm"]) - float(requirements["standoff_bore_overcut_mm"])
    z_max = float(requirements["board_bottom_z_mm"]) + float(requirements["standoff_bore_overcut_mm"])
    for ref, entry in checks.items():
        hole = expected[ref]
        if entry.get("continuous_bore") is not True or entry.get("standoff_present") is not True:
            return False
        if not at_least(entry.get("present_material_fraction"), 0.95):
            return False
        if not at_most(entry.get("residual_bore_material_volume_mm3"), volume_tolerance):
            return False
        if not at_most(entry.get("axis_error_mm"), axis_tolerance, geometry_tolerance):
            return False
        if not close_number(entry.get("x_mm"), float(hole["x_mm"]), axis_tolerance):
            return False
        if not close_number(entry.get("y_mm"), float(hole["y_mm"]), axis_tolerance):
            return False
        if not close_number(entry.get("bore_diameter_mm"), float(requirements["standoff_bore_diameter_mm"]), geometry_tolerance):
            return False
        if not close_number(entry.get("outer_diameter_mm"), float(requirements["standoff_outer_diameter_mm"]), geometry_tolerance):
            return False
        if not close_number(entry.get("bore_z_min_mm"), z_min, geometry_tolerance):
            return False
        if not close_number(entry.get("bore_z_max_mm"), z_max, geometry_tolerance):
            return False
    return True


def side_clearances_pass(report: dict[str, Any], requirements: dict[str, Any]) -> bool:
    required = float(requirements["minimum_side_clearance_mm"])
    tolerance = float(requirements["geometry_tolerance_mm"])
    directions = {"X_MINUS", "X_PLUS", "Y_MINUS", "Y_PLUS"}
    values = report.get("side_clearances_mm")
    if not isinstance(values, dict) or set(values) != directions:
        return False
    measured = [number(values[direction]) for direction in sorted(directions)]
    if any(value is None or value + tolerance < required for value in measured):
        return False
    actual_minimum = min(value for value in measured if value is not None)
    return close_number(report.get("minimum_side_clearance_mm"), actual_minimum, tolerance)


def normalize(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", str(value).upper()).strip("_")


def overlay_tokens(report: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for key in ("visible_features", "visible_accesses", "visible_overlays", "overlay_geometry"):
        raw = report.get(key, [])
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    result.extend(normalize(item.get(name, "")) for name in ("name", "ref", "role", "direction"))
                else:
                    result.append(normalize(item))
    materials = report.get("overlay_materials")
    if isinstance(materials, dict):
        result.extend(normalize(name) for name in materials)
    return [token for token in result if token]


def overlay_feature_present(tokens: list[str], *pieces: str) -> bool:
    expected = [normalize(piece) for piece in pieces]
    return any(all(piece in token for piece in expected) for token in tokens)


def main() -> None:
    work = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    internal = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/engiworld-task05-internal")
    kicad = os.environ.get("ENGIWORLD_KICAD_CLI") or shutil.which("kicad-cli") or "/usr/bin/kicad-cli"
    blender = os.environ.get("ENGIWORLD_BLENDER") or shutil.which("blender") or "/snap/bin/blender"
    freecad = os.environ.get("ENGIWORLD_FREECAD") or shutil.which("freecadcmd") or "freecadcmd"
    openscad = os.environ.get("ENGIWORLD_OPENSCAD") or shutil.which("openscad") or "/usr/bin/openscad"

    missing = [name for name in REQUIRED_ARTIFACTS[:-2] if not (work / name).is_file()]
    if missing:
        raise RuntimeError(f"cannot finalize {TASK}; missing artifacts: " + ", ".join(missing))
    requirements = json.loads((work / "mechanical_requirements.json").read_text(encoding="utf-8"))
    params = json.loads((work / "02_openscad_parameters.json").read_text(encoding="utf-8"))
    export = json.loads((work / "01_kicad_export.json").read_text(encoding="utf-8"))
    freecad_report = json.loads((work / "03_freecad_clearance_report.json").read_text(encoding="utf-8"))
    blender_report = json.loads((work / "04_blender_scene_report.json").read_text(encoding="utf-8"))
    with (work / "connector_keepouts.csv").open(newline="", encoding="utf-8") as handle:
        connectors = {row["ref"].upper(): row for row in csv.DictReader(handle)}
    if (
        requirements.get("task") != TASK
        or params.get("task") != TASK
        or export.get("task") != TASK
        or freecad_report.get("task") != TASK
        or blender_report.get("task") != TASK
    ):
        raise RuntimeError("task identity mismatch in task-05 release inputs")
    if set(connectors) != set(ACCESS_REFS):
        raise RuntimeError("connector contract must contain exactly TP1-TP4 and J1")

    versions = {
        "Blender": version([blender, "--background", "--version"]),
        "FreeCAD": version([freecad, "--version"]),
        "KiCad": version([kicad, "--version"]),
        "OpenSCAD": version([openscad, "--version"]),
    }
    generated_at = datetime.now(timezone.utc).isoformat()
    evidence_path = work / "stage_execution_evidence.json"
    if not evidence_path.is_file():
        raise RuntimeError(f"cannot finalize {TASK} without recorded stage execution evidence")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    expected_stages = ["prepare", "KiCad", "OpenSCAD", "FreeCAD", "Blender"]
    if not isinstance(evidence, list):
        raise RuntimeError(f"{TASK} stage evidence must be a list")
    selected = []
    cursor = 0
    for stage in expected_stages:
        match = None
        for index in range(cursor, len(evidence)):
            candidate = evidence[index]
            if not isinstance(candidate, dict) or candidate.get("stage") != stage or candidate.get("exit_code") != 0:
                continue
            expected_hashes = candidate.get("output_sha256")
            if not isinstance(expected_hashes, dict) or set(expected_hashes) != set(candidate.get("outputs", [])):
                continue
            if all((work / name).is_file() and sha256(work / name) == value for name, value in expected_hashes.items()):
                match = candidate
                cursor = index + 1
                break
        if match is None:
            raise RuntimeError(f"{TASK} evidence lacks a successful productive {stage} stage")
        selected.append(match)
    for entry in selected:
        if Path(str(entry.get("cwd", ""))).resolve() != work:
            raise RuntimeError(f"{TASK} stage did not run directly on the desktop: {entry.get('stage')}")
        for name, expected_hash in entry["output_sha256"].items():
            if sha256(work / name) != expected_hash:
                raise RuntimeError(f"{TASK} stage output changed after execution: {name}")
        if entry.get("software") in versions:
            entry["version"] = versions[entry["software"]]
    prepare_entry = selected[0]
    productive_commands = selected[1:]
    log = {
        "actual_invocations": evidence,
        "commands": selected,
        "generated_at_utc": generated_at,
        "generated_on_host": socket.gethostname(),
        "required_software_sequence": SOFTWARE_SEQUENCE,
        "task": TASK,
        "tool_versions": versions,
    }
    json_dump(work / "toolchain_invocation_log.json", log)

    geometry_tolerance = float(requirements["geometry_tolerance_mm"])
    volume_tolerance = float(requirements["interference_volume_tolerance_mm3"])
    density = float(requirements["enclosure_material_density_g_cm3"])
    mass_tolerance = float(requirements["mass_report_relative_tolerance"])
    enclosure_bbox = [float(value) for value in requirements["expected_enclosure_bbox_mm"]]
    expected_tray_bounds = [
        -enclosure_bbox[0] / 2.0,
        -enclosure_bbox[1] / 2.0,
        0.0,
        enclosure_bbox[0] / 2.0,
        enclosure_bbox[1] / 2.0,
        float(requirements["tray_outer_top_z_mm"]),
    ]
    expected_lid_bounds = [
        -enclosure_bbox[0] / 2.0,
        -enclosure_bbox[1] / 2.0,
        float(requirements["lid_inner_z_mm"]),
        enclosure_bbox[0] / 2.0,
        enclosure_bbox[1] / 2.0,
        enclosure_bbox[2],
    ]
    components = {str(item["ref"]).upper(): item for item in export["components"]}
    accesses = records_by_name(freecad_report.get("access_checks"), "ref")
    access_checks = {
        ref: ref in accesses
        and ref in components
        and (
            top_access_passes(accesses[ref], connectors[ref], components[ref], requirements)
            if ref in TP_REFS
            else side_access_passes(accesses[ref], connectors[ref], requirements)
        )
        for ref in ACCESS_REFS
    }
    report_checks = freecad_report.get("checks")
    tray_volume = number(freecad_report.get("tray_volume_mm3"))
    lid_volume = number(freecad_report.get("lid_volume_mm3"))
    enclosure_volume = number(freecad_report.get("enclosure_volume_mm3"))
    volume_parts_match = (
        tray_volume is not None
        and lid_volume is not None
        and enclosure_volume is not None
        and abs(enclosure_volume - tray_volume - lid_volume) <= max(volume_tolerance, enclosure_volume * 1e-6)
    )
    top_clearances = freecad_report.get("component_top_clearances_mm")
    covered_top_refs = set(ACCESS_REFS) - set(TP_REFS)
    top_clearances_ok = (
        isinstance(top_clearances, dict)
        and set(top_clearances) == set(ACCESS_REFS)
        and all(
            at_least(top_clearances[ref], float(requirements["minimum_top_clearance_mm"]), geometry_tolerance)
            for ref in covered_top_refs
        )
        and all(top_clearances[ref] is None for ref in set(ACCESS_REFS) - covered_top_refs)
    )
    geometry_checks = {
        **{f"access_{ref.lower()}": access_checks[ref] for ref in ACCESS_REFS},
        "enclosure_bbox": close_vector(freecad_report.get("enclosure_bbox_mm"), enclosure_bbox, geometry_tolerance),
        "enclosure_mass": mass_matches(freecad_report.get("enclosure_volume_mm3"), freecad_report.get("enclosure_mass_g"), density, mass_tolerance),
        "enclosure_parts_sum": volume_parts_match,
        "enclosure_solid_count": at_least(freecad_report.get("enclosure_solid_count"), 2.0),
        "freecad_boolean_checks": isinstance(report_checks, dict)
        and bool(report_checks)
        and all(value is True for value in report_checks.values()),
        "freecad_decision": freecad_report.get("decision") == "pass",
        "freecad_required_fields": all(key in freecad_report for key in FREECAD_REQUIRED_FIELDS),
        "interference": at_most(freecad_report.get("unintended_interference_volume_mm3"), volume_tolerance),
        "lid_bounds": close_vector(freecad_report.get("lid_bounds_mm"), expected_lid_bounds, geometry_tolerance),
        "lid_mass": mass_matches(freecad_report.get("lid_volume_mm3"), freecad_report.get("lid_mass_g"), density, mass_tolerance),
        "lid_present": at_least(freecad_report.get("lid_present_material_fraction"), 0.98)
        and at_least(freecad_report.get("lid_solid_count"), 1.0),
        "lid_separation": close_number(freecad_report.get("lid_separation_mm"), float(requirements["lid_separation_mm"]), geometry_tolerance),
        "side_clearances": side_clearances_pass(freecad_report, requirements),
        "standoffs": standoffs_pass(freecad_report.get("standoff_checks"), export["mounting_holes"], requirements),
        "top_clearance": top_clearances_ok
        and at_least(freecad_report.get("minimum_top_clearance_mm"), float(requirements["minimum_top_clearance_mm"]), geometry_tolerance),
        "tray_bounds": close_vector(freecad_report.get("tray_bounds_mm"), expected_tray_bounds, geometry_tolerance),
        "tray_mass": mass_matches(freecad_report.get("tray_volume_mm3"), freecad_report.get("tray_mass_g"), density, mass_tolerance),
        "tray_present": at_least(freecad_report.get("tray_present_material_fraction"), 0.98)
        and at_least(freecad_report.get("tray_solid_count"), 1.0),
    }

    tokens = overlay_tokens(blender_report)
    overlay_geometry = blender_report.get("overlay_geometry")
    overlay_materials = blender_report.get("overlay_materials")
    mesh_qc = blender_report.get("mesh_qc")
    role_counts = blender_report.get("role_counts")
    copied_metrics = blender_report.get("freecad_metrics")
    expected_overlay_features = {
        ref: overlay_feature_present(tokens, ref, "Z", "PLUS") if ref in TP_REFS else overlay_feature_present(tokens, ref, "Y", "PLUS")
        for ref in ACCESS_REFS
    }
    blender_checks = {
        "decision": blender_report.get("decision") == "pass",
        "freecad_metrics_match": isinstance(copied_metrics, dict)
        and set(copied_metrics) == set(BLENDER_COPIED_FREECAD_FIELDS)
        and all(copied_metrics.get(key) == freecad_report.get(key) for key in BLENDER_COPIED_FREECAD_FIELDS),
        "mesh_qc": isinstance(mesh_qc, dict)
        and mesh_qc.get("missing_material_slots") == 0
        and mesh_qc.get("nonmanifold_edges") == 0
        and mesh_qc.get("unclassified_objects") == 0
        and mesh_qc.get("unlabeled_overlays") == 0,
        "native_outputs_nonempty": (work / "04_blender_review.blend").stat().st_size > 10_000
        and (work / "04_blender_review.obj").stat().st_size > 0
        and (work / "04_blender_review.mtl").stat().st_size > 0
        and (work / "04_blender_review.png").stat().st_size > 10_000,
        "native_outputs_recorded": blender_report.get("native_scene") == "04_blender_review.blend"
        and blender_report.get("render") == "04_blender_review.png"
        and blender_report.get("review_obj") == "04_blender_review.obj"
        and blender_report.get("review_mtl") == "04_blender_review.mtl",
        "overlay_features": all(expected_overlay_features.values()),
        "overlay_geometry": isinstance(overlay_geometry, list)
        and len(overlay_geometry) == 5
        and {str(item.get("ref")) for item in overlay_geometry if isinstance(item, dict)} == set(ACCESS_REFS),
        "overlay_materials": isinstance(overlay_materials, dict)
        and len(overlay_materials) == 5
        and len({str(value) for value in overlay_materials.values()}) == 5,
        "real_roles": isinstance(role_counts, dict)
        and role_counts.get("tray") == 1
        and role_counts.get("lid") == 1
        and role_counts.get("pcb") == 1
        and role_counts.get("component") == 5
        and role_counts.get("access_overlay") == 5,
    }

    produced_names = {
        path.name
        for path in work.iterdir()
        if path.is_file()
        and path.suffix not in {".bak", ".blend1", ".kicad_prl", ".lck"}
        and (
            path.name.startswith(("01_", "02_", "03_", "04_"))
            or path.name in {"toolchain_invocation_log.json", "final_release_package.json"}
        )
    }
    produced_names.add("final_release_package.json")
    produced_artifacts = sorted(produced_names)
    artifact_hashes = {name: sha256(work / name) for name in HASHED_ARTIFACTS if (work / name).is_file()}
    artifact_checks = {
        "all_required_artifacts_present": all((work / name).is_file() for name in REQUIRED_ARTIFACTS[:-1]),
        "required_artifact_hashes": len(artifact_hashes) == 17 and set(artifact_hashes) == set(HASHED_ARTIFACTS),
        "required_subset_of_produced_artifacts": set(REQUIRED_ARTIFACTS).issubset(produced_names),
    }
    toolchain_checks = {
        "ordered_productive_sequence": [entry["software"] for entry in productive_commands] == SOFTWARE_SEQUENCE,
        "productive_entries_have_versions": all(isinstance(entry.get("version"), str) and bool(entry["version"].strip()) for entry in productive_commands),
        "tool_versions_present": set(versions) == set(SOFTWARE_SEQUENCE) and all(bool(value.strip()) for value in versions.values()),
    }
    checks = {
        "geometry_report_all_pass": all(geometry_checks.values()),
        **{f"geometry_{name}": passed for name, passed in geometry_checks.items()},
        **{f"blender_{name}": passed for name, passed in blender_checks.items()},
        **artifact_checks,
        **toolchain_checks,
    }
    release_pass = all(geometry_checks.values()) and all(blender_checks.values()) and all(artifact_checks.values()) and all(toolchain_checks.values())
    package = {
        "artifact_policy": {
            "extras_allowed": True,
            "membership": "required_artifacts must be a subset of produced_artifacts",
        },
        "artifact_sha256": artifact_hashes,
        "checks": checks,
        "critical_requirement": requirements["critical_requirement"],
        "domain": requirements["domain"],
        "extra_artifacts": sorted(produced_names - set(REQUIRED_ARTIFACTS)),
        "generated_at_utc": generated_at,
        "geometry_checks": geometry_checks,
        "hash_policy": "All 17 required non-self artifacts are SHA-256 hashed.",
        "key_metrics": {
            "access_checks": freecad_report.get("access_checks"),
            "board_bbox_mm": params.get("board_bbox_mm"),
            "component_top_clearances_mm": freecad_report.get("component_top_clearances_mm"),
            "enclosure_bbox_mm": freecad_report.get("enclosure_bbox_mm"),
            "enclosure_mass_g": freecad_report.get("enclosure_mass_g"),
            "enclosure_volume_mm3": freecad_report.get("enclosure_volume_mm3"),
            "lid_mass_g": freecad_report.get("lid_mass_g"),
            "lid_separation_mm": freecad_report.get("lid_separation_mm"),
            "lid_volume_mm3": freecad_report.get("lid_volume_mm3"),
            "minimum_side_clearance_mm": freecad_report.get("minimum_side_clearance_mm"),
            "minimum_top_clearance_mm": freecad_report.get("minimum_top_clearance_mm"),
            "side_clearances_mm": freecad_report.get("side_clearances_mm"),
            "standoff_checks": freecad_report.get("standoff_checks"),
            "tray_mass_g": freecad_report.get("tray_mass_g"),
            "tray_volume_mm3": freecad_report.get("tray_volume_mm3"),
            "unintended_interference_volume_mm3": freecad_report.get("unintended_interference_volume_mm3"),
        },
        "produced_artifacts": produced_artifacts,
        "release_decision": "pass" if release_pass else "fail",
        "required_artifacts": REQUIRED_ARTIFACTS,
        "software_sequence": SOFTWARE_SEQUENCE,
        "stage_outputs": {
            "Blender": productive_commands[3]["outputs"],
            "FreeCAD": productive_commands[2]["outputs"],
            "KiCad": [*prepare_entry["outputs"][:4], "01_kicad_board.step"],
            "OpenSCAD": [
                "02_openscad_enclosure.scad",
                "02_openscad_enclosure.stl",
                "02_openscad_parameters.json",
            ],
        },
        "task": TASK,
        "title": requirements["title"],
        "tool_versions": versions,
    }
    json_dump(work / "final_release_package.json", package)
    if package["release_decision"] != "pass":
        failed = sorted(name for name, passed in checks.items() if not passed)
        raise RuntimeError(f"{TASK} final release checks failed: " + ", ".join(failed))


if __name__ == "__main__":
    main()
