#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import os
import shlex
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "task-03"
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
    "enclosure_volume_mm3",
    "enclosure_mass_g",
    "shield_volume_mm3",
    "shield_mass_g",
    "minimum_side_clearance_mm",
    "u1_keepout_contained",
    "j1_protected_volume_intersection_mm3",
    "j1_protected_volume_separation_mm",
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
        raise RuntimeError(f"version command failed ({completed.returncode}): {shlex.join(command)}\n{output}")
    lines = [line.strip() for line in output.splitlines() if line.strip() and not line.strip().endswith("%")]
    if not lines:
        raise RuntimeError(f"version command returned no usable version: {shlex.join(command)}")
    return lines[0]


def close_number(actual: object, expected: float, tolerance: float) -> bool:
    try:
        return abs(float(actual) - expected) <= tolerance
    except (TypeError, ValueError):
        return False


def close_vector(actual: object, expected: list[float], tolerance: float) -> bool:
    return (
        isinstance(actual, list)
        and len(actual) == len(expected)
        and all(close_number(value, target, tolerance) for value, target in zip(actual, expected))
    )


def positive_number(value: object) -> bool:
    try:
        return float(value) > 0.0
    except (TypeError, ValueError):
        return False


def mass_matches(volume_mm3: object, mass_g: object, density_g_cm3: float, relative_tolerance: float) -> bool:
    try:
        expected = float(volume_mm3) * density_g_cm3 / 1000.0
        actual = float(mass_g)
    except (TypeError, ValueError):
        return False
    tolerance = max(0.001, abs(expected) * relative_tolerance)
    return expected > 0.0 and abs(actual - expected) <= tolerance


