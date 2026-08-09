#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "task-07"
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
    completed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=40, check=False)
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    return lines[0] if lines else f"unreported (return code {completed.returncode})"


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Blender render is not a PNG")
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def normalize_step_whitespace(path: Path) -> None:
    data = path.read_bytes()
    normalized = b"\n".join(line.rstrip(b" \t\r") for line in data.split(b"\n"))
    if normalized != data:
        path.write_bytes(normalized)


def main() -> None:
    work = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    requirements = json_load(work / "mechanical_requirements.json")
    export = json_load(work / "01_kicad_export.json")
    params = json_load(work / "02_openscad_parameters.json")
    freecad = json_load(work / "03_freecad_clearance_report.json")
    blender = json_load(work / "04_blender_scene_report.json")
    if any(value.get("task") != TASK for value in (requirements, export, params, freecad, blender)):
        raise ValueError("task identity mismatch while finalizing task-07")
    normalize_step_whitespace(work / "03_freecad_assembly.step")

    kicad = os.environ.get("ENGIWORLD_KICAD", "/home/user/Applications/kicad-10.0.2/kicad-10.0.2-x86_64.AppImage")
    blender_bin = os.environ.get("ENGIWORLD_BLENDER", "/home/user/Applications/blender-4.2.3-linux-x64/blender")
    freecad_bin = os.environ.get("ENGIWORLD_FREECAD", "freecadcmd")
    openscad_bin = os.environ.get("ENGIWORLD_OPENSCAD", "openscad")
    internal = Path(__file__).resolve().parent
    tool_versions = {
        "KiCad": version([kicad, "kicad-cli", "--version"]),
        "OpenSCAD": version([openscad_bin, "--version"]),
        "FreeCAD": version([freecad_bin, "--version"]),
        "Blender": version([blender_bin, "--version"]),
    }
    commands = [
        {
            "command": f"cd {work} && {kicad} kicad-cli pcb export step --force --board-only --output 01_kicad_board.step 01_kicad_board.kicad_pcb",
            "inputs": ["01_kicad_board.kicad_pcb"],
            "outputs": ["01_kicad_board.step"],
            "software": "KiCad",
            "version": tool_versions["KiCad"],
        },
        {
            "command": f"cd {work} && {openscad_bin} -o 02_openscad_enclosure.stl 02_openscad_enclosure.scad",
            "inputs": ["01_kicad_parameters.scad", "02_openscad_enclosure.scad"],
            "outputs": ["02_openscad_enclosure.stl"],
            "software": "OpenSCAD",
            "version": tool_versions["OpenSCAD"],
        },
        {
            "command": f"ENGIWORLD_WORKDIR={work} {freecad_bin} {internal / 'task07_freecad_stage.py'}",
            "inputs": ["01_kicad_board.step", "01_kicad_export.json", "01_kicad_mechanical_map.csv", "02_openscad_enclosure.stl", "02_openscad_parameters.json"],
            "outputs": ["03_freecad_assembly.step", "03_freecad_assembly.obj", "03_freecad_clearance_report.json"],
            "software": "FreeCAD",
            "version": tool_versions["FreeCAD"],
        },
        {
            "command": f"{blender_bin} --background --factory-startup --python {internal / 'task07_blender_stage.py'} -- {work}",
            "inputs": ["03_freecad_assembly.obj", "03_freecad_clearance_report.json"],
            "outputs": ["04_blender_review.blend", "04_blender_review.obj", "04_blender_review.mtl", "04_blender_review.png", "04_blender_scene_report.json"],
            "software": "Blender",
            "version": tool_versions["Blender"],
        },
    ]
    preparation = {
        "command": f"python3 {internal / 'task07_prepare.py'} {work}",
        "inputs": ["board_input.kicad_pcb", "mechanical_requirements.json", "connector_keepouts.csv", "enclosure_seed.scad", "handoff_notes.md"],
        "outputs": ["01_kicad_board.kicad_pcb", "01_kicad_export.json", "01_kicad_mechanical_map.csv", "01_kicad_parameters.scad", "02_openscad_enclosure.scad", "02_openscad_parameters.json"],
        "software": "Python handoff generator",
        "version": sys.version.split()[0],
    }
    log = {
        "actual_invocations": [preparation, *commands],
        "commands": commands,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "generated_on_host": socket.gethostname(),
        "preparation": preparation,
        "productive_software_sequence": SOFTWARE_SEQUENCE,
        "required_software_sequence": SOFTWARE_SEQUENCE,
        "task": TASK,
        "tool_versions": tool_versions,
    }
    json_dump(work / "toolchain_invocation_log.json", log)

    missing = [name for name in REQUIRED_ARTIFACTS if name != "final_release_package.json" and not (work / name).is_file()]
    if missing:
        raise FileNotFoundError("missing task-07 artifacts: " + ", ".join(missing))
    width, height = png_dimensions(work / "04_blender_review.png")
    access_checks = freecad.get("access_checks", {})
    standoff_checks = freecad.get("standoff_checks", {})
    optical = freecad.get("optical_corridor", {})
    optical_overlay = blender.get("optical_overlay", {})
    optical_requirements = requirements["optical_corridor"]
    release_checks = {
        "all_nonself_artifacts_present": not missing,
        "assembly_is_substantial_brep": (work / "03_freecad_assembly.step").stat().st_size > 100_000,
        "blender_materials_distinct": len(set(blender.get("overlay_materials", {}).values())) == 2,
        "blender_mesh_qc": all(value == 0 for value in blender.get("mesh_qc", {}).values()),
        "blender_native_outputs": (work / "04_blender_review.blend").stat().st_size > 10_000
        and (work / "04_blender_review.obj").stat().st_size > 10_000,
        "blender_report_pass": blender.get("decision") == "pass",
        "blender_roles": blender.get("role_counts") == {"tray": 1, "lid": 1, "pcb": 1, "component": 5, "access_overlay": 1, "optical_overlay": 1},
        "blender_optical_overlay": bool(optical_overlay.get("independent_object"))
        and float(optical_overlay.get("endpoint_error_mm", 1.0)) <= float(optical_requirements["endpoint_tolerance_mm"])
        and float(optical_overlay.get("radius_error_mm", 1.0)) <= float(optical_requirements["radius_tolerance_mm"]),
        "component_height_correct": abs(float(export["max_component_height_mm"]) - 2.8) <= float(requirements["geometry_tolerance_mm"]),
        "freecad_geometry_checks": bool(freecad.get("checks")) and all(freecad["checks"].values()),
        "freecad_report_pass": freecad.get("decision") == "pass",
        "interference": float(freecad.get("unintended_interference_volume_mm3", 1.0)) <= float(requirements["interference_volume_tolerance_mm3"]),
        "j1_y_minus_window": set(access_checks) == {"J1"}
        and bool(access_checks.get("J1", {}).get("through"))
        and bool(access_checks.get("J1", {}).get("minimum_guard_material_present"))
        and access_checks.get("J1", {}).get("direction") == "Y_MINUS",
        "mass_volume_consistent": abs(
            float(freecad["enclosure_mass_g"])
            - float(freecad["enclosure_volume_mm3"]) * float(requirements["enclosure_material_density_g_cm3"]) / 1000.0
        ) <= max(0.01, float(freecad["enclosure_mass_g"]) * 0.0001),
        "render_is_substantial": width >= 800 and height >= 600 and (work / "04_blender_review.png").stat().st_size > 10_000,
        "optical_corridor_unobstructed": bool(optical.get("unobstructed"))
        and float(freecad.get("optical_carrier_intersection_mm3", 1.0)) <= float(optical_requirements["maximum_carrier_intersection_mm3"]),
        "side_clearance": float(freecad["minimum_side_clearance_mm"]) + float(requirements["geometry_tolerance_mm"]) >= float(requirements["minimum_side_clearance_mm"]),
        "standoff_bores": set(standoff_checks) == {"MH1", "MH2", "MH3", "MH4"}
        and all(bool(item.get("continuous_bore")) and bool(item.get("standoff_present")) for item in standoff_checks.values()),
        "top_clearance": float(freecad["minimum_top_clearance_mm"]) + float(requirements["geometry_tolerance_mm"]) >= float(requirements["minimum_top_clearance_mm"]),
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
            "minimum_side_clearance_mm": freecad["minimum_side_clearance_mm"],
            "minimum_top_clearance_mm": freecad["minimum_top_clearance_mm"],
            "optical_carrier_intersection_mm3": freecad["optical_carrier_intersection_mm3"],
            "optical_corridor": optical,
            "side_clearances_mm": freecad["side_clearances_mm"],
            "standoff_checks": standoff_checks,
            "unintended_interference_volume_mm3": freecad["unintended_interference_volume_mm3"],
        },
        "produced_artifacts": REQUIRED_ARTIFACTS,
        "release_checks": release_checks,
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
        raise RuntimeError("task-07 final release failed: " + ", ".join(failed))


if __name__ == "__main__":
    main()
