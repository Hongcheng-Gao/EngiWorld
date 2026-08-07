#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_ARTIFACTS = [
    "01_kicad_board.kicad_pcb",
    "01_kicad_board.step",
    "01_kicad_export.json",
    "01_kicad_mechanical_map.csv",
    "02_openscad_enclosure.scad",
    "02_openscad_enclosure.stl",
    "02_openscad_parameters.json",
    "03_freecad_assembly.step",
    "03_freecad_assembly_for_blender.obj",
    "03_freecad_clearance_report.json",
    "04_blender_review.blend",
    "04_blender_review.obj",
    "04_blender_review.mtl",
    "04_blender_review.png",
    "04_blender_scene_report.json",
    "toolchain_invocation_log.json",
    "final_release_package.json",
]


def json_dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def version(command: list[str]) -> str:
    completed = subprocess.run(command, text=True, capture_output=True, timeout=60, check=False)
    text = (completed.stdout + "\n" + completed.stderr).strip()
    if completed.returncode != 0:
        raise RuntimeError(f"version command failed ({completed.returncode}): {' '.join(command)}\n{text}")
    return next((line.strip() for line in text.splitlines() if line.strip() and not line.strip().endswith("%")), text)


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


def main() -> None:
    work = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    internal = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/engiworld-task01-internal")
    kicad = "/home/user/Applications/kicad-10.0.2/kicad-10.0.2-x86_64.AppImage"
    blender = "/home/user/Applications/blender-4.2.3-linux-x64/blender"
    freecad_report = json.loads((work / "03_freecad_clearance_report.json").read_text(encoding="utf-8"))
    blender_report = json.loads((work / "04_blender_scene_report.json").read_text(encoding="utf-8"))
    openscad_params = json.loads((work / "02_openscad_parameters.json").read_text(encoding="utf-8"))
    requirements = json.loads((work / "mechanical_requirements.json").read_text(encoding="utf-8"))
    kicad_export = json.loads((work / "01_kicad_export.json").read_text(encoding="utf-8"))
    with (work / "connector_keepouts.csv").open(newline="", encoding="utf-8") as handle:
        connectors = {row["ref"]: row for row in csv.DictReader(handle)}

    missing = [name for name in REQUIRED_ARTIFACTS[:-2] if not (work / name).is_file()]
    if missing:
        raise RuntimeError("cannot finalize task-01; missing artifacts: " + ", ".join(missing))
    versions = {
        "Blender": version([blender, "--background", "--version"]),
        "FreeCAD": version(["freecadcmd", "--version"]),
        "KiCad": version([kicad, "kicad-cli", "--version"]),
        "OpenSCAD": version(["openscad", "--version"]),
    }
    generated_at = datetime.now(timezone.utc).isoformat()
    evidence_path = work / "stage_execution_evidence.json"
    if not evidence_path.is_file():
        raise RuntimeError("cannot finalize task-01 without recorded stage execution evidence")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    expected_stages = ["prepare", "KiCad", "OpenSCAD", "FreeCAD", "Blender"]
    if not isinstance(evidence, list) or [entry.get("stage") for entry in evidence] != expected_stages:
        raise RuntimeError("task-01 stage evidence does not contain the required ordered stages")
    version_by_software = {key: value for key, value in versions.items()}
    for entry in evidence:
        if entry.get("exit_code") != 0:
            raise RuntimeError(f"task-01 stage did not exit successfully: {entry.get('stage')}")
        if not entry.get("started_at_utc") or not entry.get("finished_at_utc"):
            raise RuntimeError(f"task-01 stage lacks execution timestamps: {entry.get('stage')}")
        expected_hashes = entry.get("output_sha256")
        if not isinstance(expected_hashes, dict) or set(expected_hashes) != set(entry.get("outputs", [])):
            raise RuntimeError(f"task-01 stage lacks output hashes: {entry.get('stage')}")
        for name, expected_hash in expected_hashes.items():
            if sha256(work / name) != expected_hash:
                raise RuntimeError(f"task-01 stage output changed after execution: {name}")
        if entry.get("software") in version_by_software:
            entry["version"] = version_by_software[entry["software"]]
    log = {
        "actual_invocations": evidence,
        "commands": evidence[1:],
        "generated_at_utc": generated_at,
        "generated_on_host": socket.gethostname(),
        "required_software_sequence": ["KiCad", "OpenSCAD", "FreeCAD", "Blender"],
        "task": "task-01",
    }
    json_dump(work / "toolchain_invocation_log.json", log)

    hashes = {
        name: sha256(work / name)
        for name in REQUIRED_ARTIFACTS
        if name != "final_release_package.json" and (work / name).is_file()
    }
    geometry_tolerance = float(requirements["geometry_tolerance_mm"])
    aperture_tolerance = float(requirements["aperture_center_tolerance_mm"])
    aperture_by_ref = {
        item.get("ref"): item
        for item in freecad_report.get("aperture_checks", [])
        if isinstance(item, dict)
    }
    aperture_checks_pass = set(aperture_by_ref) == set(connectors)
    for ref, connector in connectors.items():
        item = aperture_by_ref.get(ref, {})
        aperture_checks_pass = aperture_checks_pass and all(
            [
                item.get("through") is True,
                item.get("cavity_to_exterior") is True,
                item.get("guard_wall_material_present") is True,
                close_number(item.get("center_error_mm"), 0.0, aperture_tolerance),
                close_number(item.get("residual_material_volume_mm3"), 0.0, 0.01),
                close_number(item.get("window_width_mm"), float(connector["window_width_mm"]), geometry_tolerance),
                close_number(item.get("window_height_mm"), float(connector["window_height_mm"]), geometry_tolerance),
                item.get("wall_direction") == connector["wall_direction"],
            ]
        )

    freecad_boolean_checks = freecad_report.get("checks", {})
    required_freecad_checks = {"apertures", "assembly_has_real_solids", "interference", "side_clearance", "u1_lid_clearance"}
    freecad_checks_pass = (
        isinstance(freecad_boolean_checks, dict)
        and set(freecad_boolean_checks) == required_freecad_checks
        and all(value is True for value in freecad_boolean_checks.values())
    )
    side_clearances = freecad_report.get("nominal_side_clearances_mm", {})
    required_sides = {"X_MINUS", "X_PLUS", "Y_MINUS", "Y_PLUS"}
    volume = float(freecad_report.get("enclosure_volume_mm3", -1.0))
    density = float(requirements["material_density_g_cm3"])
    expected_mass = volume * density / 1000.0
    mass_tolerance = max(0.001, abs(expected_mass) * float(requirements["mass_relative_tolerance"]))
    geometry_metrics_pass = all(
        [
            close_vector(freecad_report.get("enclosure_bbox_mm"), [float(value) for value in requirements["expected_enclosure_bbox_mm"]], geometry_tolerance),
            close_vector(freecad_report.get("nominal_board_bbox_mm"), [float(value) for value in openscad_params["board_bbox_mm"]], 1e-6),
            isinstance(freecad_report.get("measured_board_step_bbox_mm"), list),
            int(freecad_report.get("enclosure_solid_count", 0)) >= 1,
            int(freecad_report.get("pcb_solid_count", 0)) >= 1,
            int(freecad_report.get("stl_facet_count", 0)) > 0,
            set(side_clearances) == required_sides,
            all(float(side_clearances[side]) + 1e-9 >= float(requirements["minimum_side_clearance_mm"]) for side in required_sides),
            float(freecad_report.get("u1_lid_clearance_mm", -1.0)) + 1e-9 >= float(requirements["minimum_u1_lid_clearance_mm"]),
            float(freecad_report.get("interference_volume_mm3", float("inf"))) <= float(requirements["interference_volume_tolerance_mm3"]),
            volume > 0.0,
            close_number(freecad_report.get("estimated_shell_mass_g"), expected_mass, mass_tolerance),
        ]
    )

    role_counts = blender_report.get("role_counts", {})
    assignments = blender_report.get("material_assignments", {})
    expected_assignments = {
        "J1_X_MINUS_Aperture_Overlay": "keepout_warning",
        "J2_X_PLUS_Aperture_Overlay": "keepout_warning",
        "U1_Lid_Clearance_Overlay": "clearance_ok",
    }
    blender_roles_and_materials_pass = all(
        [
            int(role_counts.get("enclosure", 0)) >= 1,
            int(role_counts.get("pcb", 0)) >= 1,
            int(role_counts.get("component_envelope", 0)) >= len(kicad_export["components"]),
            all(material in assignments.get(name, []) for name, material in expected_assignments.items()),
            {"J1", "J2"}.issubset(set(blender_report.get("visible_keepouts", []))),
            close_number(blender_report.get("visible_u1_clearance_mm"), float(freecad_report["u1_lid_clearance_mm"]), geometry_tolerance),
        ]
    )
    blender_scene_pass = all(
        [
            blender_report.get("decision") == "pass",
            blender_report.get("active_camera") == "release_review_camera",
            blender_report.get("native_scene") == "04_blender_review.blend",
            blender_report.get("render") == "04_blender_review.png",
            blender_report.get("review_obj") == "04_blender_review.obj",
            blender_report.get("review_mtl") == "04_blender_review.mtl",
            (work / "04_blender_review.blend").stat().st_size > 10_000,
            (work / "04_blender_review.png").stat().st_size > 10_000,
        ]
    )
    checks = {
        "aperture_geometry_checks_pass": aperture_checks_pass,
        "blender_roles_and_materials_pass": blender_roles_and_materials_pass,
        "blender_scene_check_pass": blender_scene_pass,
        "freecad_boolean_checks_pass": freecad_checks_pass and freecad_report.get("decision") == "pass",
        "geometry_metrics_pass": geometry_metrics_pass,
        "required_artifacts_present": all((work / name).is_file() for name in REQUIRED_ARTIFACTS if name != "final_release_package.json"),
        "software_sequence_recorded": [entry["software"] for entry in log["commands"]] == ["KiCad", "OpenSCAD", "FreeCAD", "Blender"],
    }
    package = {
        "artifact_sha256": hashes,
        "checks": checks,
        "critical_requirement": requirements["critical_requirement"],
        "domain": requirements["domain"],
        "generated_at_utc": generated_at,
        "key_metrics": {
            "board_bbox_mm": openscad_params["board_bbox_mm"],
            "enclosure_bbox_mm": freecad_report["enclosure_bbox_mm"],
            "enclosure_volume_mm3": freecad_report["enclosure_volume_mm3"],
            "estimated_shell_mass_g": freecad_report["estimated_shell_mass_g"],
            "interference_volume_mm3": freecad_report["interference_volume_mm3"],
            "minimum_component_lid_clearance_mm": freecad_report["minimum_component_lid_clearance_mm"],
            "nominal_side_clearances_mm": freecad_report["nominal_side_clearances_mm"],
            "u1_lid_clearance_mm": freecad_report["u1_lid_clearance_mm"],
        },
        "release_decision": "pass" if all(checks.values()) else "fail",
        "required_artifacts": REQUIRED_ARTIFACTS,
        "software_sequence": ["KiCad", "OpenSCAD", "FreeCAD", "Blender"],
        "stage_outputs": {
            "Blender": ["04_blender_review.blend", "04_blender_review.obj", "04_blender_review.mtl", "04_blender_review.png", "04_blender_scene_report.json"],
            "FreeCAD": ["03_freecad_assembly.step", "03_freecad_assembly_for_blender.obj", "03_freecad_clearance_report.json"],
            "KiCad": ["01_kicad_board.kicad_pcb", "01_kicad_board.step", "01_kicad_export.json", "01_kicad_mechanical_map.csv"],
            "OpenSCAD": ["02_openscad_enclosure.scad", "02_openscad_enclosure.stl", "02_openscad_parameters.json"],
        },
        "task": "task-01",
        "title": requirements["title"],
        "tool_versions": versions,
    }
    json_dump(work / "final_release_package.json", package)
    if package["release_decision"] != "pass":
        raise RuntimeError("task-01 final release checks did not pass")


if __name__ == "__main__":
    main()
