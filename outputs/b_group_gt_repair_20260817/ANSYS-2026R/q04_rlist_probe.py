from __future__ import annotations

import hashlib
import json
import traceback
from pathlib import Path

from ansys.mapdl.core import launch_mapdl


DESKTOP = Path(r"C:\Users\user\Desktop")
LOG = DESKTOP / "q04_rlist_probe.log"
BASELINE = DESKTOP / "baseline_wb_conduction.db"
EXECUTABLE = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def emit(step: str, value: object) -> None:
    line = "Q04_RLIST_PROBE " + json.dumps({"step": step, "value": value}, default=str, sort_keys=True)
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def main() -> int:
    LOG.write_text("", encoding="utf-8")
    before = digest(BASELINE)
    emit("input", {"path": str(BASELINE), "size": BASELINE.stat().st_size, "sha256": before})
    mapdl = launch_mapdl(
        exec_file=EXECUTABLE, jobname="q04_mapdl", run_location=str(DESKTOP),
        nproc=1, port=50304, override=True,
    )
    try:
        emit("mapdl_version", {"version": mapdl.version, "executable": EXECUTABLE})
        mapdl.resume(BASELINE.stem, "db")
        mapdl.prep7()
        mapdl.allsel()
        try:
            emit("rlist", {"command": "RLIST,ALL", "output": str(mapdl.run("RLIST,ALL"))})
        except Exception as exc:
            emit("rlist_exception", {
                "command": "RLIST,ALL", "type": type(exc).__name__, "message": str(exc),
                "traceback": traceback.format_exc(),
            })
        after = digest(BASELINE)
        emit("input_after", {"sha256": after, "unchanged": before == after})
        return 0
    finally:
        mapdl.exit()


if __name__ == "__main__":
    raise SystemExit(main())
