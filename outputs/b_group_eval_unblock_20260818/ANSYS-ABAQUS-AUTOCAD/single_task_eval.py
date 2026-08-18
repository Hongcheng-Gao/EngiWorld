#!/usr/bin/env python3
"""Production-style staging for redesigned c-open Abaqus tasks 08 and 18."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath


REPO = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
TASK_ROOT = REPO / "task" / "open" / "cli-ANSYS-Abaqus-AutoCAD"
REMOTE_DESKTOP = PureWindowsPath(r"C:\Users\user\Desktop")
KEEP_REMOTE = {
    "abaqus cae.lnk",
    "desktop.ini",
    "license.py",
    "microsoft edge.lnk",
    "__pycache__",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Remote:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def execute(self, command: list[str] | str, *, shell: bool = False) -> dict:
        request = urllib.request.Request(
            self.base_url + "/execute",
            data=json.dumps({"command": command, "shell": shell}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=900) as response:
            return json.loads(response.read().decode("utf-8"))

    def upload(self, local_path: Path, remote_path: str) -> dict:
        completed = subprocess.run(
            [
                "curl",
                "--fail",
                "--silent",
                "--show-error",
                "--max-time",
                "900",
                "-X",
                "POST",
                self.base_url + "/setup/upload",
                "-F",
                f"file_path={remote_path}",
                "-F",
                f"file_data=@{local_path}",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=910,
        )
        return {
            "local_path": str(local_path),
            "remote_path": remote_path,
            "size": local_path.stat().st_size,
            "sha256": sha256(local_path),
            "response": completed.stdout,
        }

    def download(self, remote_path: str, local_path: Path) -> bool:
        completed = subprocess.run(
            [
                "curl",
                "--fail",
                "--silent",
                "--show-error",
                "--max-time",
                "900",
                "-X",
                "POST",
                self.base_url + "/file",
                "-F",
                f"file_path={remote_path}",
                "-o",
                str(local_path),
            ],
            capture_output=True,
            text=True,
            timeout=910,
        )
        return completed.returncode == 0 and local_path.is_file()

    def desktop_entries(self) -> list[dict]:
        result = self.execute(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                r"Get-ChildItem -LiteralPath C:\Users\user\Desktop -Force | "
                r"Select-Object Name,Length | ConvertTo-Json -Compress",
            ]
        )
        raw = result.get("output", "").strip()
        if not raw:
            return []
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else [parsed]

    def remove_names(self, names: set[str]) -> dict:
        paths = [str(REMOTE_DESKTOP / name) for name in sorted(names) if name.lower() not in KEEP_REMOTE]
        quoted = ",".join(json.dumps(path) for path in paths)
        script = (
            "Stop-Process -Name abq2025le,ABQLauncher,SMAPcae,standard,pre -Force "
            "-ErrorAction SilentlyContinue; "
            f"$paths=@({quoted}); "
            "if ($paths.Count -gt 0) { Remove-Item -LiteralPath $paths -Recurse -Force "
            "-ErrorAction SilentlyContinue }; "
            r"Get-ChildItem -LiteralPath C:\Users\user\Desktop -Force | "
            "Select-Object Name,Length | ConvertTo-Json -Compress"
        )
        return self.execute(["powershell", "-NoProfile", "-Command", script])

    def remote_sha256(self, remote_path: str) -> str:
        script = (
            f"(Get-FileHash -Algorithm SHA256 -LiteralPath {json.dumps(remote_path)}).Hash"
        )
        result = self.execute(["powershell", "-NoProfile", "-Command", script])
        if result.get("returncode") != 0:
            raise RuntimeError(result)
        return result.get("output", "").strip().lower()


def upload_steps(remote: Remote, steps: list[dict]) -> tuple[list[dict], set[str]]:
    records = []
    paths = set()
    for step in steps:
        if step.get("type") != "upload_file":
            continue
        for item in step.get("parameters", {}).get("files", []):
            local = Path(item["local_path"])
            if not local.is_absolute():
                local = TASK_ROOT / local
            records.append(remote.upload(local, item["path"]))
            paths.add(item["path"])
    return records, paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=("08", "18"), required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:15066")
    args = parser.parse_args()

    task_dir = TASK_ROOT / ("task-" + args.task)
    config_path = task_dir / ("task-" + args.task + ".json")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config["snapshot"] != "ANSYS-ABAQUS-AUTOCAD":
        raise SystemExit("snapshot mismatch")
    task_id = config["id"]
    log_dir = OUTPUT / "logs" / task_id
    log_dir.mkdir(parents=True, exist_ok=True)
    remote = Remote(args.base_url)
    record = {
        "task_id": task_id,
        "snapshot": config["snapshot"],
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path),
        "config_sha256": sha256(config_path),
        "eval_path": str(task_dir / "eval.py"),
        "eval_sha256": sha256(task_dir / "eval.py"),
    }
    staged_paths: set[str] = set()

    initial_entries = remote.desktop_entries()
    initial_names = {item["Name"] for item in initial_entries}
    record["preclean_initial"] = initial_entries
    record["preclean"] = remote.remove_names(
        {name for name in initial_names if name.lower() not in KEEP_REMOTE}
    )
    baseline = remote.desktop_entries()
    baseline_names = {item["Name"] for item in baseline}
    record["desktop_before"] = baseline

    try:
        config_uploads, config_paths = upload_steps(remote, config.get("config", []))
        staged_paths.update(config_paths)
        record["config_uploads"] = config_uploads
        record["config_remote_sha256"] = {
            item["remote_path"]: remote.remote_sha256(item["remote_path"])
            for item in config_uploads
        }
        for item in config_uploads:
            if record["config_remote_sha256"][item["remote_path"]] != item["sha256"]:
                raise RuntimeError("remote init hash mismatch")

        gt_uploads = []
        gt_dir = task_dir / "ground_truth" / "abaqus"
        for local in sorted(path for path in gt_dir.iterdir() if path.is_file()):
            remote_path = str(REMOTE_DESKTOP / local.name)
            gt_uploads.append(remote.upload(local, remote_path))
            staged_paths.add(remote_path)
        record["gt_uploads"] = gt_uploads

        post_uploads, post_paths = upload_steps(
            remote, config.get("evaluator", {}).get("postconfig", [])
        )
        staged_paths.update(post_paths)
        record["postconfig_uploads"] = post_uploads

        result_spec = config["evaluator"]["result"]
        evaluation = remote.execute(
            result_spec["command"], shell=str(result_spec.get("shell", "false")).lower() == "true"
        )
        expected = config["evaluator"]["expected"]["rules"]["expected"]
        record["eval_command"] = result_spec["command"]
        record["evaluation"] = evaluation
        record["passed"] = evaluation.get("returncode") == 0 and evaluation.get("output") == expected
        record["score"] = 1.0 if record["passed"] else 0.0

        for remote_name, local_name in (
            (f"__task{args.task}_abaqus_detail.txt", "formal_eval_detail.txt"),
            (f"__task{args.task}_abaqus_evidence.json", "formal_eval_evidence.json"),
        ):
            local = log_dir / local_name
            if remote.download(str(REMOTE_DESKTOP / remote_name), local):
                record.setdefault("downloaded_eval_evidence", {})[local_name] = {
                    "path": str(local),
                    "sha256": sha256(local),
                }
    except Exception as exc:
        record["passed"] = False
        record["runner_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        after_eval = remote.desktop_entries()
        record["desktop_after_eval"] = after_eval
        created_names = {item["Name"] for item in after_eval} - baseline_names
        record["cleanup"] = remote.remove_names(created_names | {
            PureWindowsPath(path).name for path in staged_paths
        })
        record["desktop_after_cleanup"] = remote.desktop_entries()
        record["finished_utc"] = datetime.now(timezone.utc).isoformat()
        log_path = log_dir / "evaluation.json"
        log_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"task_id": task_id, "passed": record.get("passed"), "log": str(log_path)}, ensure_ascii=False))

    return 0 if record.get("passed") else 1


if __name__ == "__main__":
    sys.exit(main())
