#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import subprocess


ROOT = Path("/home/user/Desktop/cavity_sweep")


def run(command: list[str], log: Path) -> None:
    with log.open("w", encoding="utf-8") as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(command)}")


for reynolds in (100, 400, 1000):
    case = ROOT / f"Re{reynolds}"
    run(["blockMesh", "-case", str(case)], case / "log.blockMesh")
    run(["checkMesh", "-case", str(case)], case / "log.checkMesh")
    run(["icoFoam", "-case", str(case)], case / "log.icoFoam")
    run(
        ["postProcess", "-case", str(case), "-latestTime", "-func", "writeCellCentres"],
        case / "log.cellCentres",
    )
