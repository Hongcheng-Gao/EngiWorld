#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "bfs"
U_REF = 10.0


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
    velocity = read(CASE / "0/U")
    physical = read(CASE / "constant/physicalProperties")
    turbulence = read(CASE / "constant/momentumTransport")
    control = read(CASE / "system/controlDict")
    schemes = read(CASE / "system/fvSchemes")
    return all(
        (
            "(-0.2 0.05 0)" in mesh,
            "(1 0.1 0)" in mesh,
            "(40 20 1)" in mesh,
            mesh.count("(200 20 1)") == 2,
            "type empty;" in mesh,
            "value uniform (10 0 0);" in velocity,
            "viscosityModel constant;" in physical,
            re.search(r"\bnu\s+\[0 2 -1 0 0 0 0\]\s+1\.5e-?5\s*;", physical, re.I)
            is not None,
            "simulationType RAS;" in turbulence,
            "model kOmegaSST;" in turbulence,
            re.search(r"\bendTime\s+2000\s*;", control) is not None,
            re.search(r"\bwriteInterval\s+2000\s*;", control) is not None,
            "div(phi,U) bounded Gauss linearUpwind grad(U);" in schemes,
            "div(phi,k) bounded Gauss upwind;" in schemes,
            "div(phi,omega) bounded Gauss upwind;" in schemes,
        )
    )


def check() -> bool:
    required = (
        ROOT / "build_case.py",
        ROOT / "postprocess.py",
        ROOT / "summary.txt",
        ROOT / "downstream_wall_pressure.csv",
        CASE / "log.blockMesh",
        CASE / "log.simpleFoam",
        CASE / "log.cellCentres",
        CASE / "2000/C",
        CASE / "2000/U",
        CASE / "2000/p",
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    if "End" not in read(CASE / "log.blockMesh") or "End" not in read(CASE / "log.simpleFoam"):
        return False
    mesh_check = subprocess.run(
        ["bash", "-lc", ". /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/bfs"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if mesh_check.returncode != 0 or "Mesh OK." not in mesh_check.stdout or not check_case():
        return False

    centres = field(CASE / "2000/C", "vector")
    velocity = field(CASE / "2000/U", "vector")
    pressure = field(CASE / "2000/p", "scalar")
    if not (len(centres) == len(velocity) == len(pressure) == 8800):
        return False
    indices = sorted(
        (i for i, c in enumerate(centres) if 0.0 < c[0] < 1.0 and c[1] < 0.003),
        key=lambda i: centres[i][0],
    )
    if len(indices) != 200 or min(velocity[i][0] for i in indices) >= -0.01:
        return False
    calculated = [
        (centres[i][0], pressure[i], pressure[i] / (0.5 * U_REF**2), velocity[i][0])
        for i in indices
    ]
    min_cp = min(row[2] for row in calculated)
    if not (-1.0 < min_cp < -1.0e-5):
        return False

    with (ROOT / "downstream_wall_pressure.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 200 or rows[0].keys() != {
        "x_m",
        "p_kinematic_m2ps2",
        "cp",
        "ux_mps",
    }:
        return False
    for row, expected in zip(rows, calculated):
        actual = tuple(float(row[key]) for key in row)
        if any(abs(a - b) > 5.0e-7 for a, b in zip(actual, expected)):
            return False

    values = [line.strip() for line in read(ROOT / "summary.txt").splitlines() if line.strip()]
    if len(values) != 1:
        return False
    reported = float(values[0])
    return math.isfinite(reported) and abs(reported - min_cp) <= 5.0e-7


def main() -> int:
    try:
        result = check()
    except Exception:
        result = False
    print("True" if result else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
