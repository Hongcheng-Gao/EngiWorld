#!/usr/bin/env python3
"""Run the production config and postconfig without staging any ground truth."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import PureWindowsPath

from single_task_eval import KEEP_REMOTE, OUTPUT, TASK_ROOT, Remote, sha256, upload_steps


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=("08", "18"), required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:15066")
    args = parser.parse_args()

    task_dir = TASK_ROOT / ("task-" + args.task)
    config_path = task_dir / ("task-" + args.task + ".json")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    log_dir = OUTPUT / "logs" / config["id"]
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "config_only_evaluation.json"
    remote = Remote(args.base_url)
    record = {
        "test": "production_config_only",
        "task_id": config["id"],
        "snapshot": config["snapshot"],
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "config_sha256": sha256(config_path),
        "eval_sha256": sha256(task_dir / "eval.py"),
        "ground_truth_uploaded": False,
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
        post_uploads, post_paths = upload_steps(
            remote, config.get("evaluator", {}).get("postconfig", [])
        )
        staged_paths.update(config_paths)
        staged_paths.update(post_paths)
        record["config_uploads"] = config_uploads
        record["postconfig_uploads"] = post_uploads
        record["remote_sha256"] = {
            item["remote_path"]: remote.remote_sha256(item["remote_path"])
            for item in config_uploads + post_uploads
        }
        for item in config_uploads + post_uploads:
            if record["remote_sha256"][item["remote_path"]] != item["sha256"]:
                raise RuntimeError("remote staging hash mismatch")
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
        print(
            json.dumps(
                {
                    "task_id": config["id"],
                    "passed_negative": record.get("passed_negative"),
                    "log": str(log_path),
                },
                ensure_ascii=False,
            )
        )

    return 0 if record.get("passed_negative") else 1


if __name__ == "__main__":
    sys.exit(main())
