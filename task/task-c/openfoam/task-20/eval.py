#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "dynamic"
FORCES = CASE / "postProcessing/bodyForces/0/forces.dat"
NUMBER = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def internal_count(path: Path, kind: str) -> int:
    match = re.search(rf"internalField\s+nonuniform\s+List<{kind}>\s+(\d+)", read(path))
    if not match:
        raise ValueError(f"missing nonuniform {kind} field")
    return int(match.group(1))


def force_history() -> list[tuple[float, float, float, float, float]]:
    history = []
    for line in read(FORCES).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        values = [float(value) for value in NUMBER.findall(stripped)]
        if len(values) < 10:
            raise ValueError("invalid forces.dat row")
        pressure_fx = values[1]
        viscous_fx = values[4]
        porous_fx = values[7]
        history.append((values[0], pressure_fx, viscous_fx, porous_fx, pressure_fx + viscous_fx + porous_fx))
    return history


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    motion = read(CASE / "constant/dynamicMeshDict")
    topology = read(CASE / "system/topoSetDict")
    velocity = read(CASE / "0/U")
    physical = read(CASE / "constant/physicalProperties")
    control = read(CASE / "system/controlDict")
    return all(
        (
            mesh.count("hex (") == 20,
            mesh.count("(10 10 1)") == 16,
            mesh.count("(10 5 1)") == 4,
            "type motionSolver;" in motion,
            "motionSolver solidBody;" in motion,
            "cellZone movingZone;" in motion,
            "solidBodyMotionFunction oscillatingRotatingMotion;" in motion,
            "origin (0 0 0);" in motion,
            "amplitude (0 0 5);" in motion,
            "omega 6.283185307179586;" in motion,
            "radius 1.41;" in topology,
            "value uniform (0.5 0 0);" in velocity,
            re.search(r"\bnu\s+\[0 2 -1 0 0 0 0\]\s+0\.01\s*;", physical) is not None,
            re.search(r"\bendTime\s+2\s*;", control) is not None,
            re.search(r"\bdeltaT\s+0\.001\s*;", control) is not None,
            "type forces;" in control,
            "patches (cylinder);" in control,
        )
    )


def check() -> bool:
    required = (
        ROOT / "build_case.py",
        ROOT / "postprocess.py",
        ROOT / "summary.txt",
        ROOT / "force_history.csv",
        CASE / "log.blockMesh",
        CASE / "log.checkMesh",
        CASE / "log.topoSet",
        CASE / "log.pimpleFoam",
        CASE / "log.checkMeshFinal",
        CASE / "constant/polyMesh/cellZones",
        CASE / "0.25/polyMesh/points",
        CASE / "2/U",
        CASE / "2/p",
        FORCES,
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    initial_mesh_log = read(CASE / "log.checkMesh")
    final_mesh_log = read(CASE / "log.checkMeshFinal")
    solve_log = read(CASE / "log.pimpleFoam")
    if not (
        "Mesh OK." in initial_mesh_log
        and "End" in initial_mesh_log
        and "Mesh OK." in final_mesh_log
        and "End" in final_mesh_log
        and "Time = 2" in solve_log
        and "End" in solve_log
        and "movingZone" in read(CASE / "constant/polyMesh/cellZones")
        and internal_count(CASE / "2/U", "vector") == 1800
        and internal_count(CASE / "2/p", "scalar") == 1800
        and (CASE / "0.25/polyMesh/points").read_bytes() != (CASE / "constant/polyMesh/points").read_bytes()
    ):
        return False
    mesh_check = subprocess.run(
        [
            "bash",
            "--noprofile",
            "--norc",
            "-c",
            "trap - CHLD; . /opt/openfoam11/etc/bashrc && checkMesh -latestTime -case /home/user/Desktop/dynamic",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if mesh_check.returncode != 0 or "Mesh OK." not in mesh_check.stdout or not check_case():
        return False

    history = force_history()
    if len(history) < 500 or abs(history[-1][0] - 2.0) > 1e-9:
        return False
    totals = [row[4] for row in history]
    if not (
        all(all(math.isfinite(value) for value in row) for row in history)
        and abs(totals[-1]) < 100
        and max(totals) - min(totals) > 0.01
    ):
        return False
    keys = ("time_s", "pressure_fx_n", "viscous_fx_n", "porous_fx_n", "total_fx_n")
    with (ROOT / "force_history.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != len(history) or set(rows[0]) != set(keys):
        return False
    for row, expected in zip(rows, history):
        actual = tuple(float(row[key]) for key in keys)
        if any(abs(left - right) > 5e-7 for left, right in zip(actual, expected)):
            return False

    lines = [line.strip() for line in read(ROOT / "summary.txt").splitlines() if line.strip()]
    if len(lines) != 1:
        return False
    reported = float(lines[0])
    return math.isfinite(reported) and abs(reported - history[-1][4]) <= 5e-7


def main() -> int:
    try:
        result = check()
    except Exception:
        result = False
    print("True" if result else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
