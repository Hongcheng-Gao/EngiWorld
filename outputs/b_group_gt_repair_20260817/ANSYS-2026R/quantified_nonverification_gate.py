#!/usr/bin/env python3
"""Gate quantified MAPDL re-solves on a non-verification product session."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

from ansys.mapdl.core import launch_mapdl


DESKTOP = Path(r"C:\Users\user\Desktop")
SOURCE_DB = DESKTOP / "source_submission.db"
OUTPUT_DB = DESKTOP / "submission.db"
OUTPUT_RST = DESKTOP / "submission.rst"
EXECUTABLE = Path(r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe")
MARKER = "MAPDL VERIFICATION RUN ONLY"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def selected_lines(text: str) -> list[str]:
    needles = ("VERIFICATION", "PRODUCT", "RELEASE", "CUSTOMER", "ELEMENT TYPE")
    return [line.rstrip() for line in text.splitlines() if any(item in line.upper() for item in needles)]


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: quantified_nonverification_gate.py TASK_ID PORT")
    task_id = sys.argv[1]
    port = int(sys.argv[2])
    if not SOURCE_DB.is_file():
        raise FileNotFoundError(SOURCE_DB)
    source_before = sha256(SOURCE_DB)
    OUTPUT_DB.unlink(missing_ok=True)
    OUTPUT_RST.unlink(missing_ok=True)
    run_dir = DESKTOP / f"nonverification_gate_{task_id}"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir()
    process_log = run_dir / "process.log"
    result_path = run_dir / "nonverification_gate.json"
    record: dict[str, object] = {
        "task_id": task_id,
        "requested_license_type": "ansys",
        "executable": str(EXECUTABLE),
        "port": port,
        "source": {
            "path": str(SOURCE_DB),
            "size_bytes": SOURCE_DB.stat().st_size,
            "sha256_before": source_before,
        },
        "solve_attempted": False,
    }
    mapdl = None
    try:
        mapdl = launch_mapdl(
            exec_file=str(EXECUTABLE),
            run_location=str(run_dir),
            jobname="nonverification_gate",
            nproc=1,
            port=port,
            override=True,
            additional_switches="-smp",
            license_type="ansys",
            mapdl_output=str(process_log),
            cleanup_on_exit=True,
            timeout=90,
        )
        status = str(mapdl.run("/STATUS"))
        mapdl.cwd(str(DESKTOP))
        mapdl.resume(SOURCE_DB.stem, "db")
        model_probe = str(mapdl.run("ETLIST,ALL"))
        verification = MARKER in model_probe
        record.update(
            {
                "mapdl_version": str(mapdl.version),
                "status_selected": selected_lines(status),
                "model_probe_selected": selected_lines(model_probe),
                "verification_marker": verification,
                "gate": "environment_blocked" if verification else "nonverification_available",
            }
        )
        if verification:
            record["block_reason"] = (
                "Explicit ansys product checkout still entered MAPDL verification mode; "
                "SOLVE was intentionally not run and no submission artifacts were written."
            )
        else:
            record["block_reason"] = None
    except Exception as exc:
        record["exception"] = {"type": type(exc).__name__, "message": str(exc)}
        record["gate"] = "environment_blocked"
    finally:
        if mapdl is not None:
            try:
                mapdl.exit()
            except Exception as exc:
                record["exit_exception"] = {"type": type(exc).__name__, "message": str(exc)}
        record["source_sha256_after"] = sha256(SOURCE_DB)
        record["source_unchanged"] = source_before == record["source_sha256_after"]
        record["outputs_written"] = {
            "submission.db": OUTPUT_DB.is_file(),
            "submission.rst": OUTPUT_RST.is_file(),
        }
        result_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        print(json.dumps(record, ensure_ascii=False))
    return 0 if record.get("gate") == "environment_blocked" and record.get("verification_marker") else 2


if __name__ == "__main__":
    raise SystemExit(main())
