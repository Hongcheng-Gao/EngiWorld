"""Prepare the geometry checker after the agent has finished its blank-VM task.

This is uploaded with evaluator postconfig, never as an agent input. Ubuntu's
FreeCAD package supplies the trusted STEP geometry reader used by eval.py. No
model output or task requirements are changed by dependency preparation.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


def prepare() -> None:
    configured = os.getenv("ENGIWORLD_FREECADCMD")
    candidates = [configured] if configured else []
    candidates.extend(shutil.which(name) for name in ("freecadcmd", "FreeCADCmd", "freecadcmd-python3"))
    candidates.extend(("/usr/bin/freecadcmd", "/usr/bin/FreeCADCmd",
                       "/usr/lib/freecad/bin/freecadcmd-python3", "/usr/lib/freecad/bin/FreeCADCmd",
                       "/usr/local/bin/freecadcmd", "/home/user/.local/bin/freecadcmd"))
    if any(path and Path(path).is_file() and os.access(path, os.X_OK) for path in candidates):
        return
    if not shutil.which("apt-get"):
        raise RuntimeError("The blank Ubuntu evaluator requires apt-get or an explicit ENGIWORLD_FREECADCMD")
    elevated = [] if hasattr(os, "geteuid") and os.geteuid() == 0 else ["sudo", "-n"]
    # Noninteractive sudo must be configured in the evaluation image. Never send
    # guest passwords through task JSON, process arguments, or evaluation logs.
    if elevated and not shutil.which("sudo"):
        raise RuntimeError("Evaluator preparation requires root or noninteractive sudo")
    base = elevated + ["env", "DEBIAN_FRONTEND=noninteractive", "apt-get",
                       "-o", "DPkg::Lock::Timeout=120"]
    for arguments, timeout in ((["update"], 300), (["install", "-y", "--no-install-recommends", "freecad"], 600)):
        completed = subprocess.run(base + arguments, text=True, capture_output=True,
                                   timeout=timeout, check=False)
        if completed.returncode:
            raise RuntimeError("FreeCAD evaluator preparation failed: " +
                               (completed.stderr or completed.stdout)[-2000:])


if __name__ == "__main__":
    try:
        prepare()
    except Exception as exc:
        print(f"EVAL_DEPENDENCY_ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
