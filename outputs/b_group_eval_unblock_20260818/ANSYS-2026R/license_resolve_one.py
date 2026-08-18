#!/usr/bin/env python3
"""Run the task-declared license setup and re-solve one quantified reference."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
TASK_ROOT = REPO / "task" / "quantified" / "gui-ansys-structural-thermal-optimization"
DESKTOP = Path(r"C:\Users\user\Desktop")
BASE_URL = "http://127.0.0.1:15046"
MARKER = "MAPDL VERIFICATION RUN ONLY"
ANSYS_EXEC = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


class Remote:
    def execute(self, command: list[str], timeout: int = 600) -> dict:
        request = urllib.request.Request(
            BASE_URL + "/execute",
            data=json.dumps({"command": command}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def upload(self, source: Path, destination: str) -> dict:
        result = subprocess.run(
            [
                "curl", "-fsS", "--max-time", "600",
                "-F", f"file_path={destination}",
                "-F", f"file_data=@{source}",
                BASE_URL + "/setup/upload",
            ],
            capture_output=True,
            text=True,
            timeout=610,
            check=True,
        )
        return {
            "source": str(source),
            "destination": destination,
            "size_bytes": source.stat().st_size,
            "sha256": digest(source),
            "response": result.stdout,
        }

    def download(self, source: str, destination: Path) -> dict:
        destination.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "curl", "-fsS", "--max-time", "600",
                "-F", f"file_path={source}",
                "-o", str(destination),
                BASE_URL + "/file",
            ],
            timeout=610,
            check=True,
        )
        return {
            "source": source,
            "destination": str(destination),
            "size_bytes": destination.stat().st_size,
            "sha256": digest(destination),
        }

    def entries(self) -> list[dict]:
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

    def cleanup(self) -> dict:
        names = [
            "source_submission.db", "submission.db", "submission.rst",
            "resolve.inp", "submission.out", "submission.DSP", "submission.bat",
            "submission.err", "submission.esav", "submission.full", "submission.lock",
            "submission.log", "submission.mntr", "submission.out", "submission.page",
            "submission.stat", "submission.mode", "submission.mlv",
            ".__tmp__.inp", ".__tmp__.out",
            "mapdl_license_probe.py", "mapdl_license_probe_ansys",
            "direct_license_probe.inp", "direct_license_probe.out",
            "direct_license_probe.db", "direct_license_probe.rst",
            "direct_license_probe.DSP", "direct_license_probe.err",
            "direct_license_probe.full", "direct_license_probe.log",
            "direct_license_probe.mntr", "direct_license_probe.page", "direct_license_probe.esav",
        ]
        paths = ",".join(json.dumps(str(DESKTOP / name)) for name in names)
        command = (
            "Stop-Process -Name ANSYS,ANSYS261 -Force -ErrorAction SilentlyContinue; "
            "Start-Sleep -Seconds 2; "
            f"$paths=@({paths}); Remove-Item -LiteralPath $paths -Recurse -Force "
            "-ErrorAction SilentlyContinue; "
            r"Get-ChildItem -LiteralPath C:\Users\user\Desktop -Force | "
            "Select-Object Name,Length | ConvertTo-Json -Compress"
        )
        return self.execute(["powershell", "-NoProfile", "-Command", command])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--number", type=int, required=True, choices=(1, 2, 3, 5))
    parser.add_argument("--mode", required=True, choices=("static", "buckling", "modal"))
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    task_dir = TASK_ROOT / f"task-{args.number:02d}"
    config_path = task_dir / f"task-{args.number:02d}.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    task_id = config["id"]
    expected_launch = ["python", r"C:\Users\user\Desktop\license.py"]
    launch_commands = [
        step.get("parameters", {}).get("command")
        for step in config.get("config", [])
        if step.get("type") == "launch"
    ]
    if config.get("snapshot") != "ANSYS-2026R" or not any(
        command == expected_launch
        or (isinstance(command, list) and "license.py" in " ".join(command))
        for command in launch_commands
    ):
        raise SystemExit("Task does not declare the required ANSYS license launch.")

    reference = task_dir / "ground_truth" / "reference"
    source_db = reference / "submission.db"
    source_rst = reference / "submission.rst"
    log_dir = OUTPUT / "logs" / task_id / "license_resolve"
    candidate = log_dir / "candidate"
    candidate.mkdir(parents=True, exist_ok=True)
    record: dict = {
        "task_id": task_id,
        "snapshot": config["snapshot"],
        "mode": args.mode,
        "port": args.port,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "task_json": str(config_path),
        "declared_license_launch": expected_launch,
        "source": {
            "db": {"path": str(source_db), "size_bytes": source_db.stat().st_size, "sha256": digest(source_db)},
            "rst": {"path": str(source_rst), "size_bytes": source_rst.stat().st_size, "sha256": digest(source_rst)},
        },
    }
    remote = Remote()
    try:
        record["preclean"] = remote.cleanup()
        record["desktop_before"] = remote.entries()
        record["license_process_restart"] = remote.execute([
            "powershell", "-NoProfile", "-Command",
            "Stop-Process -Name lmgrd,ansyslmd -Force -ErrorAction SilentlyContinue; "
            "Start-Sleep -Seconds 3",
        ])
        license_result = remote.execute(expected_launch, timeout=180)
        record["license_execution"] = license_result
        if (
            license_result.get("returncode") != 0
            or "[SUCCESS]" not in license_result.get("output", "")
        ):
            raise RuntimeError("license.py did not report success")
        record["license_processes"] = {
            name: remote.execute(["tasklist", "/FI", f"IMAGENAME eq {name}", "/FO", "CSV"])
            for name in ("lmgrd.exe", "ansyslmd.exe")
        }

        solve_commands = {
            "static": ["ANTYPE,STATIC,NEW", "SOLVE"],
            "modal": ["ANTYPE,MODAL,NEW", "MODOPT,LANB,3", "MXPAND,3,,,YES", "SOLVE"],
            "buckling": [
                "ANTYPE,STATIC,NEW", "PSTRES,ON", "SOLVE", "FINISH", "/SOLU",
                "ANTYPE,BUCKLE,NEW", "BUCOPT,LANB,3", "MXPAND,3,,,YES", "SOLVE",
            ],
        }[args.mode]
        input_path = log_dir / "resolve.inp"
        input_path.write_text("\n".join([
            "/BATCH",
            "RESUME,source_submission,db",
            "/PREP7",
            "ALLSEL,ALL",
            "ETLIST,ALL",
            "MPLIST,ALL",
            "FINISH",
            "/SOLU",
            *solve_commands,
            r"SAVE,'C:\Users\user\Desktop\submission','db'",
            "FINISH",
            "/POST1",
            r"FILE,'C:\Users\user\Desktop\submission','rst'",
            "SET,LAST",
            "PRNSOL,U,COMP",
            "FINISH",
            r"SAVE,'C:\Users\user\Desktop\submission','db'",
            "/EXIT,NOSAVE",
            "",
        ]), encoding="ascii")
        record["uploads"] = [
            remote.upload(source_db, str(DESKTOP / "source_submission.db")),
            remote.upload(input_path, str(DESKTOP / "resolve.inp")),
        ]
        resolve = remote.execute(
            [
                ANSYS_EXEC, "-b", "-p", "ansys", "-smp", "-np", "1",
                "-dir", str(DESKTOP), "-j", "submission",
                "-i", str(DESKTOP / "resolve.inp"),
                "-o", str(DESKTOP / "submission.out"),
            ],
            timeout=600,
        )
        record["resolve_execution"] = resolve
        if resolve.get("returncode") != 0:
            try:
                record["failed_output_download"] = remote.download(
                    str(DESKTOP / "submission.out"), log_dir / "failed_submission.out"
                )
            except Exception as download_exc:
                record["failed_output_download_exception"] = {
                    "type": type(download_exc).__name__, "message": str(download_exc)
                }
            raise RuntimeError("MAPDL re-solve failed")

        downloads = [
            remote.download(str(DESKTOP / "submission.out"), log_dir / "submission.out"),
            remote.download(str(DESKTOP / "submission.db"), candidate / "submission.db"),
            remote.download(str(DESKTOP / "submission.rst"), candidate / "submission.rst"),
        ]
        record["downloads"] = downloads
        combined = "\n".join((resolve.get("output", ""), (log_dir / "submission.out").read_text(errors="ignore")))
        record["verification_marker"] = MARKER in combined
        if record["verification_marker"]:
            raise RuntimeError("verification marker found in solve evidence")
        if not any(
            "NUMBER OF ERROR" in line.upper() and line.rstrip().endswith("0")
            for line in combined.splitlines()
        ):
            raise RuntimeError("MAPDL output does not prove a zero-error solve")
        record["candidate"] = {
            path.name: {"size_bytes": path.stat().st_size, "sha256": digest(path)}
            for path in sorted(candidate.iterdir())
            if path.is_file()
        }
        record["status"] = "resolved_nonverification"
        return_code = 0
    except Exception as exc:
        record["status"] = "failed"
        record["exception"] = {"type": type(exc).__name__, "message": str(exc)}
        return_code = 1
    finally:
        try:
            record["cleanup"] = remote.cleanup()
            record["desktop_after_cleanup"] = remote.entries()
        except Exception as exc:
            record["cleanup_exception"] = {"type": type(exc).__name__, "message": str(exc)}
        record["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (log_dir / "license_resolve.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(json.dumps({
            "task_id": task_id,
            "status": record["status"],
            "verification_marker": record.get("verification_marker"),
            "log": str(log_dir / "license_resolve.json"),
            "exception": record.get("exception"),
        }, ensure_ascii=False))
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
