from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import traceback
from pathlib import Path

from ansys.mapdl.core import launch_mapdl


DESKTOP = Path(r"C:\Users\user\Desktop")
LOG = DESKTOP / "mapdl_raw_probe.log"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def emit(step: str, value: object) -> None:
    line = "MAPDL_PROBE " + json.dumps(
        {"step": step, "value": value}, default=str, ensure_ascii=True, sort_keys=True
    )
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def main() -> int:
    task_id = sys.argv[1]
    port = int(sys.argv[2])
    LOG.write_text("", encoding="utf-8")
    spec = importlib.util.spec_from_file_location("official_eval", DESKTOP / "eval.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    required = {
        str(path): {"size": path.stat().st_size, "sha256": digest(path)}
        for path in module.REQUIRED_FILES
    }
    emit("inputs", {"task_id": task_id, "eval_sha256": digest(DESKTOP / "eval.py"), "required": required})

    mapdl = None
    try:
        mapdl = launch_mapdl(
            exec_file=module.EXEC_FILE,
            jobname="raw_probe_" + task_id.replace("-", "_")[:40],
            run_location=str(DESKTOP),
            nproc=1,
            port=port,
            override=True,
        )
        emit("mapdl_version", {"version": mapdl.version, "executable": module.EXEC_FILE})
        try:
            emit("status", str(mapdl.run("/STATUS")))
        except Exception as exc:
            emit("status_exception", {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()})

        predictions = module.extract_predictions(mapdl)
        emit("predictions", predictions)

        mapdl.finish()
        mapdl.resume(module.DB_FILE.stem, "db")
        mapdl.prep7()
        mapdl.allsel()
        coordinates = mapdl.mesh.nodes
        emit("mesh", {
            "node_count": len(mapdl.mesh.nnum),
            "element_count": int(mapdl.get_value("ELEM", 0, "COUNT")),
            "bounds": {
                "x": [float(coordinates[:, 0].min()), float(coordinates[:, 0].max())],
                "y": [float(coordinates[:, 1].min()), float(coordinates[:, 1].max())],
                "z": [float(coordinates[:, 2].min()), float(coordinates[:, 2].max())],
            },
        })

        for command in (
            "ETLIST,ALL",
            "MPLIST,ALL",
            "DLIST,ALL,ALL",
            "FLIST,ALL,ALL",
            "BFLIST,ALL,TEMP",
            "RLIST,ALL",
            "KEYOPT,1,LIST",
        ):
            try:
                emit("raw_command", {"command": command, "output": str(mapdl.run(command))})
            except Exception as exc:
                emit("raw_command_exception", {
                    "command": command,
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                })

        try:
            emit("strict_process_check", module.strict_process_check(mapdl, predictions))
        except Exception as exc:
            emit("strict_process_check_exception", {
                "type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()
            })
        try:
            emit("passes_process_checks", module.passes_process_checks(mapdl, predictions, task_name="task-" + task_id.split("-")[-2]))
        except Exception as exc:
            emit("passes_process_checks_exception", {
                "type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()
            })
        return 0
    except Exception as exc:
        emit("probe_exception", {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()})
        return 1
    finally:
        if mapdl is not None:
            try:
                mapdl.exit()
            except Exception as exc:
                emit("exit_exception", {"type": type(exc).__name__, "message": str(exc)})


if __name__ == "__main__":
    raise SystemExit(main())
