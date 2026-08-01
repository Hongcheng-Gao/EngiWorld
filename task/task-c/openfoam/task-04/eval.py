#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "pipe_laminar"
RADIUS = 0.05
U_BULK = 1.0


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
    momentum = read(CASE / "constant/momentumTransport")
    control = read(CASE / "system/controlDict")
    schemes = read(CASE / "system/fvSchemes")
    return all(
        (
            "(5 0 0)" in mesh,
            "(0 0.0499524111 -0.00218096937)" in mesh,
            "(500 40 1)" in mesh,
            mesh.count("type wedge;") == 2,
            "type empty;" in mesh,
            "value uniform (1 0 0);" in velocity,
            "viscosityModel constant;" in physical,
            re.search(r"\bnu\s+\[0 2 -1 0 0 0 0\]\s+1e-?4\s*;", physical, re.I)
            is not None,
            "simulationType laminar;" in momentum,
            re.search(r"\bendTime\s+2000\s*;", control) is not None,
            re.search(r"\bwriteInterval\s+2000\s*;", control) is not None,
            "div(phi,U) bounded Gauss linearUpwind grad(U);" in schemes,
        )
    )


def check() -> bool:
    required = (
        ROOT / "build_case.py",
        ROOT / "postprocess.py",
        ROOT / "summary.txt",
        ROOT / "outlet_profile.csv",
        CASE / "log.blockMesh",
        CASE / "log.simpleFoam",
        CASE / "log.cellCentres",
        CASE / "2000/C",
        CASE / "2000/U",
        CASE / "2000/p",
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    block_log = read(CASE / "log.blockMesh")
    solve_log = read(CASE / "log.simpleFoam")
    if "End" not in block_log or "End" not in solve_log or "Time = 2000" not in solve_log:
        return False
    mesh_check = subprocess.run(
        ["bash", "-lc", ". /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/pipe_laminar"],
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
    if not (len(centres) == len(velocity) == len(pressure) == 20000):
        return False
    indices = sorted(
        (i for i, c in enumerate(centres) if c[0] > 4.99),
        key=lambda i: math.hypot(centres[i][1], centres[i][2]),
    )
    if len(indices) != 40:
        return False

    calculated = []
    weighted_square_error = 0.0
    weight_sum = 0.0
    for i in indices:
        radius = math.hypot(centres[i][1], centres[i][2])
        theoretical = 2.0 * U_BULK * (1.0 - (radius / RADIUS) ** 2)
        ux = velocity[i][0]
        weight = radius
        weighted_square_error += weight * (ux - theoretical) ** 2
        weight_sum += weight
        calculated.append((radius, ux, theoretical))
    profile_error = math.sqrt(weighted_square_error / weight_sum) / U_BULK
    u_max = max(row[1] for row in calculated)
    if not (1.8 < u_max < 2.1 and profile_error <= 0.05):
        return False

    with (ROOT / "outlet_profile.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    expected_keys = {"radius_m", "ux_mps", "poiseuille_ux_mps"}
    if len(rows) != 40 or set(rows[0]) != expected_keys:
        return False
    for row, expected in zip(rows, calculated):
        actual = tuple(float(row[key]) for key in ("radius_m", "ux_mps", "poiseuille_ux_mps"))
        if any(abs(a - b) > 5.0e-7 for a, b in zip(actual, expected)):
            return False

    values = [line.strip() for line in read(ROOT / "summary.txt").splitlines() if line.strip()]
    if len(values) != 1:
        return False
    reported = float(values[0])
    return math.isfinite(reported) and abs(reported - u_max) <= 5.0e-7


def main() -> int:
    try:
        result = check()
    except Exception:
        result = False
    print("True" if result else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
