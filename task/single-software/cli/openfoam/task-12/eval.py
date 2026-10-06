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


def named_block(text: str, name: str) -> str:
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*\{{", text)
    if not match:
        raise ValueError(f"missing block {name}")
    start = text.find("{", match.start())
    depth = 0
    for index in range(start, len(text)):
        depth += text[index] == "{"
        depth -= text[index] == "}"
        if depth == 0:
            return text[start + 1 : index]
    raise ValueError(f"unterminated block {name}")


def has_entry(block: str, key: str, value: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(key)}\s+{value}\s*;", block) is not None


def close(actual: float, expected: float, tolerance: float) -> bool:
    return math.isfinite(actual) and abs(actual - expected) <= tolerance


def patch(text: str, name: str) -> str:
    return named_block(named_block(text, "boundaryField"), name)


def field(path: Path, kind: str) -> list:
    text = read(path)
    header = named_block(text, "FoamFile")
    match = re.search(
        rf"internalField\s+nonuniform\s+List<{kind}>\s+(\d+)\s*\((.*?)\)\s*;",
        text,
        re.S,
    )
    if not match:
        raise ValueError(f"missing {kind} field")
    if kind == "vector":
        values = [
            tuple(float(value) for value in item.split())
            for item in re.findall(r"\(([^()]+)\)", match.group(2))
        ]
        valid = all(
            len(value) == 3 and all(math.isfinite(component) for component in value)
            for value in values
        )
    else:
        values = [float(value) for value in match.group(2).split()]
        valid = all(math.isfinite(value) for value in values)
    if (
        len(values) != int(match.group(1))
        or not valid
        or not has_entry(header, "format", r"ascii")
        or not has_entry(header, "class", rf"vol{kind.capitalize()}Field")
        or not has_entry(header, "object", re.escape(path.name))
    ):
        raise ValueError(f"invalid {kind} field")
    return values


def paren_section(text: str, name: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*\(", text)
    if not match:
        raise ValueError(f"missing section {name}")
    start = text.find("(", match.start())
    depth = 0
    for index in range(start, len(text)):
        depth += text[index] == "("
        depth -= text[index] == ")"
        if depth == 0:
            return text[start + 1 : index]
    raise ValueError(f"unterminated section {name}")


def mesh_geometry_is_valid(mesh: str) -> bool:
    scale_match = re.search(r"\bconvertToMeters\s+([^;]+);", mesh)
    vertices = [
        tuple(float(value) for value in item.split())
        for item in re.findall(r"\(([^()]+)\)", paren_section(mesh, "vertices"))
    ]
    if scale_match is None or len(vertices) != 6 or any(len(point) != 3 for point in vertices):
        return False
    scale = float(scale_match.group(1))
    points = [tuple(scale * value for value in point) for point in vertices]
    xs = [point[0] for point in points]
    outer = [point for point in points if math.hypot(point[1], point[2]) > 1e-12]
    angles = sorted(math.degrees(math.atan2(point[2], point[1])) for point in outer)
    return (
        abs(min(xs)) <= 1e-12
        and abs(max(xs) - 3.0) <= 1e-12
        and len(outer) == 4
        and all(abs(math.hypot(point[1], point[2]) - RADIUS) <= 1e-9 for point in outer)
        and abs(angles[0] + 2.5) <= 1e-6
        and abs(angles[-1] - 2.5) <= 1e-6
        and re.search(r"hex\s*\([^)]*\)\s*\(\s*240\s+20\s+1\s*\)", mesh) is not None
    )


def numeric_entry(text: str, key: str) -> float:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s+([^;]+);", text)
    if not match:
        raise ValueError(f"missing entry {key}")
    return float(match.group(1))


def dimensioned_value(text: str, key: str) -> float:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s+\[[^]]+\]\s+([^;]+);", text)
    if not match:
        raise ValueError(f"missing dimensioned entry {key}")
    return float(match.group(1))


def label_list(path: Path) -> list[int]:
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", read(path), flags=re.S)
    match = re.search(r"\n\s*(\d+)\s*\n\s*\((.*?)\)\s*$", text, re.S)
    if not match:
        raise ValueError(f"invalid label list: {path}")
    values = [int(value) for value in match.group(2).split()]
    if len(values) != int(match.group(1)):
        raise ValueError(f"label count mismatch: {path}")
    return values


def log_finished(path: Path) -> bool:
    text = read(path)
    if "FOAM FATAL" in text:
        return False
    stripped = text.rstrip()
    if path.name == "log.simpleFoam.parallel":
        return "\nEnd\n" in text and stripped.endswith("Finalising parallel run")
    return stripped.endswith("End")


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    velocity = read(CASE / "0/U")
    pressure = read(CASE / "0/p")
    physical = read(CASE / "constant/physicalProperties")
    momentum = read(CASE / "constant/momentumTransport")
    control = read(CASE / "system/controlDict")
    decomposition = read(CASE / "system/decomposeParDict")
    schemes = read(CASE / "system/fvSchemes")
    solution = read(CASE / "system/fvSolution")
    return all(
        (
            mesh_geometry_is_valid(mesh),
            mesh.count("type wedge;") == 2,
            has_entry(patch(velocity, "axis"), "type", r"empty"),
            has_entry(patch(velocity, "inlet"), "value", r"uniform\s+\(1(?:\.0+)?\s+0(?:\.0+)?\s+0(?:\.0+)?\)"),
            has_entry(patch(velocity, "outlet"), "type", r"zeroGradient"),
            has_entry(patch(velocity, "wall"), "type", r"noSlip"),
            all(has_entry(patch(velocity, name), "type", r"wedge") for name in ("wedgeLow", "wedgeHigh")),
            has_entry(patch(pressure, "axis"), "type", r"empty"),
            has_entry(patch(pressure, "inlet"), "type", r"zeroGradient"),
            has_entry(patch(pressure, "outlet"), "type", r"fixedValue"),
            has_entry(patch(pressure, "outlet"), "value", r"uniform\s+0(?:\.0+)?"),
            all(has_entry(patch(pressure, name), "type", r"wedge") for name in ("wedgeLow", "wedgeHigh")),
            abs(dimensioned_value(physical, "nu") - 1e-4) <= 1e-12,
            abs(dimensioned_value(physical, "rho") - 1.0) <= 1e-12,
            "simulationType laminar;" in momentum,
            abs(numeric_entry(control, "endTime") - 1000.0) <= 1e-12,
            re.search(r"\bwriteFormat\s+ascii\s*;", control) is not None,
            has_entry(named_block(schemes, "divSchemes"), "div(phi,U)", r"bounded\s+Gauss\s+linearUpwind\s+grad\(U\)"),
            "corrected" in named_block(schemes, "laplacianSchemes"),
            has_entry(named_block(named_block(solution, "solvers"), "p"), "solver", r"GAMG"),
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
    if any(not log_finished(path) for path in required[5:11]):
        return False
    if "Mesh OK." not in read(CASE / "log.checkMesh"):
        return False
    parallel_log = read(CASE / "log.simpleFoam.parallel")
    if re.search(r"\bnProcs\s*:\s*4\b", parallel_log) is None:
        return False
    processor_addressing = []
    for processor in range(4):
        directory = CASE / f"processor{processor}"
        addressing = label_list(directory / "constant/polyMesh/cellProcAddressing")
        processor_u = field(directory / "1000/U", "vector")
        processor_p = field(directory / "1000/p", "scalar")
        if not (
            len(addressing) == len(set(addressing)) == len(processor_u) == len(processor_p) == 1200
        ):
            return False
        processor_addressing.extend(addressing)
    if len(set(processor_addressing)) != 4800 or set(processor_addressing) != set(range(4800)):
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
        if any(not close(a, b, 5.0e-7) for a, b in zip(actual, expected)):
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
