#!/usr/bin/env python3
"""Probe MAPDL product checkout and verification mode with a fresh solve."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

from ansys.mapdl.core import launch_mapdl


DESKTOP = Path(r"C:\Users\user\Desktop")
EXECUTABLE = Path(r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe")
MARKER = "MAPDL VERIFICATION RUN ONLY"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relevant(text: str) -> list[str]:
    needles = ("VERIFICATION", "PRODUCT", "LICENSE", "RELEASE", "SOLVE", "ERROR")
    return [line.rstrip() for line in text.splitlines() if any(item in line.upper() for item in needles)]


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: mapdl_license_probe.py MODE PORT")
    requested = sys.argv[1]
    license_type = None if requested == "default" else requested
    port = int(sys.argv[2])
    run_dir = DESKTOP / f"mapdl_license_probe_{requested}"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir()
    process_log = run_dir / "process.log"
    record: dict[str, object] = {
        "requested_license_type": requested,
        "launch_license_type": license_type,
        "port": port,
        "executable": str(EXECUTABLE),
    }
    mapdl = None
    try:
        mapdl = launch_mapdl(
            exec_file=str(EXECUTABLE),
            run_location=str(run_dir),
            jobname="license_probe",
            nproc=1,
            port=port,
            override=True,
            additional_switches="-smp",
            license_type=license_type,
            mapdl_output=str(process_log),
            cleanup_on_exit=True,
            timeout=90,
        )
        record["mapdl_version"] = str(mapdl.version)
        status = str(mapdl.run("/STATUS"))
        mapdl.clear()
        model_output = str(
            mapdl.input_strings(
                """
/PREP7
ET,1,SOLID185
MP,EX,1,210000
MP,NUXY,1,0.3
BLOCK,0,1,0,1,0,1
ESIZE,1
VMESH,ALL
NSEL,S,LOC,X,0
D,ALL,ALL,0
ALLSEL,ALL
NSEL,S,LOC,X,1
F,ALL,FX,1
ALLSEL,ALL
FINISH
/SOLU
ANTYPE,STATIC,NEW
SOLVE
FINISH
"""
            )
        )
        process_text = process_log.read_text(errors="ignore") if process_log.is_file() else ""
        combined = "\n".join((status, model_output, process_text))
        record.update(
            {
                "verification_marker": MARKER in combined,
                "status_relevant": relevant(status),
                "solve_relevant": relevant(model_output),
                "process_relevant": relevant(process_text),
                "process_log_sha256": sha256(process_log) if process_log.is_file() else None,
            }
        )
    except Exception as exc:
        record["exception"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        if mapdl is not None:
            try:
                mapdl.exit()
            except Exception as exc:
                record["exit_exception"] = {"type": type(exc).__name__, "message": str(exc)}
    evidence = run_dir / "probe.json"
    evidence.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False))
    return 1 if "exception" in record else 0


if __name__ == "__main__":
    raise SystemExit(main())
