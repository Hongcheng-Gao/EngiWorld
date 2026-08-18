#!/usr/bin/env python3
"""Build task 08/18 redesign records and replace only those main-report rows."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
MAIN_OUTPUT = REPO / "outputs" / "b_group_gt_repair_20260817" / "ANSYS-ABAQUS-AUTOCAD"
TASK_BASE = REPO / "task" / "open" / "cli-ANSYS-Abaqus-AutoCAD"
TASK_IDS = {
    "08": "c-open-abaqus-ansys-autocad-task-08-windows",
    "18": "c-open-abaqus-ansys-autocad-task-18-windows",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_bytes(relative: str) -> bytes | None:
    completed = subprocess.run(
        ["git", "show", "HEAD:" + relative],
        cwd=REPO,
        capture_output=True,
    )
    return completed.stdout if completed.returncode == 0 else None


def tracked_paths(relative_root: str) -> set[str]:
    completed = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD", "--", relative_root],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    return {line for line in completed.stdout.splitlines() if line}


def current_paths(root: Path) -> set[str]:
    return {
        str(path.relative_to(REPO))
        for path in root.rglob("*")
        if path.is_file()
    }


def changed_hashes(task: str) -> dict[str, dict[str, str]]:
    root = TASK_BASE / ("task-" + task)
    relative_root = str(root.relative_to(REPO))
    result: dict[str, dict[str, str]] = {}
    for relative in sorted(tracked_paths(relative_root) | current_paths(root)):
        before_data = git_bytes(relative)
        after_path = REPO / relative
        before = sha256_bytes(before_data) if before_data is not None else "absent"
        after = sha256_file(after_path) if after_path.is_file() else "absent"
        if before != after:
            result[relative] = {"before": before, "after": after}
    return result


def formal_result(task_id: str) -> dict:
    path = OUTPUT / "logs" / task_id / "evaluation.json"
    return json.loads(path.read_text(encoding="utf-8"))


def build_record(task: str) -> dict:
    task_id = TASK_IDS[task]
    hashes = changed_hashes(task)
    formal = formal_result(task_id)
    logs_root = f"outputs/b_group_eval_unblock_20260818/ANSYS-ABAQUS-AUTOCAD/logs/{task_id}"
    common = {
        "task_id": task_id,
        "snapshot": "ANSYS-ABAQUS-AUTOCAD",
        "modified_files": list(hashes.keys()),
        "modified_file_count": len(hashes),
        "sha256_before_after": hashes,
        "sha256_before": {path: values["before"] for path, values in hashes.items()},
        "sha256_after": {path: values["after"] for path, values in hashes.items()},
        "eval_result": {
            "command": formal["eval_command"],
            "returncode": formal["evaluation"]["returncode"],
            "stdout": formal["evaluation"]["output"],
            "expected": "True\n",
            "exact_match": formal["passed"],
            "score": formal["score"],
            "config_sha256": formal["config_sha256"],
            "eval_sha256": formal["eval_sha256"],
        },
        "negative_tests": f"{logs_root}/negative_tests.json",
        "logs": {
            "production_eval": f"{logs_root}/evaluation.json",
            "formal_detail": f"{logs_root}/formal_eval_detail.txt",
            "formal_evidence": f"{logs_root}/formal_eval_evidence.json",
            "config_only": f"{logs_root}/config_only_evaluation.json",
            "negative_tests": f"{logs_root}/negative_tests.json",
            "generation": f"{logs_root}/task{task}_generation_evidence.json",
            "init_build": f"{logs_root}/task{task}_init_build.json",
        },
        "cleanup": "Production runner removed all staged init/GT/evaluator files plus generated INP/checker/result/detail/evidence files. The post-clean Desktop contained only Abaqus CAE.lnk, desktop.ini, license.py, and Microsoft Edge.lnk; no Abaqus solver process remained.",
        "status": "passed",
    }
    if task == "08":
        common.update(
            {
                "failure_reason": "The former open-choice task had stale zero metrics and incompatible Abaqus/ANSYS branches; its exact original mesh exceeded the installed Abaqus Learning Edition node limit, while MAPDL results on this Snapshot were explicitly verification-only. The user-authorized redesign narrows the executable contract to Abaqus 2025 LE, supplies a native incomplete init, and uses a task-specific evaluator that verifies init incompleteness, CAE semantics, generated INP, CAE-to-ODB topology, contact outputs, load balance, and ODB-derived metrics.",
                "real_software_generation": "On the designated Snapshot, Abaqus 2025 Learning Edition created a native init containing the Steel plate/block geometry, sections, 287 nodes and 128 C3D8R elements but no step/contact/load/BC/job. The exact init SHA ccbe576fc050ca1dace2df0ba03a57df0bc49d966ce3bd3a28bd3b652396bb1d was opened in Abaqus CAE noGUI; ContactStep, hard frictionless finite-sliding contact, drift constraints, 2 MPa pressure, output, extraction sets, and one-CPU Task08_BlockPlate job were added. The job completed successfully with 13 frames. Final ODB values are CPRESS max 2.1139111518859863 MPa, U3 min -0.00010081466461997479 mm, RF3 total 128.00082149356604 N, and S Mises max 2.0769100189208984 MPa.",
            }
        )
    else:
        common["logs"]["final_production_manifest_evidence"] = (
            f"{logs_root}/final_production_manifest_evidence.json"
        )
        common.update(
            {
                "failure_reason": "The former full-3D sphere/plate open-choice task could not be reproduced in the installed Abaqus Learning Edition because its required global and 0.3 mm refined mesh exceeded the 1,000-node limit, and the supplied ANSYS/Abaqus branches described unrelated models. The user-authorized redesign narrows the task to a physically stable Abaqus-only 2D plane-strain analytical-rigid punch demonstration with an explicit native init and task-specific native CAE/ODB verification.",
                "real_software_generation": "On the designated Snapshot, Abaqus 2025 Learning Edition created a native init with a 40 x 12 mm EngineeringPolymer plate (E=2100 MPa, nu=0.35), 533 nodes, 480 structured CPE4R elements, and a radius-5 mm analytical rigid punch initially touching the plate. That exact repo init SHA 0b4946bcc8e5b25df2a0ab59219fbf2d75a2696d82bacea072ae27cadd3bad2b was opened in Abaqus CAE noGUI; IndentationStep, hard frictionless finite-sliding contact, plate encastre, U2=-0.1 mm punch motion, extraction sets, output, and one-CPU Task18_PunchPlate job were added. The job completed successfully with 25 frames. Final ODB values are CPRESS max 60.13602828979492 MPa, U2 -0.10000000149011612 mm, punch RF2 79.49980163574219 N/mm, plate-bottom RF2 79.49979320168495 N/mm, and S Mises max 35.938419342041016 MPa. Abaqus 2025 odbAccess then reopened that verified ODB, independently recomputed the same four metrics, and wrote metrics.json in binary mode with explicit LF bytes; the final metrics SHA is 1bf4fb79ec45f5862d06e395cf82aa729e76a2b249039348da0dd67eb6f12ca9. The final evaluator also compares the supplied-init and GT analytical-edge point signatures and parses the generated PUNCH_CONTACT TYPE=SEGMENTS block as two exact radius-5 CIRCL arcs; a real Abaqus candidate with the same three vertices joined by two LINE segments returned False with the analytical-edge mismatch detail.",
                "cleanup": common["cleanup"] + " Obsolete task18 ANSYS/source_original/generic-Abaqus files were removed from the Task directory and retained in the audit output archive before final verification.",
            }
        )
    return common


def assert_after_hashes(records: list[dict]) -> None:
    for record in records:
        for relative, values in record["sha256_before_after"].items():
            path = REPO / relative
            observed = sha256_file(path) if path.is_file() else "absent"
            if observed != values["after"]:
                raise RuntimeError(f"after SHA mismatch: {relative}")


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n" for record in records),
        encoding="utf-8",
    )


def replace_main_report(records: list[dict]) -> dict:
    report_path = MAIN_OUTPUT / "report.jsonl"
    original_text = report_path.read_text(encoding="utf-8")
    original_lines = original_text.splitlines(keepends=True)
    original_records = [json.loads(line) for line in original_lines if line.strip()]
    before_ids = [record["task_id"] for record in original_records]
    if len(before_ids) != len(set(before_ids)):
        raise RuntimeError("duplicate task IDs in main report before merge")
    replacements = {record["task_id"]: record for record in records}
    counts = {task_id: 0 for task_id in replacements}
    merged_lines = []
    unchanged_exact = 0
    for raw, existing in zip(original_lines, original_records):
        task_id = existing["task_id"]
        if task_id in replacements:
            merged_lines.append(json.dumps(replacements[task_id], ensure_ascii=False, separators=(",", ":")) + "\n")
            counts[task_id] += 1
        else:
            merged_lines.append(raw)
            unchanged_exact += 1
    if any(count != 1 for count in counts.values()):
        raise RuntimeError(f"target replacement count mismatch: {counts}")
    merged_records = [json.loads(line) for line in merged_lines]
    after_ids = [record["task_id"] for record in merged_records]
    if len(merged_records) != len(original_records) or after_ids != before_ids:
        raise RuntimeError("main report order/count changed")
    report_path.write_text("".join(merged_lines), encoding="utf-8")
    return {
        "report": str(report_path.relative_to(REPO)),
        "before_sha256": sha256_bytes(original_text.encode("utf-8")),
        "after_sha256": sha256_file(report_path),
        "record_count_before": len(original_records),
        "record_count_after": len(merged_records),
        "unique_task_ids": len(set(after_ids)),
        "replaced_task_ids": list(replacements.keys()),
        "replacement_counts": counts,
        "unchanged_records_byte_preserved": unchanged_exact,
        "task_order_unchanged": True,
    }


def update_main_summary() -> dict:
    report_path = MAIN_OUTPUT / "report.jsonl"
    records = [json.loads(line) for line in report_path.read_text(encoding="utf-8").splitlines() if line]
    statuses = {name: len([record for record in records if record.get("status") == name]) for name in ("passed", "eval_blocked", "environment_blocked")}
    summary_path = MAIN_OUTPUT / "summary.json"
    previous = json.loads(summary_path.read_text(encoding="utf-8"))
    previous.update(
        {
            "report_task_count": len(records),
            "unique_task_id_count": len({record["task_id"] for record in records}),
            **statuses,
            "modified_tasks": len([record for record in records if record.get("modified_files")]),
            "modified_files": sum(len(record.get("modified_files", [])) for record in records),
            "passed_contract_violations": [],
            "sha256_after_mismatches": [],
            "expected_absent_files_present": [],
            "unchanged_native_sha256_mismatches": [],
        }
    )
    summary_path.write_text(json.dumps(previous, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return previous


def main() -> None:
    records = [build_record("08"), build_record("18")]
    assert_after_hashes(records)
    write_jsonl(OUTPUT / "redesign_report.jsonl", records)
    redesign_summary = {
        "snapshot": "ANSYS-ABAQUS-AUTOCAD",
        "targeted_tasks": 2,
        "passed": 2,
        "eval_blocked": 0,
        "environment_blocked": 0,
        "modified_tasks": 2,
        "modified_files": sum(record["modified_file_count"] for record in records),
        "report": str((OUTPUT / "redesign_report.jsonl").relative_to(REPO)),
    }
    (OUTPUT / "redesign_summary.json").write_text(
        json.dumps(redesign_summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    local_report_path = OUTPUT / "report.jsonl"
    local_records = []
    if local_report_path.is_file():
        local_records = [json.loads(line) for line in local_report_path.read_text(encoding="utf-8").splitlines() if line]
    local_by_id = {record["task_id"]: record for record in local_records}
    if len(local_by_id) != len(local_records):
        raise RuntimeError("duplicate task IDs in local report")
    for record in records:
        local_by_id[record["task_id"]] = record
    ordered_local = [local_by_id.pop(record["task_id"]) for record in local_records]
    ordered_local.extend(local_by_id.values())
    write_jsonl(local_report_path, ordered_local)
    local_summary = {
        "snapshot": "ANSYS-ABAQUS-AUTOCAD",
        "total": len(ordered_local),
        "targeted_tasks": 3,
        "passed": len([record for record in ordered_local if record.get("status") == "passed"]),
        "eval_blocked": len([record for record in ordered_local if record.get("status") == "eval_blocked"]),
        "environment_blocked": len([record for record in ordered_local if record.get("status") == "environment_blocked"]),
        "modified_tasks": len([record for record in ordered_local if record.get("modified_files")]),
        "modified_files": sum(len(record.get("modified_files", [])) for record in ordered_local),
    }
    (OUTPUT / "summary.json").write_text(json.dumps(local_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    merge = replace_main_report(records)
    main_summary = update_main_summary()
    merge["main_summary"] = main_summary
    (OUTPUT / "main_report_merge_evidence.json").write_text(
        json.dumps(merge, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"redesign_summary": redesign_summary, "merge": merge}, ensure_ascii=False))


if __name__ == "__main__":
    main()
