#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "pipe_parallel"
RADIUS = 0.05
RHO = 1.0
RADIAL_CELLS = 20


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
    decomposition = read(CASE / "system/decomposeParDict")
    return all(
        (
            "(3 0 0)" in mesh,
            "(240 20 1)" in mesh,
            mesh.count("type wedge;") == 2,
            "value uniform (1 0 0);" in velocity,
            re.search(r"\bnu\s+\[0 2 -1 0 0 0 0\]\s+1e-?4\s*;", physical, re.I)
            is not None,
            re.search(r"\brho\s+\[1 -3 0 0 0 0 0\]\s+1\s*;", physical)
            is not None,
            "simulationType laminar;" in momentum,
            re.search(r"\bendTime\s+1000\s*;", control) is not None,
            re.search(r"\bnumberOfSubdomains\s+4\s*;", decomposition) is not None,
            re.search(r"\bmethod\s+simple\s*;", decomposition) is not None,
            re.search(r"\bn\s*\(4 1 1\)\s*;", decomposition) is not None,
        )
    )


def calculate() -> tuple[float, float, list[tuple[float, ...]]]:
    centres = field(CASE / "1000/C", "vector")
    velocity = field(CASE / "1000/U", "vector")
    pressure = field(CASE / "1000/p", "scalar")
    if not (len(centres) == len(velocity) == len(pressure) == 4800):
        raise ValueError("unexpected reconstructed field size")
    indices = sorted(
        (i for i, centre in enumerate(centres) if centre[0] > 2.99),
        key=lambda i: math.hypot(centres[i][1], centres[i][2]),
    )
    if len(indices) != RADIAL_CELLS:
        raise ValueError("unexpected outlet-cell count")
    mass_flow = 0.0
    square_error = 0.0
    area_sum = 0.0
    rows = []
    for radial_index, index in enumerate(indices):
        radius = math.hypot(centres[index][1], centres[index][2])
        inner = radial_index * RADIUS / RADIAL_CELLS
        outer = (radial_index + 1) * RADIUS / RADIAL_CELLS
        area = math.pi * (outer**2 - inner**2)
        ux = velocity[index][0]
        theoretical = 2.0 * (1.0 - (radius / RADIUS) ** 2)
        contribution = RHO * ux * area
        mass_flow += contribution
        square_error += area * (ux - theoretical) ** 2
        area_sum += area
        rows.append((radius, ux, theoretical, area, contribution))
    return mass_flow, math.sqrt(square_error / area_sum), rows


def check() -> bool:
    required = (
        ROOT / "build_case.py",
        ROOT / "run_parallel.py",
        ROOT / "postprocess.py",
        ROOT / "summary.txt",
        ROOT / "outlet_mass_flow.csv",
        CASE / "log.blockMesh",
        CASE / "log.checkMesh",
        CASE / "log.decomposePar",
        CASE / "log.simpleFoam.parallel",
        CASE / "log.reconstructPar",
        CASE / "log.cellCentres",
        CASE / "1000/U",
        CASE / "1000/p",
        CASE / "1000/C",
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    if any("End" not in read(path) for path in required[5:11]):
        return False
    if "Mesh OK." not in read(CASE / "log.checkMesh"):
        return False
    parallel_log = read(CASE / "log.simpleFoam.parallel")
    if re.search(r"\bnProcs\s*:\s*4\b", parallel_log) is None:
        return False
    for processor in range(4):
        directory = CASE / f"processor{processor}"
        if not (
            (directory / "constant/polyMesh/cellProcAddressing").is_file()
            and (directory / "1000/U").is_file()
            and (directory / "1000/p").is_file()
        ):
            return False
    mesh_check = subprocess.run(
        [
            "bash",
            "--noprofile",
            "--norc",
            "-c",
            "trap - CHLD; . /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/pipe_parallel",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if mesh_check.returncode != 0 or "Mesh OK." not in mesh_check.stdout or not check_case():
        return False

    mass_flow, profile_error, calculated_rows = calculate()
    theoretical_flow = RHO * math.pi * RADIUS**2
    if not (
        abs(mass_flow - theoretical_flow) / theoretical_flow < 0.02
        and profile_error < 0.08
    ):
        return False
    keys = ("radius_m", "ux_m_s", "poiseuille_ux_m_s", "annulus_area_m2", "mass_flow_kg_s")
    with (ROOT / "outlet_mass_flow.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != RADIAL_CELLS or set(rows[0]) != set(keys):
        return False
    for row, expected in zip(rows, calculated_rows):
        actual = tuple(float(row[key]) for key in keys)
        if any(abs(a - b) > 5.0e-7 for a, b in zip(actual, expected)):
            return False
    reported = float(read(ROOT / "summary.txt").strip())
    return math.isfinite(reported) and abs(reported - mass_flow) <= 5.0e-7


def main() -> int:
    try:
        result = check()
    except Exception:
        result = False
    print("True" if result else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
