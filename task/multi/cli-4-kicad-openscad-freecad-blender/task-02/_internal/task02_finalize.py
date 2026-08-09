#!/usr/bin/env python3
from __future__ import annotations

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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def version(command: list[str]) -> str:
    completed = subprocess.run(command, text=True, capture_output=True, timeout=60, check=False)
    output = (completed.stdout + "\n" + completed.stderr).strip()
    if completed.returncode != 0:
        raise RuntimeError(f"version command failed ({completed.returncode}): {' '.join(command)}\n{output}")
    return next((line.strip() for line in output.splitlines() if line.strip() and not line.strip().endswith("%")), output)


def main() -> None:
    work = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    internal = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/engiworld-task02-internal")
    kicad = "/home/user/Applications/kicad-10.0.2/kicad-10.0.2-x86_64.AppImage"
    blender = "/home/user/Applications/blender-4.2.3-linux-x64/blender"

    missing = [name for name in REQUIRED_ARTIFACTS[:-2] if not (work / name).is_file()]
    if missing:
        raise RuntimeError("cannot finalize task-02; missing artifacts: " + ", ".join(missing))

    requirements = json.loads((work / "mechanical_requirements.json").read_text(encoding="utf-8"))
    freecad_report = json.loads((work / "03_freecad_clearance_report.json").read_text(encoding="utf-8"))
    blender_report = json.loads((work / "04_blender_scene_report.json").read_text(encoding="utf-8"))
    params = json.loads((work / "02_openscad_parameters.json").read_text(encoding="utf-8"))
    versions = {
        "Blender": version([blender, "--background", "--version"]),
        "FreeCAD": version(["freecadcmd", "--version"]),
        "KiCad": version([kicad, "kicad-cli", "--version"]),
        "OpenSCAD": version(["openscad", "--version"]),
    }
    generated_at = datetime.now(timezone.utc).isoformat()
    evidence_path = work / "stage_execution_evidence.json"
    if not evidence_path.is_file():
        raise RuntimeError("cannot finalize task-02 without recorded stage execution evidence")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    expected_stages = ["prepare", "KiCad", "OpenSCAD", "FreeCAD", "Blender"]
    if not isinstance(evidence, list) or [entry.get("stage") for entry in evidence] != expected_stages:
        raise RuntimeError("task-02 stage evidence does not contain the required ordered stages")
    for entry in evidence:
        if entry.get("exit_code") != 0:
            raise RuntimeError(f"task-02 stage did not exit successfully: {entry.get('stage')}")
        if not entry.get("started_at_utc") or not entry.get("finished_at_utc"):
            raise RuntimeError(f"task-02 stage lacks execution timestamps: {entry.get('stage')}")
        expected_hashes = entry.get("output_sha256")
        if not isinstance(expected_hashes, dict) or set(expected_hashes) != set(entry.get("outputs", [])):
            raise RuntimeError(f"task-02 stage lacks output hashes: {entry.get('stage')}")
        for name, expected_hash in expected_hashes.items():
            if sha256(work / name) != expected_hash:
                raise RuntimeError(f"task-02 stage output changed after execution: {name}")
        if entry.get("software") in versions:
            entry["version"] = versions[entry["software"]]
    log = {
        "actual_invocations": evidence,
        "commands": evidence,
        "generated_at_utc": generated_at,
        "generated_on_host": socket.gethostname(),
        "required_software_sequence": ["KiCad", "OpenSCAD", "FreeCAD", "Blender"],
        "task": "task-02",
    }
    json_dump(work / "toolchain_invocation_log.json", log)

    geometry_checks = freecad_report.get("checks", {})
    checks = {
        "blender_review_pass": blender_report.get("decision") == "pass",
        "c1_clamp_clearance_pass": float(freecad_report.get("c1_clamp_clearance_mm", -1.0)) + 1e-6 >= float(requirements["minimum_c1_clamp_clearance_mm"]),
        "freecad_geometry_pass": freecad_report.get("decision") == "pass" and isinstance(geometry_checks, dict) and all(value is True for value in geometry_checks.values()),
        "l1_keepout_pass": float(freecad_report.get("l1_keepout_intersection_mm3", float("inf"))) <= float(requirements["interference_volume_tolerance_mm3"]),
        "required_artifacts_present": all((work / name).is_file() for name in REQUIRED_ARTIFACTS[:-1]),
        "u1_contact_pass": 0.0 <= float(freecad_report.get("u1_contact_gap_mm", -1.0)) <= float(requirements["maximum_u1_contact_gap_mm"]) + 1e-6,
    }
    hashes = {name: sha256(work / name) for name in REQUIRED_ARTIFACTS[:-2]}
    hashes["toolchain_invocation_log.json"] = sha256(work / "toolchain_invocation_log.json")
    package = {
        "artifact_sha256": hashes,
        "checks": checks,
        "critical_requirement": requirements["critical_requirement"],
        "domain": requirements["domain"],
        "generated_at_utc": generated_at,
        "key_metrics": {
            "board_bbox_mm": params["board_bbox_mm"],
            "c1_clamp_clearance_mm": freecad_report["c1_clamp_clearance_mm"],
            "enclosure_bbox_mm": freecad_report["enclosure_bbox_mm"],
            "enclosure_volume_mm3": freecad_report["enclosure_volume_mm3"],
            "estimated_shell_mass_g": freecad_report["estimated_shell_mass_g"],
            "interference_volume_mm3": freecad_report["interference_volume_mm3"],
            "l1_keepout_intersection_mm3": freecad_report["l1_keepout_intersection_mm3"],
            "side_clearances_mm": freecad_report["nominal_side_clearances_mm"],
            "u1_contact_gap_mm": freecad_report["u1_contact_gap_mm"],
        },
        "release_decision": "pass" if all(checks.values()) else "fail",
        "required_artifacts": REQUIRED_ARTIFACTS,
        "software_sequence": ["KiCad", "OpenSCAD", "FreeCAD", "Blender"],
        "task": "task-02",
        "title": requirements["title"],
        "tool_versions": versions,
    }
    json_dump(work / "final_release_package.json", package)
    if package["release_decision"] != "pass":
        raise RuntimeError("task-02 final release checks did not pass")


if __name__ == "__main__":
    main()