def access_entries(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    raw = report.get("access_checks")
    if isinstance(raw, dict):
        for ref, item in raw.items():
            if isinstance(item, dict):
                result[str(ref).upper()] = item
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and item.get("ref"):
                result[str(item["ref"]).upper()] = item
    return result


def access_passes(
    entry: dict[str, Any],
    connector: dict[str, str],
    requirements: dict[str, Any],
) -> bool:
    expected_direction = connector["direction"]
    actual_direction = entry.get("direction", entry.get("wall_direction", entry.get("access_direction")))
    if actual_direction != expected_direction:
        return False

    verdict_present = False
    if "decision" in entry:
        verdict_present = True
        if entry["decision"] != "pass":
            return False
    if "pass" in entry:
        verdict_present = True
        if entry["pass"] is not True:
            return False

    continuity_fields = (
        "continuous",
        "through",
        "through_wall",
        "through_lid",
        "cavity_to_exterior",
        "access_continuous",
        "continuity_pass",
    )
    present_continuity = [entry[key] for key in continuity_fields if key in entry]
    if not present_continuity or not any(value is True for value in present_continuity):
        return False
    if any(value is not True for value in present_continuity):
        return False

    boolean_guard_fields = (
        "guard_material_present",
        "guard_wall_material_present",
        "guard_pass",
        "minimum_guard_material_present",
    )
    if any(entry[key] is not True for key in boolean_guard_fields if key in entry):
        return False
    guard_value = entry.get("minimum_guard_mm", entry.get("guard_mm"))
    if guard_value is not None:
        try:
            if float(guard_value) + 1e-9 < float(requirements["minimum_access_guard_mm"]):
                return False
        except (TypeError, ValueError):
            return False
    center_error = entry.get("center_error_mm")
    if center_error is not None:
        try:
            if abs(float(center_error)) > float(requirements["access_center_tolerance_mm"]):
                return False
        except (TypeError, ValueError):
            return False

    geometry_tolerance = float(requirements["geometry_tolerance_mm"])
    for key in ("finished_width_mm", "finished_height_mm", "finished_diameter_mm"):
        expected = float(connector[key])
        if expected > 0.0 and key in entry and not close_number(entry[key], expected, geometry_tolerance):
            return False
    return verdict_present or bool(present_continuity)


def role_count(role_counts: object, *names: str) -> int:
    if not isinstance(role_counts, dict):
        return 0
    values = []
    for name in names:
        try:
            values.append(int(role_counts.get(name, 0)))
        except (TypeError, ValueError):
            values.append(0)
    return max(values, default=0)


def main() -> None:
    work = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    internal = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/engiworld-task03-internal")
    kicad = os.environ.get("ENGIWORLD_KICAD") or shutil.which("kicad-cli") or "/usr/bin/kicad-cli"
    blender = os.environ.get("ENGIWORLD_BLENDER") or shutil.which("blender") or "/snap/bin/blender"
    freecad = os.environ.get("ENGIWORLD_FREECAD") or shutil.which("freecadcmd") or "freecadcmd"
    openscad = os.environ.get("ENGIWORLD_OPENSCAD") or shutil.which("openscad") or "/usr/bin/openscad"

    missing = [name for name in REQUIRED_ARTIFACTS[:-2] if not (work / name).is_file()]
    if missing:
        raise RuntimeError(f"cannot finalize {TASK}; missing artifacts: " + ", ".join(missing))

    requirements = json.loads((work / "mechanical_requirements.json").read_text(encoding="utf-8"))
    freecad_report = json.loads((work / "03_freecad_clearance_report.json").read_text(encoding="utf-8"))
    blender_report = json.loads((work / "04_blender_scene_report.json").read_text(encoding="utf-8"))
    params = json.loads((work / "02_openscad_parameters.json").read_text(encoding="utf-8"))
    with (work / "connector_keepouts.csv").open(newline="", encoding="utf-8") as handle:
        connectors = {row["ref"]: row for row in csv.DictReader(handle)}

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
        expected_hashes = entry.get("output_sha256")
        if not isinstance(expected_hashes, dict) or set(expected_hashes) != set(entry.get("outputs", [])):
            raise RuntimeError(f"{TASK} stage lacks output hashes: {entry.get('stage')}")
        for name, expected_hash in expected_hashes.items():
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
    interference_tolerance = float(requirements["interference_volume_tolerance_mm3"])
    mass_tolerance = float(requirements["mass_report_relative_tolerance"])
    access_by_ref = access_entries(freecad_report)
    required_accesses = {"J1", "J2", "TP1"}
    access_checks = {
        ref: ref in access_by_ref and access_passes(access_by_ref[ref], connectors[ref], requirements)
        for ref in sorted(required_accesses)
    }

    report_checks = freecad_report.get("checks")
    copied_metrics = blender_report.get("freecad_metrics")
    overlay_materials = blender_report.get("overlay_materials")
    mesh_qc = blender_report.get("mesh_qc")
    checks = {
        "all_required_artifacts_present": all((work / name).is_file() for name in REQUIRED_ARTIFACTS[:-1]),
        "blender_decision_pass": blender_report.get("decision") == "pass",
        "blender_features_present": {
            "protected_volume",
            "U1_inclusion",
            "J1_exclusion",
            "J1_X_PLUS_access",
            "J2_X_MINUS_access",
            "TP1_Z_PLUS_lid_bore",
        }.issubset(set(blender_report.get("visible_features", []))),
        "blender_native_outputs_recorded": all(
            [
                blender_report.get("native_scene") == "04_blender_review.blend",
                blender_report.get("render") == "04_blender_review.png",
                blender_report.get("review_obj") == "04_blender_review.obj",
                blender_report.get("review_mtl") == "04_blender_review.mtl",
            ]
        ),
        "blender_native_outputs_nonempty": all(
            [
                (work / "04_blender_review.blend").stat().st_size > 10_000,
                (work / "04_blender_review.obj").stat().st_size > 0,
                (work / "04_blender_review.mtl").stat().st_size > 0,
                (work / "04_blender_review.png").stat().st_size > 10_000,
            ]
        ),
        "blender_overlay_qc_pass": isinstance(mesh_qc, dict)
        and mesh_qc.get("missing_material_slots") == 0
        and mesh_qc.get("unlabeled_overlays") == 0,
        "blender_metrics_match_freecad": isinstance(copied_metrics, dict)
        and all(copied_metrics.get(key) == freecad_report.get(key) for key in FREECAD_REQUIRED_FIELDS),
        "blender_overlays_materially_distinct": isinstance(overlay_materials, dict)
        and len(overlay_materials) == 6
        and len(set(overlay_materials.values())) == 6,
        "blender_real_roles_present": all(
            [
                role_count(blender_report.get("role_counts"), "package", "enclosure") >= 1,
                role_count(blender_report.get("role_counts"), "shield") >= 1,
                role_count(blender_report.get("role_counts"), "pcb") >= 1,
                role_count(blender_report.get("role_counts"), "component", "component_envelope") >= 1,
            ]
        ),
        "enclosure_bbox_pass": close_vector(
            freecad_report.get("enclosure_bbox_mm"),
            [float(value) for value in requirements["expected_enclosure_bbox_mm"]],
            geometry_tolerance,
        ),
        "enclosure_mass_pass": positive_number(freecad_report.get("enclosure_volume_mm3"))
        and mass_matches(
            freecad_report.get("enclosure_volume_mm3"),
            freecad_report.get("enclosure_mass_g"),
            float(requirements["enclosure_material_density_g_cm3"]),
            mass_tolerance,
        ),
        "freecad_boolean_checks_pass": isinstance(report_checks, dict)
        and bool(report_checks)
        and all(value is True for value in report_checks.values()),
        "freecad_decision_pass": freecad_report.get("decision") == "pass",
        "freecad_required_metrics_present": all(key in freecad_report for key in FREECAD_REQUIRED_FIELDS),
        "j1_access_pass": access_checks["J1"],
        "j1_exclusion_pass": close_number(
            freecad_report.get("j1_protected_volume_intersection_mm3"),
            0.0,
            interference_tolerance,
        )
        and positive_number(freecad_report.get("j1_protected_volume_separation_mm")),
        "j2_access_pass": access_checks["J2"],
        "shield_mass_pass": positive_number(freecad_report.get("shield_volume_mm3"))
        and mass_matches(
            freecad_report.get("shield_volume_mm3"),
            freecad_report.get("shield_mass_g"),
            float(requirements["shield"]["material_density_g_cm3"]),
            mass_tolerance,
        ),
        "side_clearance_pass": close_number(
            freecad_report.get("minimum_side_clearance_mm"),
            float(requirements["minimum_side_clearance_mm"]),
            geometry_tolerance,
        )
        or (
            positive_number(freecad_report.get("minimum_side_clearance_mm"))
            and float(freecad_report["minimum_side_clearance_mm"])
            >= float(requirements["minimum_side_clearance_mm"])
        ),
        "tp1_access_pass": access_checks["TP1"],
        "u1_containment_pass": freecad_report.get("u1_keepout_contained") is True,
        "unintended_interference_pass": close_number(
            freecad_report.get("unintended_interference_volume_mm3"),
            0.0,
            interference_tolerance,
        ),
    }

    produced_names = {
        path.name
        for path in work.iterdir()
        if path.is_file()
        and path.suffix not in {".kicad_prl", ".blend1", ".lck", ".bak"}
        and (
            path.name.startswith(("01_", "02_", "03_", "04_"))
            or path.name in {"toolchain_invocation_log.json", "final_release_package.json"}
        )
    }
    produced_names.add("final_release_package.json")
    produced_artifacts = sorted(produced_names)
    hashes = {
        name: sha256(work / name)
        for name in produced_artifacts
        if name != "final_release_package.json" and (work / name).is_file()
    }
    membership_pass = set(REQUIRED_ARTIFACTS).issubset(set(produced_artifacts))
    checks["required_subset_of_produced_artifacts"] = membership_pass

    package = {
        "artifact_policy": {
            "extras_allowed": True,
            "membership": "required_artifacts must be a subset of produced_artifacts",
        },
        "artifact_sha256": hashes,
        "checks": checks,
        "critical_requirement": requirements["critical_requirement"],
        "domain": requirements["domain"],
        "generated_at_utc": generated_at,
        "hash_policy": "All generated required artifacts except this self-referential package are SHA-256 hashed.",
        "key_metrics": {
            "access_checks": freecad_report.get("access_checks"),
            "board_bbox_mm": params.get("board_bbox_mm"),
            "enclosure_bbox_mm": freecad_report.get("enclosure_bbox_mm"),
            "enclosure_mass_g": freecad_report.get("enclosure_mass_g"),
            "enclosure_volume_mm3": freecad_report.get("enclosure_volume_mm3"),
            "j1_protected_volume_intersection_mm3": freecad_report.get(
                "j1_protected_volume_intersection_mm3"
            ),
            "j1_protected_volume_separation_mm": freecad_report.get("j1_protected_volume_separation_mm"),
            "minimum_side_clearance_mm": freecad_report.get("minimum_side_clearance_mm"),
            "shield_mass_g": freecad_report.get("shield_mass_g"),
            "shield_volume_mm3": freecad_report.get("shield_volume_mm3"),
            "u1_keepout_contained": freecad_report.get("u1_keepout_contained"),
            "unintended_interference_volume_mm3": freecad_report.get(
                "unintended_interference_volume_mm3"
            ),
        },
        "produced_artifacts": produced_artifacts,
        "extra_artifacts": sorted(set(produced_artifacts) - set(REQUIRED_ARTIFACTS)),
        "release_decision": "pass" if all(checks.values()) else "fail",
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
