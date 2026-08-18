#!/usr/bin/env python3
"""Run one isolated negative evaluation case on the real snapshot."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath

from single_task_eval import KEEP_REMOTE, OUTPUT, TASK_ROOT, Remote, sha256, upload_steps


REMOTE_DESKTOP = PureWindowsPath(r"C:\Users\user\Desktop")
ABAQUS = r"C:\SIMULIA\Commands\abaqus.bat"
ARTIFACTS = {
    "08": {
        "cae": "Task08_BlockPlate_GT.cae",
        "odb": "Task08_BlockPlate.odb",
        "metrics": "metrics.json",
        "detail": "__task08_abaqus_detail.txt",
        "mutations": {
            "wrong_pressure": "mutate_task08_pressure.py",
            "extra_guide_bc": "mutate_task08_extra_bc.py",
        },
    },
    "18": {
        "cae": "Task18_PunchPlate_GT.cae",
        "odb": "Task18_PunchPlate.odb",
        "metrics": "metrics.json",
        "detail": "__task18_abaqus_detail.txt",
        "mutations": {
            "wrong_displacement": "mutate_task18_displacement.py",
            "no_separation": "mutate_task18_no_separation.py",
            "v_punch": "build_task18_v_punch_candidate.py",
        },
    },
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=("08", "18"), required=True)
    parser.add_argument(
        "--case",
        choices=(
            "init_as_candidate",
            "missing_odb",
            "wrong_pressure",
            "extra_guide_bc",
            "wrong_displacement",
            "no_separation",
            "v_punch",
        ),
        required=True,
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:15066")
    args = parser.parse_args()

    artifact = ARTIFACTS[args.task]
    if args.case not in ("init_as_candidate", "missing_odb") and args.case not in artifact["mutations"]:
        raise SystemExit("case does not apply to selected task")
    task_dir = TASK_ROOT / ("task-" + args.task)
    config_path = task_dir / ("task-" + args.task + ".json")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    task_id = config["id"]
    log_dir = OUTPUT / "logs" / task_id
    gt_dir = task_dir / "ground_truth" / "abaqus"
    log_path = log_dir / (args.case + "_evaluation.json")
    remote = Remote(args.base_url)
    record = {
        "case": args.case,
        "task_id": task_id,
        "snapshot": config["snapshot"],
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "config_sha256": sha256(config_path),
        "eval_sha256": sha256(task_dir / "eval.py"),
    }
    staged_paths: set[str] = set()
    initial = remote.desktop_entries()
    record["preclean_initial"] = initial
    record["preclean"] = remote.remove_names(
        {item["Name"] for item in initial if item["Name"].lower() not in KEEP_REMOTE}
    )
    baseline = remote.desktop_entries()
    baseline_names = {item["Name"] for item in baseline}
    record["desktop_before"] = baseline

    try:
        config_uploads, config_paths = upload_steps(remote, config.get("config", []))
        staged_paths.update(config_paths)
        record["config_uploads"] = config_uploads
        init_path = Path(config_uploads[0]["local_path"])
        candidate_local = init_path if args.case == "init_as_candidate" else gt_dir / artifact["cae"]
        candidate_remote = str(REMOTE_DESKTOP / artifact["cae"])
        record["candidate_upload"] = remote.upload(candidate_local, candidate_remote)
        staged_paths.add(candidate_remote)

        if args.case != "missing_odb":
            odb_remote = str(REMOTE_DESKTOP / artifact["odb"])
            record["odb_upload"] = remote.upload(gt_dir / artifact["odb"], odb_remote)
            staged_paths.add(odb_remote)
        metrics_remote = str(REMOTE_DESKTOP / artifact["metrics"])
        record["metrics_upload"] = remote.upload(gt_dir / artifact["metrics"], metrics_remote)
        staged_paths.add(metrics_remote)

        mutation_name = artifact["mutations"].get(args.case)
        if mutation_name:
            mutation_local = log_dir / mutation_name
            mutation_remote = str(REMOTE_DESKTOP / mutation_name)
            record["mutation_upload"] = remote.upload(mutation_local, mutation_remote)
            staged_paths.add(mutation_remote)
            mutation = remote.execute([ABAQUS, "cae", "noGUI=" + mutation_remote])
            record["mutation"] = mutation
            if mutation.get("returncode") != 0:
                raise RuntimeError("real Abaqus mutation failed")

        post_uploads, post_paths = upload_steps(
            remote, config.get("evaluator", {}).get("postconfig", [])
        )
        staged_paths.update(post_paths)
        record["postconfig_uploads"] = post_uploads
        result_spec = config["evaluator"]["result"]
        evaluation = remote.execute(
            result_spec["command"],
            shell=str(result_spec.get("shell", "false")).lower() == "true",
        )
        record["eval_command"] = result_spec["command"]
        record["evaluation"] = evaluation
        record["passed_negative"] = (
            evaluation.get("returncode") == 0 and evaluation.get("output") == "False\n"
        )
        detail_local = log_dir / (args.case + "_eval_detail.txt")
        if remote.download(str(REMOTE_DESKTOP / artifact["detail"]), detail_local):
            record["detail_log"] = str(detail_local)
            record["detail_sha256"] = sha256(detail_local)
    except Exception as exc:
        record["passed_negative"] = False
        record["runner_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        after_eval = remote.desktop_entries()
        record["desktop_after_eval"] = after_eval
        created_names = {item["Name"] for item in after_eval} - baseline_names
        record["cleanup"] = remote.remove_names(
            created_names | {PureWindowsPath(path).name for path in staged_paths}
        )
        record["desktop_after_cleanup"] = remote.desktop_entries()
        record["finished_utc"] = datetime.now(timezone.utc).isoformat()
        log_path.write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({
            "task_id": task_id,
            "case": args.case,
            "passed_negative": record.get("passed_negative"),
            "log": str(log_path),
        }, ensure_ascii=False))

    return 0 if record.get("passed_negative") else 1


if __name__ == "__main__":
    sys.exit(main())
