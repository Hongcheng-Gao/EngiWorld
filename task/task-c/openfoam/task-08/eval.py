#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "airfoil"
COEFFICIENTS = CASE / "postProcessing/forces/0/forceCoeffs.dat"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def field(path: Path, kind: str) -> list:
    match = re.search(
        rf"internalField\s+nonuniform\s+List<{kind}>\s+\d+\s*\((.*?)\)\s*;",
        read(path),
        re.S,
    )
    if not match:
        raise ValueError(f"missing {kind} field")
    if kind == "vector":
        return [
            tuple(float(value) for value in item.split())
            for item in re.findall(r"\(([^()]+)\)", match.group(1))
        ]
    return [float(value) for value in match.group(1).split()]


def coefficient_history() -> list[tuple[float, float, float]]:
    history = []
    for line in read(COEFFICIENTS).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        values = [float(value) for value in stripped.split()]
        if len(values) >= 4:
            history.append((values[0], values[2], values[3]))
    return history


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    build_script = read(ROOT / "build_case.py")
    physical = read(CASE / "constant/physicalProperties")
    momentum = read(CASE / "constant/momentumTransport")
    control = read(CASE / "system/controlDict")
    schemes = read(CASE / "system/fvSchemes")
    boundary = read(CASE / "constant/polyMesh/boundary")
    return all(
        (
            mesh.count("hex (") == 161,
            mesh.count("(80 1 1) simpleGrading (80 1 1)") == 161,
            "FARFIELD { type patch;" in mesh,
            "internalField uniform (0.9961946981 0.08715574275 0);" in build_script,
            "type freestreamVelocity;" in build_script,
            "type freestreamPressure;" in build_script,
            build_script.count("type inletOutlet;") == 2,
            re.search(r"\bnu\s+\[0 2 -1 0 0 0 0\]\s+1e-?5\s*;", physical, re.I)
            is not None,
            "model kOmegaSST;" in momentum,
            re.search(r"\bendTime\s+1000\s*;", control) is not None,
            "patches (WALL10);" in control,
            "magUInf 1;" in control,
            "lRef 1;" in control,
            "Aref 0.01;" in control,
            "liftDir (-0.08715574275 0.9961946981 0);" in control,
            "div(phi,U) bounded Gauss upwind;" in schemes,
            re.search(r"\bSYMP3\b.*?type\s+empty;", boundary, re.S) is not None,
        )
    )


def check() -> bool:
    required = (
        ROOT / "build_case.py",
        ROOT / "postprocess.py",
        ROOT / "summary.txt",
        ROOT / "force_coefficients.csv",
        CASE / "log.blockMesh",
        CASE / "log.checkMesh",
        CASE / "log.potentialFoam",
        CASE / "log.simpleFoam",
        CASE / "1000/U",
        CASE / "1000/p",
        CASE / "1000/k",
        CASE / "1000/omega",
        COEFFICIENTS,
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    solve_log = read(CASE / "log.simpleFoam")
    if any(
        "End" not in read(path)
        for path in (CASE / "log.blockMesh", CASE / "log.checkMesh", CASE / "log.potentialFoam")
    ):
        return False
    if "End" not in solve_log or "Time = 1000" not in solve_log:
        return False
    mesh_check = subprocess.run(
        [
            "bash",
            "--noprofile",
            "--norc",
            "-c",
            "trap - CHLD; . /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/airfoil",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if mesh_check.returncode != 0 or "Mesh OK." not in mesh_check.stdout or not check_case():
        return False
    velocity = field(CASE / "1000/U", "vector")
    pressure = field(CASE / "1000/p", "scalar")
    turbulent_k = field(CASE / "1000/k", "scalar")
    omega = field(CASE / "1000/omega", "scalar")
    if not (len(velocity) == len(pressure) == len(turbulent_k) == len(omega) == 12880):
        return False

    history = coefficient_history()
    window = [row for row in history if row[0] >= 800]
    if len(window) < 200:
        return False
    avg_cd = sum(row[1] for row in window) / len(window)
    avg_cl = sum(row[2] for row in window) / len(window)
    std_cd = math.sqrt(sum((row[1] - avg_cd) ** 2 for row in window) / len(window))
    std_cl = math.sqrt(sum((row[2] - avg_cl) ** 2 for row in window) / len(window))
    if not (0.1 < avg_cl < 2.0 and 0.001 < avg_cd < 0.2 and std_cl < 0.02 and std_cd < 0.01):
        return False

    keys = ("iteration", "cd", "cl")
    with (ROOT / "force_coefficients.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != len(history) or set(rows[0]) != set(keys):
        return False
    for row, expected in zip(rows, history):
        actual = tuple(float(row[key]) for key in keys)
        if any(abs(a - b) > 5.0e-7 for a, b in zip(actual, expected)):
            return False

    values = [item.strip() for item in read(ROOT / "summary.txt").strip().split(",")]
    if len(values) != 2:
        return False
    reported = tuple(float(value) for value in values)
    expected = (avg_cl, avg_cd)
    return all(math.isfinite(value) for value in reported) and all(
        abs(actual - target) <= 5.0e-7 for actual, target in zip(reported, expected)
    )


def main() -> int:
    try:
        result = check()
    except Exception:
        result = False
    print("True" if result else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
