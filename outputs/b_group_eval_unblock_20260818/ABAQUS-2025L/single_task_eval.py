#!/usr/bin/env python3
"""Stage, evaluate, and clean exactly one ABAQUS-2025L task."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath


REPO = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
TASK_ROOT = REPO / "task" / "task-v" / "abaqus"
REMOTE_DESKTOP = PureWindowsPath(r"C:\Users\user\Desktop")
KEEP_REMOTE = {"desktop.ini", "license.py", "__pycache__"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--number", required=True, type=int)
    parser.add_argument("--base-url", default="http://127.0.0.1:15233")
    return parser.parse_args()


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
        payload = json.dumps({"command": command, "shell": shell}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/execute",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=900) as response:
            return json.loads(response.read().decode("utf-8"))

    def upload(self, local_path: Path, remote_path: str) -> dict:
        result = subprocess.run(
            [
                "curl",
                "-sS",
                "--max-time",
                "900",
                "-F",
                f"file_path={remote_path}",
                "-F",
                f"file_data=@{local_path}",
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
        payload = json.dumps({"command": command, "shell": shell}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/setup/launch",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            response_text = response.read().decode("utf-8")
        return {"command": command, "shell": shell, "response": response_text}

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

    def cleanup(self, remote_paths: set[str], created_names: set[str]) -> dict:
        names = {
            PureWindowsPath(path).name
            for path in remote_paths
            if PureWindowsPath(path).name.lower() not in KEEP_REMOTE
        }
        names.update(name for name in created_names if name.lower() not in KEEP_REMOTE)
        paths = [str(REMOTE_DESKTOP / name) for name in sorted(names)]
        quoted = ",".join(json.dumps(path) for path in paths)
        script = (
            "Stop-Process -Name abq2025le,ABQLauncher,SMAPcae,standard,pre -Force "
            "-ErrorAction SilentlyContinue; Start-Sleep -Seconds 2; "
            f"$paths=@({quoted}); "
            "if ($paths.Count -gt 0) { Remove-Item -LiteralPath $paths -Recurse -Force "
            "-ErrorAction SilentlyContinue }; "
            r"Get-ChildItem -LiteralPath C:\Users\user\Desktop -Force | "
            "Select-Object Name,Length | ConvertTo-Json -Compress"
        )
        return self.execute(["powershell", "-NoProfile", "-Command", script])


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


def main() -> int:
    args = parse_args()
    if args.number not in set(range(1, 14)) | {16, 17, 19, 20}:
        raise SystemExit("Task number is outside this owner's assigned set.")

    task_dir = TASK_ROOT / f"task-{args.number:02d}"
    config_path = task_dir / f"task-{args.number:02d}.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("snapshot") != "ABAQUS-2025L":
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
    }
    staged_paths: set[str] = set()
    before = remote.desktop_entries()
    before_names = {item["Name"] for item in before}
    record["desktop_before"] = before

    try:
        config_uploads, config_paths = upload_steps(remote, config.get("config", []), TASK_ROOT)
        staged_paths.update(config_paths)
        record["config_uploads"] = config_uploads
        record["config_launches"] = launch_steps(remote, config.get("config", []))
        if record["config_launches"]:
            time.sleep(3)

        gt_uploads = []
        for path in sorted(item for item in (task_dir / "ground_truth").rglob("*") if item.is_file()):
            rel = path.relative_to(task_dir / "ground_truth")
            remote_path = str(REMOTE_DESKTOP / PureWindowsPath(*rel.parts))
            gt_uploads.append(remote.upload(path, remote_path))
            staged_paths.add(remote_path)
        record["gt_uploads"] = gt_uploads

        post_uploads, post_paths = upload_steps(
            remote, config.get("evaluator", {}).get("postconfig", []), TASK_ROOT
        )
        staged_paths.update(post_paths)
        record["postconfig_uploads"] = post_uploads

        result_spec = config["evaluator"]["result"]
        evaluation = remote.execute(
            result_spec["command"], shell=bool(result_spec.get("shell", False))
        )
        record["eval_command"] = result_spec["command"]
        record["evaluation"] = evaluation
        detail = remote.execute(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    r"$p='C:\Users\user\Desktop\eval_detail.txt'; "
                    r"if (Test-Path -LiteralPath $p) { Get-Content -LiteralPath $p -Raw }"
                ),
            ]
        )
        record["eval_detail"] = detail.get("output", "")
        expected = config["evaluator"]["expected"]["rules"]["expected"]
        passed = evaluation.get("returncode") == 0 and evaluation.get("output", "") == expected
        record["score"] = 1.0 if passed else 0.0
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
        print(
            json.dumps(
                {
                    "task_id": task_id,
                    "passed": record.get("passed", False),
                    "score": record.get("score"),
                    "log": str(log_path),
                    "runner_error": record.get("runner_error"),
                },
                ensure_ascii=False,
            )
        )

    return 0 if record.get("passed") else 1


if __name__ == "__main__":
    sys.exit(main())
