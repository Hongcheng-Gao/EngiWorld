from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ansys.mapdl.core import launch_mapdl


DESKTOP = Path(r"C:\Users\user\Desktop")
DB_FILE = DESKTOP / "apdl_thermal_stress.db"
EXEC_FILE = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
LOG_FILE = DESKTOP / "task08_uniform_temp_evidence.jsonl"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def emit(step: str, value: object) -> None:
    line = "TASK08_TEMP_PROBE " + json.dumps(
        {"step": step, "value": value}, default=str, ensure_ascii=True, sort_keys=True
    )
    print(line, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def main() -> int:
    LOG_FILE.write_text("", encoding="utf-8")
    emit("input", {"path": str(DB_FILE), "size": DB_FILE.stat().st_size, "sha256": digest(DB_FILE)})
    mapdl = None
    try:
        mapdl = launch_mapdl(
            exec_file=EXEC_FILE,
            jobname="task08_uniform_temp_probe",
            run_location=str(DESKTOP),
            nproc=1,
            port=50808,
            override=True,
        )
        emit("runtime", {"version": mapdl.version, "executable": EXEC_FILE})
        mapdl.finish()
        mapdl.resume(DB_FILE.stem, "db")
        mapdl.finish()
        mapdl.slashsolu()
        for command in (
            "/STATUS,SOLU",
            "/STATUS",
            "BFLIST,ALL,TEMP",
            "BFELIST,ALL,TEMP",
            "BFELIST,ALL",
        ):
            try:
                emit("command", {"command": command, "output": str(mapdl.run(command))})
            except Exception as exc:
                emit("command_exception", {"command": command, "type": type(exc).__name__, "message": str(exc)})
        for label in ("TUNIF", "TREF"):
            try:
                value = mapdl.get_value("ACTIVE", 0, "SOLU", label)
                emit("get_value", {"entity": "ACTIVE", "item1": "SOLU", "it1num": label, "value": value})
            except Exception as exc:
                emit("get_value_exception", {"label": label, "type": type(exc).__name__, "message": str(exc)})
            try:
                parameter = "PROBE_" + label
                output = str(mapdl.run(f"*GET,{parameter},ACTIVE,0,SOLU,{label}"))
                emit("star_get", {"label": label, "output": output, "value": mapdl.parameters.get(parameter)})
            except Exception as exc:
                emit("star_get_exception", {"label": label, "type": type(exc).__name__, "message": str(exc)})
        return 0
    except Exception as exc:
        emit("probe_exception", {"type": type(exc).__name__, "message": str(exc)})
        return 1
    finally:
        if mapdl is not None:
            try:
                mapdl.exit()
            except Exception as exc:
                emit("exit_exception", {"type": type(exc).__name__, "message": str(exc)})


if __name__ == "__main__":
    raise SystemExit(main())
