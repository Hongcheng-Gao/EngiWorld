#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import shlex
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "task-04"
SOFTWARE_SEQUENCE = ["KiCad", "OpenSCAD", "FreeCAD", "Blender"]
REQUIRED_ARTIFACTS = [
    "01_kicad_board.kicad_pcb",
    "01_kicad_board.step",
    "01_kicad_export.json",
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
FREECAD_REQUIRED_FIELDS = [
    "access_checks",
    "decision",
    "enclosure_bbox_mm",
    "enclosure_mass_g",
    "enclosure_volume_mm3",
    "lid_mass_g",
    "lid_separation_mm",
    "lid_volume_mm3",
    "minimum_side_clearance_mm",
    "minimum_top_clearance_mm",
    "projected_keepout_checks",
    "rib_checks",
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
    "rib_checks",
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
    lines = [
        line.strip()
        for line in output.splitlines()
        if line.strip() and not line.strip().endswith("%")
    ]
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


def access_passes(
    entry: dict[str, Any],
    connector: dict[str, str],
    requirements: dict[str, Any],
) -> bool:
    geometry_tolerance = float(requirements["geometry_tolerance_mm"])
    volume_tolerance = float(requirements["interference_volume_tolerance_mm3"])
    center_tolerance = float(requirements["access_center_tolerance_mm"])
    minimum_guard = float(requirements["minimum_access_guard_mm"])
    if entry.get("direction", entry.get("wall_direction")) != connector["direction"]:
        return False
    if entry.get("through") is not True:
        return False
    if entry.get("minimum_guard_material_present") is not True:
        return False
    if not at_most(entry.get("residual_material_volume_mm3"), volume_tolerance):
        return False
    if not at_least(entry.get("minimum_guard_mm"), minimum_guard, geometry_tolerance):
        return False
    if not at_most(entry.get("center_error_mm"), center_tolerance, geometry_tolerance):
        return False
    if not at_most(entry.get("width_error_mm"), geometry_tolerance):
        return False
    if not at_most(entry.get("height_error_mm"), geometry_tolerance):
        return False
    for key in ("finished_width_mm", "finished_height_mm"):
        if not close_number(entry.get(key), float(connector[key]), geometry_tolerance):
            return False
    return True


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
    expected_z_min = -float(requirements["standoff_bore_overcut_mm"])
    expected_z_max = float(requirements["board_bottom_z_mm"]) - expected_z_min
    for ref, entry in checks.items():
        hole = expected[ref]
        if entry.get("continuous_bore") is not True or entry.get("standoff_present") is not True:
            return False
        if not at_least(entry.get("present_material_fraction"), 0.95):
            return False
        if not at_most(entry.get("residual_bore_material_volume_mm3"), volume_tolerance):
            return False
        if not at_most(entry.get("axis_error_mm"), axis_tolerance):
            return False
        if not close_number(entry.get("x_mm"), float(hole["x_mm"]), axis_tolerance):
            return False
        if not close_number(entry.get("y_mm"), float(hole["y_mm"]), axis_tolerance):
            return False
        if not close_number(
            entry.get("bore_diameter_mm"),
            float(requirements["standoff_bore_diameter_mm"]),
            geometry_tolerance,
        ):
            return False
        if not close_number(
            entry.get("outer_diameter_mm"),
            float(requirements["standoff_outer_diameter_mm"]),
            geometry_tolerance,
        ):
            return False
        if not close_number(entry.get("bore_z_min_mm"), expected_z_min, geometry_tolerance):
            return False
        if not close_number(entry.get("bore_z_max_mm"), expected_z_max, geometry_tolerance):
            return False
    return True


def ribs_pass(raw: object, projected_raw: object, requirements: dict[str, Any]) -> bool:
    ribs = records_by_name(raw, "id")
    required_ribs = {str(item["id"]).upper(): item for item in requirements["required_ribs"]}
    q_refs = {str(ref).upper() for ref in requirements["rib_exclusion"]["keepout_refs"]}
    if set(ribs) != set(required_ribs) or len(ribs) != 2:
        return False
    geometry_tolerance = float(requirements["geometry_tolerance_mm"])
    volume_tolerance = float(requirements["interference_volume_tolerance_mm3"])
    minimum_clearance = float(requirements["minimum_rib_keepout_clearance_mm"])
    for rib_id, entry in ribs.items():
        expected_bounds = [float(value) for value in required_ribs[rib_id]["bounds_mm"]]
        expected_volume = (
            (expected_bounds[3] - expected_bounds[0])
            * (expected_bounds[4] - expected_bounds[1])
            * (expected_bounds[5] - expected_bounds[2])
        )
        if entry.get("present") is not True or not at_least(entry.get("present_material_fraction"), 0.98):
            return False
        if not close_vector(entry.get("bounds_mm"), expected_bounds, geometry_tolerance):
            return False
        if not close_number(entry.get("expected_volume_mm3"), expected_volume, volume_tolerance):
            return False
        if not close_number(
            entry.get("measured_volume_mm3"), expected_volume, max(volume_tolerance, expected_volume * 0.01)
        ):
            return False
        q_checks = records_by_name(entry.get("q_keepout_checks"), "ref")
        if set(q_checks) != q_refs:
            return False
        for check in q_checks.values():
            if check.get("passes") is not True:
                return False
            if not at_most(check.get("intersection_mm3"), volume_tolerance):
                return False
            if not at_least(check.get("separation_mm"), minimum_clearance, geometry_tolerance):
                return False

    projected = records_by_name(projected_raw, "ref")
    if set(projected) != q_refs:
        return False
    for check in projected.values():
        if check.get("clear") is not True:
            return False
        if not at_most(check.get("all_tray_structural_intersection_mm3"), volume_tolerance):
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
    for key in ("visible_features", "overlays"):
        raw = report.get(key, [])
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    result.extend(normalize(item.get(name, "")) for name in ("name", "ref", "role", "direction"))
                else:
                    result.append(normalize(item))
        elif isinstance(raw, dict):
            result.extend(normalize(name) for name in raw)
    materials = report.get("overlay_materials")
    if isinstance(materials, dict):
        result.extend(normalize(name) for name in materials)
    return [token for token in result if token]


def overlay_feature_present(tokens: list[str], *pieces: str) -> bool:
    normalized_pieces = [normalize(piece) for piece in pieces]
    return any(all(piece in token for piece in normalized_pieces) for token in tokens)


def role_count(raw: object, *names: str) -> int:
    if not isinstance(raw, dict):
        return 0
    normalized = {normalize(key): number(value) for key, value in raw.items()}
    return max((int(normalized.get(normalize(name)) or 0) for name in names), default=0)


def main() -> None:
    work = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    internal = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/engiworld-task04-internal")
    kicad = os.environ.get(
        "ENGIWORLD_KICAD_CLI",
        "/home/user/Applications/kicad-10.0.2/kicad-10.0.2-x86_64.AppImage",
    )
    blender = os.environ.get(
        "ENGIWORLD_BLENDER",
        "/home/user/Applications/blender-4.2.3-linux-x64/blender",
    )
    freecad = os.environ.get("ENGIWORLD_FREECAD", "freecadcmd")
    openscad = os.environ.get("ENGIWORLD_OPENSCAD", "openscad")

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
    if requirements.get("task") != TASK or freecad_report.get("task") != TASK or blender_report.get("task") != TASK:
        raise RuntimeError("task identity mismatch in task-04 release inputs")

    versions = {
        "Blender": version([blender, "--background", "--version"]),
        "FreeCAD": version([freecad, "--version"]),
        "KiCad": version([kicad, "kicad-cli", "--version"]),
        "OpenSCAD": version([openscad, "--version"]),
    }
    generated_at = datetime.now(timezone.utc).isoformat()

    prepare_entry = {
        "command": f"python3 {shlex.quote(str(internal / 'task04_prepare.py'))} {shlex.quote(str(work))}",
        "inputs": [
            "board_input.kicad_pcb",
            "mechanical_requirements.json",
            "connector_keepouts.csv",
            "enclosure_seed.scad",
            "handoff_notes.md",
        ],
        "outputs": [
            "01_kicad_board.kicad_pcb",
            "01_kicad_export.json",
            "01_kicad_mechanical_map.csv",
            "01_kicad_parameters.scad",
            "02_openscad_enclosure.scad",
            "02_openscad_parameters.json",
        ],
        "software": "Python handoff generator",
    }
    productive_commands = [
        {
            "command": (
                f"cd {shlex.quote(str(work))} && {shlex.quote(kicad)} kicad-cli pcb export step "
                "--force --board-only --output 01_kicad_board.step 01_kicad_board.kicad_pcb"
            ),
            "inputs": ["01_kicad_board.kicad_pcb"],
            "outputs": ["01_kicad_board.step"],
            "software": "KiCad",
            "version": versions["KiCad"],
        },
        {
            "command": (
                f"cd {shlex.quote(str(work))} && {shlex.quote(openscad)} "
                "-o 02_openscad_enclosure.stl 02_openscad_enclosure.scad"
            ),
            "inputs": ["01_kicad_parameters.scad", "02_openscad_enclosure.scad"],
            "outputs": ["02_openscad_enclosure.stl"],
            "software": "OpenSCAD",
            "version": versions["OpenSCAD"],
        },
        {
            "command": (
                f"ENGIWORLD_WORKDIR={shlex.quote(str(work))} {shlex.quote(freecad)} "
                f"{shlex.quote(str(internal / 'task04_freecad_stage.py'))}"
            ),
            "inputs": [
                "01_kicad_board.step",
                "01_kicad_export.json",
                "01_kicad_mechanical_map.csv",
                "02_openscad_enclosure.stl",
                "02_openscad_parameters.json",
            ],
            "outputs": [
                "03_freecad_assembly.step",
                "03_freecad_assembly.obj",
                "03_freecad_clearance_report.json",
            ],
            "software": "FreeCAD",
            "version": versions["FreeCAD"],
        },
        {
            "command": (
                f"{shlex.quote(blender)} --background --factory-startup --python "
                f"{shlex.quote(str(internal / 'task04_blender_stage.py'))} -- {shlex.quote(str(work))}"
            ),
            "inputs": ["03_freecad_assembly.obj", "03_freecad_clearance_report.json"],
            "outputs": [
                "04_blender_review.blend",
                "04_blender_review.obj",
                "04_blender_review.mtl",
                "04_blender_review.png",
                "04_blender_scene_report.json",
            ],
            "software": "Blender",
            "version": versions["Blender"],
        },
    ]
    log = {
        "actual_invocations": [prepare_entry, *productive_commands],
        "commands": productive_commands,
        "generated_at_utc": generated_at,
        "generated_on_host": socket.gethostname(),
        "preparation": prepare_entry,
        "productive_software_sequence": [entry["software"] for entry in productive_commands],
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
    access_by_ref = records_by_name(freecad_report.get("access_checks"), "ref")
    access_checks = {
        ref: ref in access_by_ref and ref in connectors
        and access_passes(access_by_ref[ref], connectors[ref], requirements)
        for ref in ("J1", "J2")
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

    geometry_checks = {
        "access_j1": access_checks["J1"],
        "access_j2": access_checks["J2"],
        "enclosure_bbox": close_vector(
            freecad_report.get("enclosure_bbox_mm"), enclosure_bbox, geometry_tolerance
        ),
        "enclosure_mass": mass_matches(
            freecad_report.get("enclosure_volume_mm3"),
            freecad_report.get("enclosure_mass_g"),
            density,
            mass_tolerance,
        ),
        "enclosure_parts_sum": volume_parts_match,
        "enclosure_solid_count": at_least(freecad_report.get("enclosure_solid_count"), 2.0),
        "freecad_boolean_checks": isinstance(report_checks, dict)
        and bool(report_checks)
        and all(value is True for value in report_checks.values()),
        "freecad_decision": freecad_report.get("decision") == "pass",
        "freecad_required_fields": all(key in freecad_report for key in FREECAD_REQUIRED_FIELDS),
        "interference": at_most(
            freecad_report.get("unintended_interference_volume_mm3"), volume_tolerance
        ),
        "lid_bounds": close_vector(
            freecad_report.get("lid_bounds_mm"), expected_lid_bounds, geometry_tolerance
        ),
        "lid_mass": mass_matches(
            freecad_report.get("lid_volume_mm3"),
            freecad_report.get("lid_mass_g"),
            density,
            mass_tolerance,
        ),
        "lid_present": at_least(freecad_report.get("lid_present_material_fraction"), 0.98)
        and at_least(freecad_report.get("lid_solid_count"), 1.0),
        "lid_separation": close_number(
            freecad_report.get("lid_separation_mm"),
            float(requirements["lid_separation_mm"]),
            geometry_tolerance,
        ),
        "ribs": ribs_pass(
            freecad_report.get("rib_checks"),
            freecad_report.get("projected_keepout_checks"),
            requirements,
        ),
        "side_clearances": side_clearances_pass(freecad_report, requirements),
        "standoffs": standoffs_pass(
            freecad_report.get("standoff_checks"), export["mounting_holes"], requirements
        ),
        "top_clearance": at_least(
            freecad_report.get("minimum_top_clearance_mm"),
            float(requirements["minimum_top_clearance_mm"]),
            geometry_tolerance,
        ),
        "tray_bounds": close_vector(
            freecad_report.get("tray_bounds_mm"), expected_tray_bounds, geometry_tolerance
        ),
        "tray_mass": mass_matches(
            freecad_report.get("tray_volume_mm3"),
            freecad_report.get("tray_mass_g"),
            density,
            mass_tolerance,
        ),
        "tray_present": at_least(freecad_report.get("tray_present_material_fraction"), 0.98)
        and at_least(freecad_report.get("tray_solid_count"), 1.0),
    }

    tokens = overlay_tokens(blender_report)
    overlay_materials = blender_report.get("overlay_materials")
    mesh_qc = blender_report.get("mesh_qc")
    copied_metrics = blender_report.get("freecad_metrics")
    expected_overlay_features = {
        "q1": overlay_feature_present(tokens, "Q1"),
        "q2": overlay_feature_present(tokens, "Q2"),
        "q3": overlay_feature_present(tokens, "Q3"),
        "rib_neg_y": overlay_feature_present(tokens, "RIB", "NEG", "Y"),
        "rib_pos_y": overlay_feature_present(tokens, "RIB", "POS", "Y"),
        "j1_x_plus": overlay_feature_present(tokens, "J1", "X", "PLUS"),
        "j2_x_minus": overlay_feature_present(tokens, "J2", "X", "MINUS"),
    }
    blender_checks = {
        "decision": blender_report.get("decision") == "pass",
        "freecad_metrics_match": isinstance(copied_metrics, dict)
        and set(copied_metrics) == set(BLENDER_COPIED_FREECAD_FIELDS)
        and all(
            copied_metrics.get(key) == freecad_report.get(key)
            for key in BLENDER_COPIED_FREECAD_FIELDS
        ),
        "mesh_qc": isinstance(mesh_qc, dict)
        and mesh_qc.get("missing_material_slots") == 0
        and mesh_qc.get("nonmanifold_edges") == 0
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
        "overlay_materials": isinstance(overlay_materials, dict)
        and len(overlay_materials) >= 7
        and len({str(value) for value in overlay_materials.values()}) >= 3,
        "real_roles": role_count(blender_report.get("role_counts"), "tray", "enclosure", "package") >= 1
        and role_count(blender_report.get("role_counts"), "lid") >= 1
        and role_count(blender_report.get("role_counts"), "pcb", "board") >= 1
        and role_count(blender_report.get("role_counts"), "component", "component_envelope") >= 1
        and role_count(blender_report.get("role_counts"), "rib") >= 2,
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
    required_hashes = {
        name: sha256(work / name)
        for name in REQUIRED_ARTIFACTS
        if name != "final_release_package.json" and (work / name).is_file()
    }
    artifact_checks = {
        "all_required_artifacts_present": all(
            (work / name).is_file() for name in REQUIRED_ARTIFACTS[:-1]
        ),
        "required_nonself_hashes": len(required_hashes) == 17
        and set(required_hashes) == set(REQUIRED_ARTIFACTS[:-1]),
        "required_subset_of_produced_artifacts": set(REQUIRED_ARTIFACTS).issubset(produced_names),
    }
    toolchain_checks = {
        "ordered_productive_sequence": [entry["software"] for entry in productive_commands]
        == SOFTWARE_SEQUENCE,
        "productive_entries_have_versions": all(
            isinstance(entry.get("version"), str) and bool(entry["version"].strip())
            for entry in productive_commands
        ),
        "tool_versions_present": set(versions) == set(SOFTWARE_SEQUENCE)
        and all(bool(value.strip()) for value in versions.values()),
    }
    checks = {
        "geometry_report_all_pass": all(geometry_checks.values()),
        **{f"geometry_{name}": passed for name, passed in geometry_checks.items()},
        **{f"blender_{name}": passed for name, passed in blender_checks.items()},
        **artifact_checks,
        **toolchain_checks,
    }
    release_pass = all(geometry_checks.values()) and all(checks.values())
    package = {
        "artifact_policy": {
            "extras_allowed": True,
            "membership": "required_artifacts must be a subset of produced_artifacts",
        },
        "artifact_sha256": required_hashes,
        "checks": checks,
        "critical_requirement": requirements["critical_requirement"],
        "domain": requirements["domain"],
        "extra_artifacts": sorted(produced_names - set(REQUIRED_ARTIFACTS)),
        "generated_at_utc": generated_at,
        "geometry_checks": geometry_checks,
        "hash_policy": "Exactly the 17 required non-self artifacts are SHA-256 hashed.",
        "key_metrics": {
            "access_checks": freecad_report.get("access_checks"),
            "board_bbox_mm": params.get("board_bbox_mm"),
            "enclosure_bbox_mm": freecad_report.get("enclosure_bbox_mm"),
            "enclosure_mass_g": freecad_report.get("enclosure_mass_g"),
            "enclosure_volume_mm3": freecad_report.get("enclosure_volume_mm3"),
            "lid_mass_g": freecad_report.get("lid_mass_g"),
            "lid_separation_mm": freecad_report.get("lid_separation_mm"),
            "lid_volume_mm3": freecad_report.get("lid_volume_mm3"),
            "minimum_side_clearance_mm": freecad_report.get("minimum_side_clearance_mm"),
            "minimum_top_clearance_mm": freecad_report.get("minimum_top_clearance_mm"),
            "rib_checks": freecad_report.get("rib_checks"),
            "standoff_checks": freecad_report.get("standoff_checks"),
            "tray_mass_g": freecad_report.get("tray_mass_g"),
            "tray_volume_mm3": freecad_report.get("tray_volume_mm3"),
            "unintended_interference_volume_mm3": freecad_report.get(
                "unintended_interference_volume_mm3"
            ),
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
