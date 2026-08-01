#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "heat"


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


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    initial = read(CASE / "0/T")
    physical = read(CASE / "constant/physicalProperties")
    control = read(CASE / "system/controlDict")
    schemes = read(CASE / "system/fvSchemes")
    return all(
        (
            "(1 0.5 0)" in mesh,
            "(200 20 1)" in mesh,
            "value uniform 400;" in initial,
            "value uniform 300;" in initial,
            "DT DT [0 2 -1 0 0 0 0] 0.01;" in physical,
            re.search(r"\bendTime\s+50\s*;", control) is not None,
            re.search(r"\bdeltaT\s+0\.05\s*;", control) is not None,
            "laplacian(DT,T) Gauss linear corrected;" in schemes,
        )
    )


def check() -> bool:
    required = (
        ROOT / "build_case.py",
        ROOT / "postprocess.py",
        ROOT / "summary.txt",
        ROOT / "temperature_profile.csv",
        CASE / "log.blockMesh",
        CASE / "log.laplacianFoam",
        CASE / "log.cellCentres",
        CASE / "50/C",
        CASE / "50/T",
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    solve_log = read(CASE / "log.laplacianFoam")
    if any("End" not in read(path) for path in (CASE / "log.blockMesh", CASE / "log.cellCentres")):
        return False
    if "End" not in solve_log or "Time = 50" not in solve_log:
        return False
    mesh_check = subprocess.run(
        ["bash", "-lc", ". /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/heat"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if mesh_check.returncode != 0 or "Mesh OK." not in mesh_check.stdout or not check_case():
        return False

    centres = field(CASE / "50/C", "vector")
    temperature = field(CASE / "50/T", "scalar")
    if len(centres) != 4000 or len(temperature) != 4000:
        return False
    theoretical = [400.0 - 100.0 * centre[0] for centre in centres]
    rms_error = math.sqrt(sum((value - theory) ** 2 for value, theory in zip(temperature, theoretical)) / len(temperature))
    if rms_error > 1.0:
        return False
    target_a = min(range(len(centres)), key=lambda i: (centres[i][0] - 0.25) ** 2 + (centres[i][1] - 0.25) ** 2)
    target_b = min(range(len(centres)), key=lambda i: (centres[i][0] - 0.75) ** 2 + (centres[i][1] - 0.25) ** 2)
    if max(abs(centres[target_a][0] - 0.25), abs(centres[target_b][0] - 0.75)) > 0.006:
        return False

    centerline = sorted(
        (i for i, centre in enumerate(centres) if abs(centre[1] - centres[target_a][1]) < 1e-9),
        key=lambda i: centres[i][0],
    )
    keys = ("x_m", "temperature_K", "linear_theory_K")
    with (ROOT / "temperature_profile.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 200 or set(rows[0]) != set(keys):
        return False
    expected_rows = [(centres[i][0], temperature[i], theoretical[i]) for i in centerline]
    for row, expected in zip(rows, expected_rows):
        actual = tuple(float(row[key]) for key in keys)
        if any(abs(a - b) > 5.0e-7 for a, b in zip(actual, expected)):
            return False

    values = [item.strip() for item in read(ROOT / "summary.txt").strip().split(",")]
    if len(values) != 2:
        return False
    reported = tuple(float(value) for value in values)
    expected = (temperature[target_a], temperature[target_b])
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
