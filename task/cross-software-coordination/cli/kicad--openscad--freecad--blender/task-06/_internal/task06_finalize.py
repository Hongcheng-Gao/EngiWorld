#!/usr/bin/env python3
from __future__ import annotations

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


TASK = "task-06"
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


def json_dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def json_load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} is not a JSON object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Blender render is not a PNG")
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def main() -> None:
    work = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    internal = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/engiworld-task06-internal")
    requirements = json_load(work / "mechanical_requirements.json")
    export = json_load(work / "01_kicad_export.json")
    params = json_load(work / "02_openscad_parameters.json")
    freecad = json_load(work / "03_freecad_clearance_report.json")
    blender = json_load(work / "04_blender_scene_report.json")
    if any(value.get("task") != TASK for value in (requirements, export, params, freecad, blender)):
        raise ValueError("task identity mismatch while finalizing task-06")
    kicad = os.environ.get("ENGIWORLD_KICAD_CLI") or shutil.which("kicad-cli") or "/usr/bin/kicad-cli"
    blender_bin = os.environ.get("ENGIWORLD_BLENDER") or shutil.which("blender") or "/snap/bin/blender"
    freecad_bin = os.environ.get("ENGIWORLD_FREECAD") or shutil.which("freecadcmd") or "freecadcmd"
    openscad_bin = os.environ.get("ENGIWORLD_OPENSCAD") or shutil.which("openscad") or "/usr/bin/openscad"
    tool_versions = {
        "KiCad": version([kicad, "--version"]),
        "OpenSCAD": version([openscad_bin, "--version"]),
        "FreeCAD": version([freecad_bin, "--version"]),
        "Blender": version([blender_bin, "--background", "--version"]),
    }
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
        if entry.get("software") in tool_versions:
            entry["version"] = tool_versions[entry["software"]]
    log = {
        "actual_invocations": evidence,
        "commands": selected,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "generated_on_host": socket.gethostname(),
        "required_software_sequence": SOFTWARE_SEQUENCE,
        "task": TASK,
        "tool_versions": tool_versions,
    }
    json_dump(work / "toolchain_invocation_log.json", log)

    missing = [name for name in REQUIRED_ARTIFACTS if name != "final_release_package.json" and not (work / name).is_file()]
    if missing:
        raise FileNotFoundError("missing task-06 artifacts: " + ", ".join(missing))
    width, height = png_dimensions(work / "04_blender_review.png")
    access_checks = freecad.get("access_checks", {})
    standoff_checks = freecad.get("standoff_checks", {})
    release_checks = {
        "all_nonself_artifacts_present": not missing,
        "assembly_is_substantial_brep": (work / "03_freecad_assembly.step").stat().st_size > 100_000,
        "blender_materials_distinct": len(set(blender.get("overlay_materials", {}).values())) == 3,
        "blender_mesh_qc": all(value == 0 for value in blender.get("mesh_qc", {}).values()),
        "blender_native_outputs": (work / "04_blender_review.blend").stat().st_size > 10_000
        and (work / "04_blender_review.obj").stat().st_size > 10_000,
        "blender_report_pass": blender.get("decision") == "pass",
        "blender_roles": blender.get("role_counts") == {"tray": 1, "lid": 1, "pcb": 1, "component": 5, "access_overlay": 3},
        "f1_keepout_uncovered": bool(access_checks.get("F1", {}).get("through"))
        and float(access_checks.get("F1", {}).get("projected_exclusion_residual_mm3", 1.0)) <= float(requirements["interference_volume_tolerance_mm3"]),
        "freecad_geometry_checks": bool(freecad.get("checks")) and all(freecad["checks"].values()),
        "freecad_report_pass": freecad.get("decision") == "pass",
        "interference": float(freecad.get("unintended_interference_volume_mm3", 1.0)) <= float(requirements["interference_volume_tolerance_mm3"]),
        "j1_j2_opposite_windows": all(bool(access_checks.get(ref, {}).get("through")) for ref in ("J1", "J2"))
        and access_checks.get("J1", {}).get("direction") == "X_MINUS"
        and access_checks.get("J2", {}).get("direction") == "X_PLUS",
        "mass_volume_consistent": abs(
            float(freecad["enclosure_mass_g"])
            - float(freecad["enclosure_volume_mm3"]) * float(requirements["enclosure_material_density_g_cm3"]) / 1000.0
        ) <= max(0.01, float(freecad["enclosure_mass_g"]) * 0.0001),
        "render_is_substantial": width >= 800 and height >= 600 and (work / "04_blender_review.png").stat().st_size > 10_000,
        "side_clearance": float(freecad["minimum_side_clearance_mm"]) + float(requirements["geometry_tolerance_mm"]) >= float(requirements["minimum_side_clearance_mm"]),
        "standoff_bores": set(standoff_checks) == {"MH1", "MH2", "MH3", "MH4"}
        and all(bool(item.get("continuous_bore")) and bool(item.get("standoff_present")) for item in standoff_checks.values()),
        "top_clearance": float(freecad["minimum_top_clearance_mm"]) + float(requirements["geometry_tolerance_mm"]) >= float(requirements["minimum_top_clearance_mm"]),
        "f1_top_clearance_unbounded": freecad.get("component_top_clearances_mm", {}).get("F1") is None,
    }
    decision = "pass" if all(release_checks.values()) else "fail"
    hash_names = [name for name in REQUIRED_ARTIFACTS if name != "final_release_package.json"]
    artifact_hashes = {name: sha256(work / name) for name in hash_names}
    artifact_sizes = {name: (work / name).stat().st_size for name in hash_names}
    package = {
        "artifact_sha256": artifact_hashes,
        "artifact_sizes_bytes": artifact_sizes,
        "critical_requirement": requirements["critical_requirement"],
        "domain": requirements["domain"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "key_metrics": {
            "access_checks": access_checks,
            "board_bbox_mm": freecad["board_bbox_mm"],
            "component_top_clearances_mm": freecad["component_top_clearances_mm"],
            "enclosure_bbox_mm": freecad["enclosure_bbox_mm"],
            "enclosure_mass_g": freecad["enclosure_mass_g"],
            "enclosure_volume_mm3": freecad["enclosure_volume_mm3"],
            "f1_keepout_intersection_mm3": freecad["f1_keepout_intersection_mm3"],
            "lid_mass_g": freecad["lid_mass_g"],
            "lid_separation_mm": freecad["lid_separation_mm"],
            "lid_volume_mm3": freecad["lid_volume_mm3"],
            "minimum_side_clearance_mm": freecad["minimum_side_clearance_mm"],
            "minimum_top_clearance_mm": freecad["minimum_top_clearance_mm"],
            "side_clearances_mm": freecad["side_clearances_mm"],
            "standoff_checks": standoff_checks,
            "tray_mass_g": freecad["tray_mass_g"],
            "tray_volume_mm3": freecad["tray_volume_mm3"],
            "unintended_interference_volume_mm3": freecad["unintended_interference_volume_mm3"],
        },
        "produced_artifacts": REQUIRED_ARTIFACTS,
        "checks": release_checks,
        "release_decision": decision,
        "required_artifacts": REQUIRED_ARTIFACTS,
        "software_sequence": SOFTWARE_SEQUENCE,
        "stage_outputs": {
            "KiCad": ["01_kicad_board.kicad_pcb", "01_kicad_board.step", "01_kicad_export.json", "01_kicad_mechanical_map.csv", "01_kicad_parameters.scad"],
            "OpenSCAD": ["02_openscad_enclosure.scad", "02_openscad_enclosure.stl", "02_openscad_parameters.json"],
            "FreeCAD": ["03_freecad_assembly.step", "03_freecad_assembly.obj", "03_freecad_clearance_report.json"],
            "Blender": ["04_blender_review.blend", "04_blender_review.obj", "04_blender_review.mtl", "04_blender_review.png", "04_blender_scene_report.json"],
        },
        "task": TASK,
        "title": requirements["title"],
        "tool_versions": tool_versions,
    }
    json_dump(work / "final_release_package.json", package)
    if decision != "pass":
        failed = sorted(name for name, passed in release_checks.items() if not passed)
        raise RuntimeError("task-06 final release failed: " + ", ".join(failed))


if __name__ == "__main__":
    main()
