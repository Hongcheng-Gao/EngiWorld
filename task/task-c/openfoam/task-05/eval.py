#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "pipe_turb"
RADIUS = 0.05
RHO = 1.225
RADIAL_CELLS = 20


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def vector_field(path: Path) -> list[tuple[float, float, float]]:
    match = re.search(
        r"internalField\s+nonuniform\s+List<vector>\s+\d+\s*\((.*?)\)\s*;",
        read(path),
        re.S,
    )
    if not match:
        raise ValueError("missing vector field")
    return [
        tuple(float(value) for value in item.split())
        for item in re.findall(r"\(([^()]+)\)", match.group(1))
    ]


def scalar_field(path: Path) -> list[float]:
    match = re.search(
        r"internalField\s+nonuniform\s+List<scalar>\s+\d+\s*\((.*?)\)\s*;",
        read(path),
        re.S,
    )
    if not match:
        raise ValueError("missing scalar field")
    return [float(value) for value in match.group(1).split()]


def wall_yplus(path: Path) -> list[float]:
    match = re.search(
        r"\bwall\s*\{.*?value\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)\s*;",
        read(path),
        re.S,
    )
    if not match:
        raise ValueError("missing wall yPlus values")
    values = [float(value) for value in match.group(2).split()]
    if len(values) != int(match.group(1)):
        raise ValueError("wall yPlus count mismatch")
    return values


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    velocity = read(CASE / "0/U")
    physical = read(CASE / "constant/physicalProperties")
    momentum = read(CASE / "constant/momentumTransport")
    control = read(CASE / "system/controlDict")
    schemes = read(CASE / "system/fvSchemes")
    return all(
        (
            "(3 0 0)" in mesh,
            "(300 20 1)" in mesh,
            mesh.count("type wedge;") == 2,
            "value uniform (15 0 0);" in velocity,
            re.search(r"\bnu\s+\[0 2 -1 0 0 0 0\]\s+1\.5e-?5\s*;", physical, re.I)
            is not None,
            re.search(r"\brho\s+\[1 -3 0 0 0 0 0\]\s+1\.225\s*;", physical) is not None,
            "simulationType RAS;" in momentum,
            "model kOmegaSST;" in momentum,
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
        ROOT / "outlet_profile.csv",
        ROOT / "wall_yplus.csv",
        CASE / "log.blockMesh",
        CASE / "log.simpleFoam",
        CASE / "log.cellCentres",
        CASE / "log.yPlus",
        CASE / "2000/C",
        CASE / "2000/U",
        CASE / "2000/p",
        CASE / "2000/k",
        CASE / "2000/omega",
        CASE / "2000/yPlus",
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    solve_log = read(CASE / "log.simpleFoam")
    if any("End" not in read(path) for path in (CASE / "log.blockMesh", CASE / "log.cellCentres", CASE / "log.yPlus")):
        return False
    if "End" not in solve_log or "Time = 2000" not in solve_log:
        return False
    mesh_check = subprocess.run(
        ["bash", "-lc", ". /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/pipe_turb"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if mesh_check.returncode != 0 or "Mesh OK." not in mesh_check.stdout or not check_case():
        return False

    centres = vector_field(CASE / "2000/C")
    velocity = vector_field(CASE / "2000/U")
    pressure = scalar_field(CASE / "2000/p")
    if not (len(centres) == len(velocity) == len(pressure) == 6000):
        return False
    indices = sorted(
        (i for i, c in enumerate(centres) if c[0] > 2.99),
        key=lambda i: math.hypot(centres[i][1], centres[i][2]),
    )
    if len(indices) != RADIAL_CELLS:
        return False

    calculated = []
    mass_flow = 0.0
    for radial_index, i in enumerate(indices):
        radius = math.hypot(centres[i][1], centres[i][2])
        inner = radial_index * RADIUS / RADIAL_CELLS
        outer = (radial_index + 1) * RADIUS / RADIAL_CELLS
        annulus_area = math.pi * (outer**2 - inner**2)
        contribution = RHO * velocity[i][0] * annulus_area
        mass_flow += contribution
        calculated.append((radius, velocity[i][0], annulus_area, contribution))
    if not (0.13 < mass_flow < 0.16):
        return False

    yplus = wall_yplus(CASE / "2000/yPlus")
    if len(yplus) != 300:
        return False
    avg_yplus = sum(yplus) / len(yplus)
    if not (20.0 <= avg_yplus <= 100.0):
        return False

    with (ROOT / "outlet_profile.csv").open(encoding="utf-8", newline="") as stream:
        outlet_rows = list(csv.DictReader(stream))
    outlet_keys = ("radius_m", "ux_mps", "annulus_area_m2", "mass_flow_kgps")
    if len(outlet_rows) != RADIAL_CELLS or set(outlet_rows[0]) != set(outlet_keys):
        return False
    for row, expected in zip(outlet_rows, calculated):
        actual = tuple(float(row[key]) for key in outlet_keys)
        if any(abs(a - b) > 5.0e-7 for a, b in zip(actual, expected)):
            return False

    with (ROOT / "wall_yplus.csv").open(encoding="utf-8", newline="") as stream:
        yplus_rows = list(csv.DictReader(stream))
    if len(yplus_rows) != 300 or set(yplus_rows[0]) != {"wall_face_index", "yplus"}:
        return False
    if any(
        int(row["wall_face_index"]) != index
        or abs(float(row["yplus"]) - expected) > 5.0e-7
        for index, (row, expected) in enumerate(zip(yplus_rows, yplus))
    ):
        return False

    values = [item.strip() for item in read(ROOT / "summary.txt").strip().split(",")]
    if len(values) != 2:
        return False
    reported = tuple(float(value) for value in values)
    return all(math.isfinite(value) for value in reported) and all(
        abs(actual - expected) <= 5.0e-7
        for actual, expected in zip(reported, (mass_flow, avg_yplus))
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
