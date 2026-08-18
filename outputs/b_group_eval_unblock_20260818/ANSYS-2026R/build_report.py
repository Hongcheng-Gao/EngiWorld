#!/usr/bin/env python3
"""Build and validate the ANSYS-2026R per-task repair report."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
OLD_OUTPUT = REPO / "outputs/b_group_gt_repair_20260817/ANSYS-2026R"


TASKS = [
    {
        "id": "c-ansys-task-15-windows",
        "dir": "task/task-c/ansys/task-15",
        "failure": "The internal Fluent checks returned True, but PyFluent file-loading output preceded the final marker, so exact_match did not receive exactly 'True\\n'.",
        "generation": "No GT regeneration was required. The native pipe case/data were reopened by Fluent 2026 R1 and passed mesh, zones, materials, boundary conditions, and field checks. The evaluator now isolates PyFluent diagnostics while preserving every native check.",
        "files": ["eval.py"],
        "old_logs": ["logs/c-ansys-task-15-windows/diagnosis.txt"],
    },
    {
        "id": "v-ansys-task-04-windows",
        "dir": "task/task-v/ansys/task-04",
        "failure": "The evaluator searched MPLIST for fixed decimal substrings, while ANSYS 2026 R1 printed valid KXX and density values in scientific notation.",
        "generation": "No GT regeneration was required. ANSYS Mechanical APDL 2026 R1 reopened the native transient thermal DB/RTH; the evaluator numerically parses KXX, C, and DENS and retains geometry, mesh, boundary, time, and temperature checks.",
        "files": ["eval.py"],
        "old_logs": ["logs/v-ansys-task-04-windows/diagnosis.txt", "logs/v-ansys-task-04-windows/raw_probe.log"],
    },
    {
        "id": "v-ansys-task-05-windows",
        "dir": "task/task-v/ansys/task-05",
        "failure": "The evaluator searched MPLIST for a fixed density substring, while ANSYS 2026 R1 printed the correct beam density in scientific notation.",
        "generation": "No GT regeneration was required. ANSYS Mechanical APDL 2026 R1 reopened the modal DB/RST; the evaluator numerically parses EX, NUXY, and DENS and retains section, mesh, constraints, and modal-frequency checks.",
        "files": ["eval.py"],
        "old_logs": ["logs/v-ansys-task-05-windows/diagnosis.txt", "logs/v-ansys-task-05-windows/raw_probe.log"],
    },
    {
        "id": "v-ansys-task-06-windows",
        "dir": "task/task-v/ansys/task-06",
        "failure": "The evaluator issued invalid MAPDL command KEYOPT,1,LIST and failed before it could accept the valid axisymmetric PLANE183 model.",
        "generation": "No GT regeneration was required. ANSYS Mechanical APDL 2026 R1 reopened the native cylinder DB/RST; ETLIST's complete PLANE183 axisymmetric description is now used while material, geometry, pressure, constraints, mesh, and result checks remain active.",
        "files": ["eval.py"],
        "old_logs": ["logs/v-ansys-task-06-windows/diagnosis.txt", "logs/v-ansys-task-06-windows/raw_probe.log"],
    },
    {
        "id": "v-ansys-task-08-windows",
        "dir": "task/task-v/ansys/task-08",
        "failure": "The evaluator rejected scientific-notation ALPX output and looked for a nodal BFLIST temperature even though this GT stores the required temperature as element body loads; the first repair inferred 100 C only from the 252 MPa result and did not directly prove the complete applied temperature field.",
        "generation": "No GT regeneration was required. ANSYS Mechanical APDL 2026 R1 reopened the native thermal-stress DB/RST. The strengthened evaluator numerically checks the material and TREF=20, requires BFELIST to contain exactly the current 80 model elements exactly once, requires all eight expanded SOLID185 temperatures on every element to equal 100 C, rejects nodal force and element surface loads, retains both restrained end faces, and uses the E*alpha*(100-20)=252 MPa result only as corroboration.",
        "files": ["eval.py"],
        "old_logs": ["logs/v-ansys-task-08-windows/diagnosis.txt", "logs/v-ansys-task-08-windows/raw_probe.log"],
        "evidence_logs": [
            "logs/v-ansys-task-08-windows/task08_uniform_temp_evidence.jsonl",
            "logs/v-ansys-task-08-windows/task08_uniform_temp_probe.py",
        ],
    },
    {
        "id": "v-ansys-task-09-windows",
        "dir": "task/task-v/ansys/task-09",
        "failure": "The evaluator applied Python truth testing to nonempty NumPy mesh arrays, raising ValueError before the Fluent checks, and PyFluent diagnostics also polluted exact-match stdout.",
        "generation": "No GT regeneration was required. Fluent 2026 R1 reopened the cavity case/data; explicit None/len checks and stdout isolation allow all original mesh, material, boundary, and solution checks to run.",
        "files": ["eval.py"],
        "old_logs": ["logs/v-ansys-task-09-windows/diagnosis.txt", "logs/v-ansys-task-09-windows/audit_candidates/exact_eval_diagnosis.log"],
    },
    {
        "id": "v-ansys-task-10-windows",
        "dir": "task/task-v/ansys/task-10",
        "failure": "The internal Fluent checks returned True, but PyFluent loading diagnostics preceded the final marker and broke exact_match.",
        "generation": "No GT regeneration was required. Fluent 2026 R1 reopened the native case/data and completed all original checks; only evaluator-owned stdout/stderr is isolated.",
        "files": ["eval.py"],
        "old_logs": ["logs/v-ansys-task-10-windows/diagnosis.txt"],
    },
    {
        "id": "v-ansys-task-14-windows",
        "dir": "task/task-v/ansys/task-14",
        "failure": "The evaluator searched MPLIST for a fixed density substring, while ANSYS 2026 R1 printed the correct density in scientific notation.",
        "generation": "No GT regeneration was required. ANSYS Mechanical APDL 2026 R1 reopened the harmonic DB/RST; numerical material parsing preserves element, mesh, support, load, frequency, and response checks.",
        "files": ["eval.py"],
        "old_logs": ["logs/v-ansys-task-14-windows/diagnosis.txt", "logs/v-ansys-task-14-windows/raw_probe.log"],
    },
    {
        "id": "v-ansys-task-15-windows",
        "dir": "task/task-v/ansys/task-15",
        "failure": "The internal Fluent checks returned True, but PyFluent loading diagnostics preceded the final marker and broke exact_match.",
        "generation": "No GT regeneration was required. Fluent 2026 R1 reopened the native pipe case/data and completed all original mesh, near-wall, material, boundary, velocity-profile, and pressure checks; only evaluator-owned output is isolated.",
        "files": ["eval.py"],
        "old_logs": ["logs/v-ansys-task-15-windows/diagnosis.txt"],
    },
    {
        "id": "v-ansys-task-16-windows",
        "dir": "task/task-v/ansys/task-16",
        "failure": "The original GT did not satisfy every downstream flow check, and the evaluator also raised ValueError by truth-testing NumPy mesh arrays before a valid candidate could be scored.",
        "generation": "Fluent 2026 R1 loaded the current Poiseuille model, set laminar water properties, SIMPLE and second-order schemes, initialized and ran 1200 iterations, verified mass balance and velocities, then wrote a solved 1920-cell/2025-node CAS/DAT pair. The evaluator fix only replaces ambiguous NumPy truth testing and isolates diagnostics.",
        "files": ["eval.py", "ground_truth/poiseuille_2d.cas", "ground_truth/poiseuille_2d.dat"],
        "old_logs": [
            "logs/v-ansys-task-16-windows/candidate_generation.log",
            "logs/v-ansys-task-16-windows/candidate_inner_probe.log",
            "logs/v-ansys-task-16-windows/exact_eval_diagnosis.log",
        ],
    },
    {
        "id": "v-ansys-task-17-windows",
        "dir": "task/task-v/ansys/task-17",
        "failure": "The original GT did not satisfy every downstream Couette check, and the evaluator also raised ValueError by truth-testing NumPy mesh arrays before a valid candidate could be scored.",
        "generation": "Fluent 2026 R1 loaded the Couette model, preserved the 1 m/s moving top and stationary bottom, configured conformal periodic left/right boundaries, laminar water, SIMPLE and second-order schemes, initialized and ran 1200 iterations, checked wall velocities/shear, then wrote a solved 2560-cell/2673-node CAS/DAT pair.",
        "files": ["eval.py", "ground_truth/couette.cas", "ground_truth/couette.dat"],
        "old_logs": [
            "logs/v-ansys-task-17-windows/audit_candidates/candidate_generation.log",
            "logs/v-ansys-task-17-windows/audit_candidates/candidate_inner_probe.log",
            "logs/v-ansys-task-17-windows/audit_candidates/exact_eval_diagnosis.log",
        ],
    },
    {
        "id": "v-quantified-ansys-structural-thermal-optimization-task-04-windows",
        "dir": "task/quantified/gui-ansys-structural-thermal-optimization/task-04",
        "failure": "The shared evaluator treated ANSYS's valid default unit thickness for PLANE55/PLANE77 as an error because RLIST,ALL reports no explicit real-constant entities.",
        "generation": "No GT regeneration was required. ANSYS Mechanical APDL 2026 R1 reopened the baseline and reference DB/RTH. The task-local wrapper accepts implicit thickness only when expected thickness is exactly 1.0, RLIST explicitly reports no entities, and mesh real-constant IDs are only 0/1; all shared geometry, load, material, connectivity, feature, and score checks remain active.",
        "files": ["eval.py"],
        "old_logs": [
            "logs/v-quantified-ansys-structural-thermal-optimization-task-04-windows/diagnosis.txt",
            "logs/v-quantified-ansys-structural-thermal-optimization-task-04-windows/rlist_probe.log",
        ],
    },
]


QUANTIFIED = {
    1: {
        "id": "v-quantified-ansys-structural-thermal-optimization-task-01-windows",
        "mode": "static",
        "score": 0.059090,
        "failure": "The existing reference DB/RST had to be replaced with a fresh licensed solve because prior attempts contained or risked MAPDL verification-only output.",
    },
    2: {
        "id": "v-quantified-ansys-structural-thermal-optimization-task-02-windows",
        "mode": "prestressed static plus linear buckling",
        "score": 0.847114,
        "failure": "The existing reference DB/RST had to be replaced with a fresh licensed solve because prior attempts contained or risked MAPDL verification-only output.",
    },
    3: {
        "id": "v-quantified-ansys-structural-thermal-optimization-task-03-windows",
        "mode": "three-mode modal",
        "score": 0.430291,
        "failure": "The existing reference DB/RST had to be replaced with a fresh licensed solve because prior attempts contained or risked MAPDL verification-only output.",
    },
    5: {
        "id": "v-quantified-ansys-structural-thermal-optimization-task-05-windows",
        "mode": "static",
        "score": 0.220819,
        "failure": "The existing reference DB/RST had to be replaced with a fresh licensed solve because prior attempts contained or risked MAPDL verification-only output.",
    },
}

for number, item in QUANTIFIED.items():
    item.update({
        "dir": f"task/quantified/gui-ansys-structural-thermal-optimization/task-{number:02d}",
        "files": [
            "ground_truth/GT_MANIFEST.json",
            "ground_truth/reference/REFERENCE_MANIFEST.json",
            "ground_truth/reference/submission.db",
            "ground_truth/reference/submission.rst",
        ],
        "generation": (
            f"Stopped only lmgrd/ansyslmd, executed the task-declared python C:\\Users\\user\\Desktop\\license.py, "
            f"confirmed new license processes, then ran ANSYS261.exe -b -p ansys for a fresh {item['mode']} solve. "
            "Saved native submission.db/submission.rst, required return code 0 and zero MAPDL errors, and the resolver "
            "rejected 'MAPDL VERIFICATION RUN ONLY' before candidate acceptance and writeback. The report-time audit "
            "scanned persisted submission.out for both that marker and 'DO NOT USE RESULTS FOR PRODUCTION'. Formal "
            "pre-clean and final cleanup removed resolver sidecars including submission.stat, submission.mode, and submission.mlv."
        ),
    })
    TASKS.append(item)


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def before_digest(relative: str) -> str:
    result = subprocess.run(
        ["git", "show", f"HEAD:{relative}"], cwd=REPO, capture_output=True, check=True
    )
    return digest_bytes(result.stdout)


def modified_file(relative: str) -> dict:
    path = REPO / relative
    before = before_digest(relative)
    after = digest(path)
    if before == after:
        raise RuntimeError(f"Expected modified file is unchanged: {relative}")
    return {
        "path": relative,
        "before_sha256": before,
        "after_sha256": after,
        "after_size_bytes": path.stat().st_size,
    }


def review_inputs(task_dir: Path, config: dict) -> dict:
    config_files = []
    for step in config.get("config", []):
        if step.get("type") == "upload_file":
            config_files.extend(item["local_path"] for item in step["parameters"].get("files", []))
    gt_files = [
        str(path.relative_to(REPO))
        for path in sorted((task_dir / "ground_truth").rglob("*"))
        if path.is_file()
    ]
    return {
        "instruction": config["instruction"],
        "task_json": str((task_dir / f"{task_dir.name}.json").relative_to(REPO)),
        "init_or_config_uploads": config_files,
        "ground_truth_files": gt_files,
        "eval_py": str((task_dir / "eval.py").relative_to(REPO)),
        "production_upload_and_result": config["evaluator"],
    }


def build_record(item: dict) -> dict:
    task_dir = REPO / item["dir"]
    config_path = task_dir / f"{task_dir.name}.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    task_id = item["id"]
    if config["id"] != task_id or config["snapshot"] != "ANSYS-2026R":
        raise RuntimeError(f"Task identity mismatch: {task_id}")

    eval_log_path = OUTPUT / "logs" / task_id / "evaluation.json"
    evaluation = json.loads(eval_log_path.read_text(encoding="utf-8"))
    if not evaluation.get("passed") or evaluation["evaluation"].get("returncode") != 0:
        raise RuntimeError(f"Formal evaluator did not pass: {task_id}")
    if evaluation["eval_sha256"] != digest(task_dir / "eval.py"):
        raise RuntimeError(f"Formal evaluator hash is stale: {task_id}")

    expected = config["evaluator"].get("expected", {}).get("rules", {}).get("expected")
    if expected is not None and evaluation["evaluation"].get("output") != expected:
        raise RuntimeError(f"Exact output mismatch: {task_id}")
    if expected is None and float(evaluation["score"]) <= float(
        config["evaluator"].get("metric", {}).get("baseline_score", 0.0)
    ):
        raise RuntimeError(f"Quantified score did not beat baseline: {task_id}")

    changed = [modified_file(f"{item['dir']}/{name}") for name in item["files"]]
    modified_paths = [entry["path"] for entry in changed]
    sha256_before_after = {
        entry["path"]: {"before": entry["before_sha256"], "after": entry["after_sha256"]}
        for entry in changed
    }
    logs = {"production_eval": str(eval_log_path.relative_to(REPO))}
    for index, path in enumerate(item.get("old_logs", []), 1):
        logs[f"diagnosis_or_generation_{index:02d}"] = str((OLD_OUTPUT / path).relative_to(REPO))
    supporting_evidence_sha256 = {}
    for index, path in enumerate(item.get("evidence_logs", []), 1):
        relative = str((OUTPUT / path).relative_to(REPO))
        logs[f"direct_probe_evidence_{index:02d}"] = relative
        supporting_evidence_sha256[relative] = digest(REPO / relative)
    solve_evidence = None
    if "mode" in item:
        resolve_dir = OUTPUT / "logs" / task_id / "license_resolve"
        resolve_log = resolve_dir / "license_resolve.json"
        output_log = resolve_dir / "submission.out"
        resolve = json.loads(resolve_log.read_text(encoding="utf-8"))
        solve_text = output_log.read_text(errors="ignore")
        upper = solve_text.upper()
        if (
            resolve.get("status") != "resolved_nonverification"
            or resolve.get("verification_marker") is not False
            or "MAPDL VERIFICATION RUN ONLY" in upper
            or "DO NOT USE RESULTS FOR PRODUCTION" in upper
            or "NUMBER OF ERROR   MESSAGES ENCOUNTERED=          0" not in upper
        ):
            raise RuntimeError(f"Fresh solve evidence is invalid: {task_id}")
        if abs(float(evaluation["score"]) - float(item["score"])) > 5.0e-7:
            raise RuntimeError(f"Unexpected score: {task_id}")
        baseline_names = sorted(entry["Name"] for entry in evaluation["desktop_before"])
        cleanup_names = sorted(entry["Name"] for entry in evaluation["desktop_after_cleanup"])
        allowed = ["__pycache__", "desktop.ini", "license.py"]
        if baseline_names != allowed or cleanup_names != allowed:
            raise RuntimeError(f"Desktop was not clean before/after formal eval: {task_id}")
        logs["fresh_solve"] = str(resolve_log.relative_to(REPO))
        logs["solver_output"] = str(output_log.relative_to(REPO))
        solve_evidence = {
            "mode": item["mode"],
            "license_launch": ["python", r"C:\Users\user\Desktop\license.py"],
            "native_command": "ANSYS261.exe -b -p ansys",
            "returncode": resolve["resolve_execution"]["returncode"],
            "zero_error_summary": True,
            "verification_marker": False,
            "production_forbidden_marker": False,
        }

    disconnect = OUTPUT / "disconnect_verification.json"
    if not disconnect.is_file():
        raise RuntimeError("Disconnect verification is missing")
    logs["disconnect"] = str(disconnect.relative_to(REPO))
    missing_logs = [path for path in logs.values() if not (REPO / path).is_file()]
    if missing_logs:
        raise RuntimeError(f"Missing report logs for {task_id}: {missing_logs}")

    cleanup_names = sorted(entry["Name"] for entry in evaluation["desktop_after_cleanup"])
    return {
        "task_id": task_id,
        "snapshot": "ANSYS-2026R",
        "instruction": config["instruction"],
        "independent_review": review_inputs(task_dir, config),
        "failure_reason": item["failure"],
        "modified_files": modified_paths,
        "sha256_before_after": sha256_before_after,
        "init_modified": False,
        "real_software_generation": item["generation"],
        "fresh_solve_evidence": solve_evidence,
        "eval_result": {
            "command": evaluation["eval_command"],
            "returncode": evaluation["evaluation"]["returncode"],
            "stdout": evaluation["evaluation"]["output"],
            "stderr": evaluation["evaluation"].get("error", ""),
            "expected": expected,
            "exact_match": evaluation["evaluation"]["output"] == expected if expected is not None else None,
            "score": evaluation["score"],
            "success_condition": expected if expected is not None else "finite score > baseline_score",
        },
        "logs": logs,
        "supporting_evidence_sha256": supporting_evidence_sha256,
        "cleanup": (
            "Stopped task ANSYS/Fluent processes and removed uploaded init, GT, evaluator, result "
            f"sidecars, logs, caches, and temporary task files. Cleanup returned {evaluation['cleanup']['returncode']}; "
            f"desktop_after_cleanup contained only {cleanup_names}. The local tunnel was then disconnected "
            "and independently verified closed without reconnecting."
        ),
        "status": "passed",
    }


def main() -> int:
    records = [build_record(item) for item in TASKS]
    report_path = OUTPUT / "report.jsonl"
    report_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n" for record in records),
        encoding="utf-8",
    )
    summary = {
        "snapshot": "ANSYS-2026R",
        "total": len(records),
        "assigned_tasks": len(records),
        "completed": len(records),
        "passed": sum(record["status"] == "passed" for record in records),
        "eval_blocked": sum(record["status"] == "eval_blocked" for record in records),
        "environment_blocked": sum(record["status"] == "environment_blocked" for record in records),
        "modified_tasks": sum(bool(record["modified_files"]) for record in records),
        "modified_files": sum(len(record["modified_files"]) for record in records),
        "status": "complete",
        "report": str(report_path.relative_to(REPO)),
    }
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
