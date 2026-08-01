#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "cylinder"
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
    values = []
    for line in read(COEFFICIENTS).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        row = [float(value) for value in stripped.split()]
        if len(row) >= 4:
            values.append((row[0], row[2], row[3]))
    return values


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    velocity = read(CASE / "0/U")
    physical = read(CASE / "constant/physicalProperties")
    momentum = read(CASE / "constant/momentumTransport")
    control = read(CASE / "system/controlDict")
    return all(
        (
            mesh.count("hex (") == 8,
            mesh.count("(40 12 1)") == 8,
            mesh.count("arc ") == 32,
            "type wall;" in mesh,
            "internalField uniform (1 0.01 0);" in velocity,
            "value uniform (1 0 0);" in velocity,
            re.search(r"\bnu\s+\[0 2 -1 0 0 0 0\]\s+1e-?3\s*;", physical, re.I)
            is not None,
            "simulationType laminar;" in momentum,
            re.search(r"\bendTime\s+20\s*;", control) is not None,
            re.search(r"\bdeltaT\s+0\.0025\s*;", control) is not None,
            "type forceCoeffs;" in control,
            "patches (cylinder);" in control,
            "Aref 0.001;" in control,
        )
    )


def check() -> bool:
    required = (
        ROOT / "build_case.py",
        ROOT / "postprocess.py",
        ROOT / "summary.txt",
        ROOT / "lift_history.csv",
        CASE / "log.blockMesh",
        CASE / "log.pimpleFoam",
        CASE / "20/U",
        CASE / "20/p",
        COEFFICIENTS,
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    solve_log = read(CASE / "log.pimpleFoam")
    if "End" not in read(CASE / "log.blockMesh") or "End" not in solve_log or "Time = 20" not in solve_log:
        return False
    mesh_check = subprocess.run(
        ["bash", "-lc", ". /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/cylinder"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if mesh_check.returncode != 0 or "Mesh OK." not in mesh_check.stdout or not check_case():
        return False
    velocity = field(CASE / "20/U", "vector")
    pressure = field(CASE / "20/p", "scalar")
    if not (len(velocity) == len(pressure) == 3840):
        return False

    history = coefficient_history()
    window = [row for row in history if row[0] >= 10.0]
    if len(window) < 100:
        return False
    cl_mean = sum(row[2] for row in window) / len(window)
    cl_rms = math.sqrt(sum((row[2] - cl_mean) ** 2 for row in window) / len(window))
    zero_crossings = sum(
        (left[2] - cl_mean) * (right[2] - cl_mean) < 0
        for left, right in zip(window, window[1:])
    )
    cl_max = max(abs(row[2]) for row in window)
    if not (0.05 < cl_max < 3.0 and cl_rms > 0.05 and zero_crossings >= 5):
        return False

    keys = ("time_s", "cd", "cl")
    with (ROOT / "lift_history.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != len(history) or set(rows[0]) != set(keys):
        return False
    for row, expected in zip(rows, history):
        actual = tuple(float(row[key]) for key in keys)
        if any(abs(a - b) > 5.0e-7 for a, b in zip(actual, expected)):
            return False

    values = [line.strip() for line in read(ROOT / "summary.txt").splitlines() if line.strip()]
    if len(values) != 1:
        return False
    reported = float(values[0])
    return math.isfinite(reported) and abs(reported - cl_max) <= 5.0e-7


def main() -> int:
    try:
        result = check()
    except Exception:
        result = False
    print("True" if result else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
