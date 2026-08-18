from __future__ import annotations

import hashlib
import json
import sys
import traceback
from pathlib import Path

from ansys.mapdl.core import launch_mapdl


DESKTOP = Path(r"C:\Users\user\Desktop")
SOURCE_DB = DESKTOP / "source_submission.db"
OUTPUT_DB = DESKTOP / "submission.db"
OUTPUT_RST = DESKTOP / "submission.rst"
LOG = DESKTOP / "resolve_provenance.log"
PROCESS_LOG = DESKTOP / "resolve_process.log"
EXECUTABLE = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
VERIFICATION_MARKER = "MAPDL VERIFICATION RUN ONLY"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def emit(step: str, value: object) -> None:
    line = "RESOLVE " + json.dumps({"step": step, "value": value}, default=str, ensure_ascii=True, sort_keys=True)
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def run_command(mapdl, command: str) -> str:
    output = str(mapdl.run(command))
    emit("command", {"command": command, "output": output})
    return output


def inspect_command(mapdl, command: str) -> dict:
    try:
        return {"command": command, "output": str(mapdl.run(command))}
    except Exception as exc:
        return {"command": command, "type": type(exc).__name__, "message": str(exc)}


def main() -> int:
    task_id, mode, port_text = sys.argv[1:4]
    port = int(port_text)
    LOG.write_text("", encoding="utf-8")
    source_before = digest(SOURCE_DB)
    for path in (OUTPUT_DB, OUTPUT_RST):
        path.unlink(missing_ok=True)
    emit("source", {
        "task_id": task_id,
        "mode": mode,
        "path": str(SOURCE_DB),
        "size": SOURCE_DB.stat().st_size,
        "sha256": source_before,
        "old_outputs_removed": not OUTPUT_DB.exists() and not OUTPUT_RST.exists(),
    })

    mapdl = None
    try:
        mapdl = launch_mapdl(
            exec_file=EXECUTABLE,
            jobname="submission",
            run_location=str(DESKTOP),
            nproc=1,
            port=port,
            override=True,
            additional_switches="-smp",
            license_type="ansys",
            mapdl_output=str(PROCESS_LOG),
            cleanup_on_exit=True,
            timeout=90,
        )
        status = str(mapdl.run("/STATUS"))
        mapdl.resume(SOURCE_DB.stem, "db")
        mapdl.prep7()
        mapdl.allsel()
        element_output = str(mapdl.run("ETLIST,ALL"))
        process_output = PROCESS_LOG.read_text(errors="ignore") if PROCESS_LOG.is_file() else ""
        verification = any(
            VERIFICATION_MARKER in output
            for output in (status, element_output, process_output)
        )
        emit("mapdl", {
            "version": mapdl.version,
            "executable": EXECUTABLE,
            "port": port,
            "requested_license_type": "ansys",
            "verification_marker": verification,
            "status_product_lines": [
                line.rstrip()
                for line in status.splitlines()
                if "PRODUCT" in line.upper() or "CUSTOMER" in line.upper()
            ],
            "element_license_lines": [
                line.rstrip()
                for line in element_output.splitlines()
                if "VERIFICATION" in line.upper() or "PRODUCTION" in line.upper()
            ],
        })
        if verification:
            raise RuntimeError("MAPDL verification mode detected before SOLVE")
        emit("model", {
            "nodes": len(mapdl.mesh.nnum),
            "elements": int(mapdl.get_value("ELEM", 0, "COUNT")),
            "commands": [
                inspect_command(mapdl, command)
                for command in ("ETLIST,ALL", "MPLIST,ALL", "SLIST,ALL,,,FULL", "DLIST,ALL,ALL", "FLIST,ALL,ALL")
            ],
        })

        mapdl.finish()
        mapdl.slashsolu()
        if mode == "static":
            run_command(mapdl, "ANTYPE,STATIC,NEW")
            run_command(mapdl, "SOLVE")
        elif mode == "modal":
            run_command(mapdl, "ANTYPE,MODAL,NEW")
            run_command(mapdl, "MODOPT,LANB,3")
            run_command(mapdl, "MXPAND,3,,,YES")
            run_command(mapdl, "SOLVE")
        elif mode == "buckling":
            run_command(mapdl, "ANTYPE,STATIC,NEW")
            run_command(mapdl, "PSTRES,ON")
            run_command(mapdl, "SOLVE")
            mapdl.finish()
            mapdl.slashsolu()
            run_command(mapdl, "ANTYPE,BUCKLE,NEW")
            run_command(mapdl, "BUCOPT,LANB,3")
            run_command(mapdl, "MXPAND,3,,,YES")
            run_command(mapdl, "SOLVE")
        else:
            raise ValueError(mode)

        mapdl.finish()
        mapdl.save(OUTPUT_DB.stem, OUTPUT_DB.suffix.lstrip("."))
        emit("saved", {
            "db_exists": OUTPUT_DB.is_file(),
            "db_size": OUTPUT_DB.stat().st_size if OUTPUT_DB.is_file() else 0,
            "rst_exists": OUTPUT_RST.is_file(),
            "rst_size": OUTPUT_RST.stat().st_size if OUTPUT_RST.is_file() else 0,
        })
        mapdl.post1()
        mapdl.file(OUTPUT_RST.stem, OUTPUT_RST.suffix.lstrip("."))
        mapdl.set("LAST")
        emit("result", {
            "active_time": float(mapdl.get_value("ACTIVE", 0, "SET", "TIME")),
            "active_frequency": float(mapdl.get_value("ACTIVE", 0, "SET", "FREQ")),
            "result_nodes": len(mapdl.result.mesh.nnum),
        })
        mapdl.finish()
        mapdl.save(OUTPUT_DB.stem, OUTPUT_DB.suffix.lstrip("."))
        source_after = digest(SOURCE_DB)
        emit("artifacts", {
            "source_sha256_after": source_after,
            "source_unchanged": source_before == source_after,
            "submission_db": {"size": OUTPUT_DB.stat().st_size, "sha256": digest(OUTPUT_DB)},
            "submission_rst": {"size": OUTPUT_RST.stat().st_size, "sha256": digest(OUTPUT_RST)},
        })
        (DESKTOP / "resolve.done").write_text("success\n", encoding="utf-8")
        return 0
    except Exception as exc:
        emit("exception", {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()})
        (DESKTOP / "resolve.failed").write_text(traceback.format_exc(), encoding="utf-8")
        return 1
    finally:
        if mapdl is not None:
            try:
                mapdl.exit()
            except Exception as exc:
                emit("exit_exception", {"type": type(exc).__name__, "message": str(exc)})


if __name__ == "__main__":
    raise SystemExit(main())
