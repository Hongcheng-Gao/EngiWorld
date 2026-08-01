#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import subprocess


CASE = Path("/home/user/Desktop/pipe_parallel")


def run(command: list[str], name: str) -> None:
    with (CASE / name).open("w", encoding="utf-8") as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(command)}")


run(["blockMesh", "-case", str(CASE)], "log.blockMesh")
run(["checkMesh", "-case", str(CASE)], "log.checkMesh")
run(["decomposePar", "-force", "-case", str(CASE)], "log.decomposePar")
run(
    ["mpirun", "--oversubscribe", "-np", "4", "simpleFoam", "-parallel", "-case", str(CASE)],
    "log.simpleFoam.parallel",
)
run(["reconstructPar", "-latestTime", "-case", str(CASE)], "log.reconstructPar")
run(
    ["postProcess", "-case", str(CASE), "-latestTime", "-func", "writeCellCentres"],
    "log.cellCentres",
)
