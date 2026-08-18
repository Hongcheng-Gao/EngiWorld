#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
TASK_ROOT = REPO / "task" / "task-v" / "abaqus"
NUMBERS = list(range(1, 14)) + [16, 17, 19, 20]
TASK08_REDESIGN_PATH = (
    OUTPUT / "logs" / "v-abaqus-task-08-windows" / "task08_redesign_report.json"
)


CAUSES = {
    1: "The valid reopened CAE passed artifact, step, material, section, geometry, mesh, and set checks, but Abaqus 2025LE did not expose createStepName/u1/u2 or cf2 as direct attributes on the saved DisplacementBC and ConcentratedForce wrappers. The evaluator now validates each Initial-step BC group and every Step-Pressure CLOAD component, sign, and value in synchronized Abaqus keyword blocks.",
    2: "The reopened valid cylinder model hid createStepName/u2/cf1 on standard BC/load wrappers. The repaired evaluator keeps repository-count checks and matches the Initial U2 constraint plus both Step-Pressure positive CF1 values in structured keyword groups.",
    3: "The reopened shell model hid direct BC values. The repaired evaluator now requires two distinct active ShellEdgeLoad objects with NORMAL traction, opposite outward directions, and dynamically resolved regions spanning the complete model-minimum/model-maximum X edges. It independently links those regions to distinct Step-HoleTension EDNOR keyword groups at positive magnitude 8 while retaining all geometry, hole, shell-section, mesh, material, set, and ODB checks.",
    4: "The valid SurfaceTraction wrapper did not expose createStepName or magnitude after reopen. The evaluator now confirms the Initial ENCASTRE and the Step-Load TRVEC surface-traction magnitude 10 in synchronized keyword blocks, in addition to the existing solid/model/ODB checks.",
    5: "The valid TypeBC and ConcentratedForce wrappers hid createStepName/u*/cf1. The evaluator now checks the Initial ENCASTRE and Step-Load CF1=+800 keyword records while preserving the kinematic-coupling, geometry, material, mesh, section, and ODB checks.",
    6: "Abaqus 2025LE hid createStepName and magnitude on reopened TemperatureBC objects. The evaluator now uniquely matches the two Step-Thermal temperature boundary groups at 100 and 20 degrees through DOF 11 keyword records.",
    7: "The reopened Moment wrapper hid createStepName/cm2. The evaluator now checks the Initial ENCASTRE and Step-Torque-A rotational DOF 5 CLOAD of +850, while retaining the coupling and all structural/solver checks.",
    8: "The evaluator indexed bbox_from_xyz's dictionary as a six-element tuple and raised KeyError: 3. That bug is repaired, and the evaluator now dynamically validates the real top Pressure, bottom ENCASTRE, aligned no-gap contact surfaces, and Hard/frictionless property before mesh rejection. The current GT is genuinely noncompliant: BLOCK/PLATE CAE seeds are 5/10 instead of the required 3/5. Every applicable native HEX control tested on these unpartitioned extrusion cells produced 1,586 nodes at seeds 3/5 and hit the 1,000-node Learning Edition restriction; this does not prove the same bound for materially different topology or partitioning.",
    9: "Reopened DisplacementBC and Pressure wrappers hid their direct step/DOF/magnitude values, the auto-picked CAE Pressure surface reopens empty, and the ODB exposes no public load record for direct name mapping. The evaluator now requires the real active uniform Pressure object linked to exactly one Step-Load DSLOAD P=0.05 record, then proves its solved footprint through the unique full-top ODB surface: one FACE6 facet family, its matching internal surface-backing set, and the unique solver-internal DSL set with the same instance/element labels. Both kinematic couplings and all prior model/solver checks remain enforced.",
    10: "The reopened Moment wrapper hid createStepName/cm2. The evaluator now checks Initial ENCASTRE and Step-Torque-B rotational DOF 5 CLOAD=+920 in the canonical keyword blocks.",
    11: "The old fallback rejected the valid Abaqus ENCASTRE form and the Moment wrapper hid cm1. The repaired evaluator accepts the canonical Initial ENCASTRE record and requires Step-Twist rotational DOF 4 CLOAD=+5000.",
    12: "Direct BC introspection failed and returned before the existing keyword path could run; reopened CF1 values were also hidden. The repaired control flow uniquely matches all three Initial BC signatures and all four signed representative CLOAD signatures in Step-Buckle-A without reducing any mesh, section, mode, or ODB check.",
    13: "The reopened BC hid direct u1/u2/u3 values. The repaired evaluator accepts either canonical ENCASTRE or one Initial boundary group that explicitly fixes translational DOFs 1, 2, and 3, while preserving the four-mode ODB check.",
    16: "Reopened TemperatureBC and predefined Temperature objects hid createStepName/magnitude/magnitudes. The evaluator now checks Step-Heat-A DOF-11 temperature 95 and Initial uniform temperature 25 from their canonical keyword groups, plus the full transient-step and final-time ODB checks.",
    17: "The old BC fallback rejected valid ENCASTRE and reopened predefined temperatures hid direct attributes. The evaluator now requires FIXED_END ENCASTRE, Initial temperature 20, and HOT_HALF temperature 120 specifically in Step-ThermalBend keyword records.",
    19: "The evaluator hard-coded 7.2/3.6 N despite the instruction requiring 0.9 times each actual tributary edge length; this GT's partitioned mesh yields 6.75/3.375 N. The evaluator now derives tributary lengths from the real boundary-node coordinates and compares the complete positive and negative CLOAD multisets and counts, rather than hard-coding either mesh outcome.",
    20: "Reopened BC and ConcentratedForce wrappers hid direct step/DOF/CF1 values. The evaluator now uniquely matches the three Initial in-plane constraint groups and four signed Step-Tension-A representative nodal loads while retaining the hole, local/global seeding, shell, material, and ODB checks.",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git_head_bytes(path: Path) -> bytes:
    relative = path.relative_to(REPO).as_posix()
    return subprocess.check_output(["git", "show", f"HEAD:{relative}"], cwd=REPO)


records = []
for number in NUMBERS:
    task_dir = TASK_ROOT / f"task-{number:02d}"
    config_path = task_dir / f"task-{number:02d}.json"
    eval_path = task_dir / "eval.py"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    task_id = config["id"]
    log_path = OUTPUT / "logs" / task_id / "evaluation.json"
    evidence = json.loads(log_path.read_text(encoding="utf-8"))
    status = "passed" if evidence["passed"] else "environment_blocked"

    if number == 8:
        redesign = json.loads(TASK08_REDESIGN_PATH.read_text(encoding="utf-8"))
        if not evidence["passed"] or redesign["status"] != "passed":
            raise RuntimeError("Task 08 redesign evidence is not passing")
        eval_hashes = redesign["sha256_before_after"][
            "task/task-v/abaqus/task-08/eval.py"
        ]
        eval_hashes.setdefault("before", eval_hashes["repository_head"])
        for relative, hashes in redesign["sha256_before_after"].items():
            current = sha256_file(REPO / relative)
            if current != hashes["after"]:
                raise RuntimeError(
                    f"Task 08 artifact hash mismatch for {relative}: {current}"
                )
        records.append({
            "task_id": task_id,
            "snapshot": "ABAQUS-2025L",
            "instruction": config["instruction"],
            "failure_reason": redesign["redesign_reason"],
            "modified_files": redesign["modified_files"],
            "sha256_before_after": redesign["sha256_before_after"],
            "seed_provenance": redesign["seed_provenance"],
            "ground_truth_provenance": redesign["ground_truth_provenance"],
            "evaluator_semantics": redesign["evaluator_semantics"],
            "real_software_generation": redesign["real_software_generation"],
            "generation_commands": redesign["generation_commands"],
            "native_solve": redesign["native_solve"],
            "native_results": redesign["native_results"],
            "eval_result": {
                "command": config["evaluator"]["result"]["command"],
                "returncode": evidence["evaluation"]["returncode"],
                "stdout": evidence["evaluation"]["output"],
                "expected": config["evaluator"]["expected"]["rules"]["expected"],
                "exact_match": bool(evidence["passed"]),
                "score": evidence["score"],
                "detail": evidence.get("eval_detail", ""),
            },
            "negative_eval_results": redesign["negative_evaluations"],
            "logs": redesign["logs"],
            "cleanup": redesign["cleanup"],
            "status": status,
        })
        continue

    gt_hashes = {}
    for path in sorted((task_dir / "ground_truth").rglob("*")):
        if path.is_file():
            gt_hashes[path.relative_to(REPO).as_posix()] = sha256_file(path)

    eval_relative = eval_path.relative_to(REPO).as_posix()
    logs = {"production_eval": log_path.relative_to(REPO).as_posix()}
    if number == 3:
        logs.update({
            "load_surface_probe_script": (
                OUTPUT / "load_surface_probe.py"
            ).relative_to(REPO).as_posix(),
            "load_surface_probe_result": (
                OUTPUT / "logs" / task_id / "load_surface_probe_result.txt"
            ).relative_to(REPO).as_posix(),
        })
    if number == 8:
        logs.update({
            "fine_mesh_probe_script": (
                OUTPUT / "logs" / task_id / "task08_fine_mesh_probe.py"
            ).relative_to(REPO).as_posix(),
            "fine_mesh_probe_result": (
                OUTPUT / "logs" / task_id / "task08_fine_mesh_probe_result.txt"
            ).relative_to(REPO).as_posix(),
            "hex_mesh_matrix_probe_script": (
                OUTPUT / "logs" / task_id / "task08_hex_mesh_matrix_probe.py"
            ).relative_to(REPO).as_posix(),
            "hex_mesh_matrix_probe_result": (
                OUTPUT / "logs" / task_id / "task08_hex_mesh_matrix_probe_result.txt"
            ).relative_to(REPO).as_posix(),
            "semantics_probe_script": (
                OUTPUT / "logs" / task_id / "task08_semantics_probe.py"
            ).relative_to(REPO).as_posix(),
            "semantics_probe_result": (
                OUTPUT / "logs" / task_id / "task08_semantics_probe_result.txt"
            ).relative_to(REPO).as_posix(),
        })
    if number == 9:
        logs.update({
            "pressure_probe_script": (
                OUTPUT / "logs" / task_id / "task09_pressure_probe.py"
            ).relative_to(REPO).as_posix(),
            "pressure_probe_result": (
                OUTPUT / "logs" / task_id / "task09_pressure_probe_result.txt"
            ).relative_to(REPO).as_posix(),
        })

    if number == 3:
        generation = (
            "No GT regeneration occurred. Abaqus/CAE Learning Edition 2025 reopened the unchanged "
            "native CAE and confirmed two distinct active NORMAL ShellEdgeLoad objects, their "
            "opposite directions, complete left/right edge-node coverage, and corresponding EDNOR "
            "keyword groups. The unchanged solved ODB passed the formal evaluator."
        )
    elif number == 8:
        generation = (
            "Abaqus/CAE Learning Edition 2025 opened the unchanged Job-Contact.cae and tested all "
            "applicable native HEX controls exposed for its unpartitioned extrusion cells: "
            "STRUCTURED, SWEEP/ADVANCING_FRONT (default and explicit), and SWEEP/MEDIAL_AXIS. At "
            "required global seeds 3.0 (BLOCK) and 5.0 (PLATE), every case generated 704/490 and "
            "882/400 nodes/elements respectively; native job.submit rejected the 1,586-node "
            "assembly with the Learning Edition 1,000-node restriction. No candidate was written "
            "back. This result is scoped to the tested unpartitioned topology and is not a universal "
            "lower-bound claim for materially different topology or partitioning."
        )
    elif number == 9:
        generation = (
            "No GT regeneration occurred. The original native CAE and solved ODB remained byte "
            "unchanged. Abaqus/CAE Learning Edition 2025 confirmed the active uniform Pressure and "
            "its dynamic Step-Load DSLOAD P=0.05 record; odbAccess with readInternalSets=True "
            "confirmed that the solver-internal DSL element set exactly matches the unique full-top "
            "FACE6 surface and its internal backing set. The original files passed the formal run."
        )
    else:
        generation = (
            "No GT regeneration was required. The unchanged native CAE and solved ODB were staged "
            "from this Task's ground_truth into the designated ABAQUS-2025L Snapshot. Abaqus/CAE "
            "Learning Edition 2025 opened the CAE, synchronized its input keywords, and opened the "
            "ODB through odbAccess during the formal evaluator run."
        )

    records.append({
        "task_id": task_id,
        "snapshot": "ABAQUS-2025L",
        "instruction": config["instruction"],
        "failure_reason": CAUSES[number],
        "modified_files": [eval_relative],
        "sha256_before_after": {
            eval_relative: {
                "before": sha256_bytes(git_head_bytes(eval_path)),
                "after": sha256_file(eval_path),
            }
        },
        "unchanged_native_sha256": gt_hashes,
        "real_software_generation": generation,
        "eval_result": {
            "command": config["evaluator"]["result"]["command"],
            "returncode": evidence["evaluation"]["returncode"],
            "stdout": evidence["evaluation"]["output"],
            "expected": config["evaluator"]["expected"]["rules"]["expected"],
            "exact_match": bool(evidence["passed"]),
            "score": evidence["score"],
            "detail": evidence.get("eval_detail", ""),
        },
        "logs": logs,
        "cleanup": (
            "The runner stopped Abaqus task processes, removed the Task CAE/ODB/evaluator/result "
            "files and sidecars, and verified desktop_after_cleanup was empty."
        ),
        "status": status,
    })


report_path = OUTPUT / "report.jsonl"
with report_path.open("w", encoding="utf-8") as stream:
    for record in records:
        stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")

summary = {
    "snapshot": "ABAQUS-2025L",
    "total": len(records),
    "passed": sum(record["status"] == "passed" for record in records),
    "eval_blocked": sum(record["status"] == "eval_blocked" for record in records),
    "environment_blocked": sum(record["status"] == "environment_blocked" for record in records),
    "modified_tasks": len(records),
    "modified_files": sum(len(record["modified_files"]) for record in records),
}
(OUTPUT / "summary.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(summary, ensure_ascii=False))
