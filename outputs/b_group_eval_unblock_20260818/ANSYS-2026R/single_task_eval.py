#!/usr/bin/env python3
"""Stage, evaluate, and clean exactly one assigned ANSYS-2026R task."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath


REPO = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
REMOTE_DESKTOP = PureWindowsPath(r"C:\Users\user\Desktop")
BASE_URL = "http://127.0.0.1:15046"
KEEP_REMOTE = {"desktop.ini", "license.py", "__pycache__"}

TASKS = {
    "c15": (REPO / "task/task-c/ansys/task-15", REPO / "task/task-c/ansys", "ground_truth"),
    **{
        f"v{number:02d}": (
            REPO / f"task/task-v/ansys/task-{number:02d}",
            REPO / "task/task-v/ansys",
            "ground_truth",
        )
        for number in (4, 5, 6, 8, 9, 10, 14, 15, 16, 17)
    },
    **{
        f"q{number:02d}": (
            REPO / f"task/quantified/gui-ansys-structural-thermal-optimization/task-{number:02d}",
            REPO / "task/quantified/gui-ansys-structural-thermal-optimization",
            "ground_truth/reference",
        )
        for number in (1, 2, 3, 4, 5)
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Remote:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def execute(self, command: list[str] | str, *, shell: bool = False) -> dict:
        request = urllib.request.Request(
            f"{self.base_url}/execute",
            data=json.dumps({"command": command, "shell": shell}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=900) as response:
            return json.loads(response.read().decode("utf-8"))

    def upload(self, local_path: Path, remote_path: str) -> dict:
        result = subprocess.run(
            [
                "curl", "-fsS", "--max-time", "900",
                "-F", f"file_path={remote_path}",
                "-F", f"file_data=@{local_path}",
                f"{self.base_url}/setup/upload",
            ],
            capture_output=True,
            text=True,
            timeout=910,
            check=True,
        )
        return {
            "local_path": str(local_path),
            "remote_path": remote_path,
            "size": local_path.stat().st_size,
            "sha256": sha256(local_path),
            "response": result.stdout,
        }

    def launch(self, command: list[str] | str, *, shell: bool = False) -> dict:
        request = urllib.request.Request(
            f"{self.base_url}/setup/launch",
            data=json.dumps({"command": command, "shell": shell}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            response_text = response.read().decode("utf-8")
        return {"command": command, "shell": shell, "response": response_text}

    def desktop_entries(self) -> list[dict]:
        result = self.execute([
            "powershell", "-NoProfile", "-Command",
            r"Get-ChildItem -LiteralPath C:\Users\user\Desktop -Force | "
            r"Select-Object Name,Length | ConvertTo-Json -Compress",
        ])
        raw = result.get("output", "").strip()
        if not raw:
            return []
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else [parsed]

    def stop_task_processes(self, *, stop_license: bool) -> dict:
        names = "ANSYS,ANSYS261,fluent,fluent_mpi.26.1.0,fluent_mpi.26.1.0_node"
        if stop_license:
            names += ",lmgrd,ansyslmd"
        return self.execute([
            "powershell", "-NoProfile", "-Command",
            f"Stop-Process -Name {names} -Force -ErrorAction SilentlyContinue; "
            "Start-Sleep -Seconds 3",
        ])

    def license_processes(self) -> dict:
        return {
            name: self.execute(["tasklist", "/FI", f"IMAGENAME eq {name}", "/FO", "CSV"])
            for name in ("lmgrd.exe", "ansyslmd.exe")
        }

    def cleanup(self, remote_paths: set[str], created_names: set[str]) -> dict:
        names = {
            PureWindowsPath(path).name
            for path in remote_paths
            if PureWindowsPath(path).name.lower() not in KEEP_REMOTE
        }
        names.update(name for name in created_names if name.lower() not in KEEP_REMOTE)
        names.update({"submission.mode", "submission.stat", "submission.mlv"})
        paths = [str(REMOTE_DESKTOP / name) for name in sorted(names)]
        quoted = ",".join(json.dumps(path) for path in paths)
        command = (
            "Stop-Process -Name ANSYS,ANSYS261,fluent,fluent_mpi.26.1.0,"
            "fluent_mpi.26.1.0_node -Force -ErrorAction SilentlyContinue; "
            "Start-Sleep -Seconds 3; "
            f"$paths=@({quoted}); "
            "if ($paths.Count -gt 0) { Remove-Item -LiteralPath $paths -Recurse -Force "
            "-ErrorAction SilentlyContinue }; "
            r"Get-ChildItem -LiteralPath C:\Users\user\Desktop -Force | "
            "Select-Object Name,Length | ConvertTo-Json -Compress"
        )
        return self.execute(["powershell", "-NoProfile", "-Command", command])


def upload_steps(
    remote: Remote, steps: list[dict], asset_root: Path
) -> tuple[list[dict], set[str]]:
    records: list[dict] = []
    paths: set[str] = set()
    for step in steps:
        if step.get("type") != "upload_file":
            continue
        for spec in step.get("parameters", {}).get("files", []):
            local_path = Path(spec["local_path"])
            if not local_path.is_absolute():
                local_path = asset_root / local_path
            remote_path = spec["path"]
            records.append(remote.upload(local_path, remote_path))
            paths.add(remote_path)
    return records, paths


def launch_steps(remote: Remote, steps: list[dict]) -> list[dict]:
    records = []
    for step in steps:
        if step.get("type") != "launch":
            continue
        params = step.get("parameters", {})
        records.append(remote.launch(params["command"], shell=bool(params.get("shell", False))))
    return records


def check_result(config: dict, evaluation: dict) -> tuple[bool, float | None]:
    if evaluation.get("returncode") != 0:
        return False, None
    evaluator = config["evaluator"]
    output = evaluation.get("output", "")
    expected = evaluator.get("expected", {}).get("rules", {}).get("expected")
    if expected is not None:
        passed = output == expected
        return passed, 1.0 if passed else 0.0
    try:
        score = float(output.strip())
    except ValueError:
        return False, None
    baseline = float(evaluator.get("metric", {}).get("baseline_score", 0.0))
    return math.isfinite(score) and score > baseline, score


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=sorted(TASKS), required=True)
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--gt-dir", type=Path)
    args = parser.parse_args()

    task_dir, asset_root, gt_subdir = TASKS[args.task]
    config_path = task_dir / f"{task_dir.name}.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("snapshot") != "ANSYS-2026R":
        raise SystemExit("Refusing to operate on a different snapshot.")

    task_id = config["id"]
    log_dir = OUTPUT / "logs" / task_id
    log_dir.mkdir(parents=True, exist_ok=True)
    remote = Remote(args.base_url)
    record: dict = {
        "task_id": task_id,
        "snapshot": config["snapshot"],
        "instruction": config["instruction"],
        "config_path": str(config_path),
        "config_sha256": sha256(config_path),
        "eval_path": str(task_dir / "eval.py"),
        "eval_sha256": sha256(task_dir / "eval.py"),
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "gt_subdir": gt_subdir,
    }
    staged_paths: set[str] = set()
    before_preclean = remote.desktop_entries()
    record["desktop_before_preclean"] = before_preclean
    record["preclean"] = remote.cleanup(
        set(), {item["Name"] for item in before_preclean if item["Name"].lower() not in KEEP_REMOTE}
    )
    before = remote.desktop_entries()
    before_names = {item["Name"] for item in before}
    record["desktop_before"] = before

    try:
        record["pre_task_process_stop"] = remote.stop_task_processes(stop_license=True)
        config_uploads, config_paths = upload_steps(remote, config.get("config", []), asset_root)
        staged_paths.update(config_paths)
        record["config_uploads"] = config_uploads
        record["config_launches"] = launch_steps(remote, config.get("config", []))
        time.sleep(22)
        record["license_processes_after_launch"] = remote.license_processes()

        gt_root = args.gt_dir.resolve() if args.gt_dir else task_dir / gt_subdir
        record["gt_source"] = str(gt_root)
        gt_uploads = []
        for path in sorted(item for item in gt_root.rglob("*") if item.is_file()):
            remote_path = str(REMOTE_DESKTOP / path.relative_to(gt_root).name)
            gt_uploads.append(remote.upload(path, remote_path))
            staged_paths.add(remote_path)
        record["gt_uploads"] = gt_uploads

        post_uploads, post_paths = upload_steps(
            remote, config.get("evaluator", {}).get("postconfig", []), asset_root
        )
        staged_paths.update(post_paths)
        record["postconfig_uploads"] = post_uploads

        result_spec = config["evaluator"]["result"]
        evaluation = remote.execute(
            result_spec["command"], shell=bool(result_spec.get("shell", False))
        )
        record["eval_command"] = result_spec["command"]
        record["evaluation"] = evaluation
        passed, score = check_result(config, evaluation)
        record["score"] = score
        record["passed"] = passed
    except Exception as exc:
        record["passed"] = False
        record["runner_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        after = remote.desktop_entries()
        after_names = {item["Name"] for item in after}
        record["desktop_after_eval"] = after
        record["cleanup"] = remote.cleanup(staged_paths, after_names - before_names)
        record["desktop_after_cleanup"] = remote.desktop_entries()
        record["finished_utc"] = datetime.now(timezone.utc).isoformat()
        log_path = log_dir / "evaluation.json"
        log_path.write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(json.dumps({
            "task_id": task_id,
            "passed": record.get("passed", False),
            "score": record.get("score"),
            "log": str(log_path),
            "runner_error": record.get("runner_error"),
        }, ensure_ascii=False))

    return 0 if record.get("passed") else 1


if __name__ == "__main__":
    sys.exit(main())
