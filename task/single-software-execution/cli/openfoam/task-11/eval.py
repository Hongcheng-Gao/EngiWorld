#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
SWEEP = ROOT / "cavity_sweep"
REYNOLDS = (100, 400, 1000)


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


def vectors(path: Path) -> list[tuple[float, float, float]]:
    text = read(path)
    header = named_block(text, "FoamFile")
    match = re.search(
        r"internalField\s+nonuniform\s+List<vector>\s+(\d+)\s*\((.*?)\)\s*;",
        text,
        re.S,
    )
    if not match:
        raise ValueError(f"missing vector field: {path}")
    values = [
        tuple(float(value) for value in item.split())
        for item in re.findall(r"\(([^()]+)\)", match.group(2))
    ]
    if (
        len(values) != int(match.group(1))
        or any(
            len(value) != 3 or not all(math.isfinite(component) for component in value)
            for value in values
        )
        or not has_entry(header, "format", r"ascii")
        or not has_entry(header, "class", r"volVectorField")
        or not has_entry(header, "object", re.escape(path.name))
    ):
        raise ValueError(f"invalid vector field: {path}")
    return values


def scalars(path: Path) -> list[float]:
    text = read(path)
    header = named_block(text, "FoamFile")
    match = re.search(
        r"internalField\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)\s*;",
        text,
        re.S,
    )
    if not match:
        raise ValueError(f"missing scalar field: {path}")
    values = [float(value) for value in match.group(2).split()]
    if (
        len(values) != int(match.group(1))
        or any(not math.isfinite(value) for value in values)
        or not has_entry(header, "format", r"ascii")
        or not has_entry(header, "class", r"volScalarField")
        or not has_entry(header, "object", re.escape(path.name))
    ):
        raise ValueError(f"invalid scalar field: {path}")
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
    if scale_match is None or len(vertices) != 8 or any(len(point) != 3 for point in vertices):
        return False
    scale = float(scale_match.group(1))
    xs, ys, zs = zip(*(tuple(scale * value for value in point) for point in vertices))
    return (
        abs(min(xs)) <= 1e-12
        and abs(max(xs) - 1.0) <= 1e-12
        and abs(min(ys)) <= 1e-12
        and abs(max(ys) - 1.0) <= 1e-12
        and abs(min(zs)) <= 1e-12
        and abs(max(zs) - 0.01) <= 1e-12
        and re.search(r"hex\s*\([^)]*\)\s*\(\s*50\s+50\s+1\s*\)", mesh) is not None
    )


def numeric_entry(text: str, key: str) -> float:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s+([^;]+);", text)
    if not match:
        raise ValueError(f"missing entry {key}")
    return float(match.group(1))


def log_finished(path: Path) -> bool:
    text = read(path)
    return "FOAM FATAL" not in text and text.rstrip().endswith("End")


def case_inputs(case: Path, reynolds: int) -> bool:
    mesh = read(case / "system/blockMeshDict")
    velocity = read(case / "0/U")
    pressure = read(case / "0/p")
    physical = read(case / "constant/physicalProperties")
    control = read(case / "system/controlDict")
    schemes = read(case / "system/fvSchemes")
    solution = read(case / "system/fvSolution")
    boundary = read(case / "constant/polyMesh/boundary")
    match = re.search(r"\bnu\s+\[[^]]+\]\s+([^;]+);", physical)
    return all(
        (
            mesh_geometry_is_valid(mesh),
            has_entry(patch(velocity, "movingWall"), "value", r"uniform\s+\(1(?:\.0+)?\s+0(?:\.0+)?\s+0(?:\.0+)?\)"),
            has_entry(patch(velocity, "fixedWalls"), "type", r"noSlip"),
            has_entry(patch(velocity, "frontAndBack"), "type", r"empty"),
            has_entry(patch(pressure, "movingWall"), "type", r"zeroGradient"),
            has_entry(patch(pressure, "fixedWalls"), "type", r"zeroGradient"),
            has_entry(patch(pressure, "frontAndBack"), "type", r"empty"),
            match is not None and abs(float(match.group(1)) - 1.0 / reynolds) < 1.0e-12,
            abs(numeric_entry(control, "endTime") - 30.0) <= 1e-12,
            abs(numeric_entry(control, "deltaT") - 0.005) <= 1e-12,
            re.search(r"\bwriteFormat\s+ascii\s*;", control) is not None,
            has_entry(named_block(schemes, "ddtSchemes"), "default", r"Euler"),
            has_entry(named_block(schemes, "divSchemes"), "div(phi,U)", r"Gauss\s+linear"),
            has_entry(named_block(solution, "PISO"), "nCorrectors", r"2"),
            re.search(r"\bfrontAndBack\b.*?type\s+empty;", boundary, re.S)
            is not None,
        )
    )


def center_result(case: Path) -> tuple[tuple[float, float, float], float]:
    final = case / "30"
    centres = vectors(final / "C")
    velocity = vectors(final / "U")
    if len(centres) != 2500 or len(velocity) != len(centres):
        raise ValueError("unexpected final field size")
    target = (0.5, 0.5, 0.005)
    indices = sorted(
        range(len(centres)),
        key=lambda i: sum((centres[i][j] - target[j]) ** 2 for j in range(3)),
    )[:4]
    center = tuple(sum(velocity[i][j] for i in indices) / 4.0 for j in range(3))
    max_speed = max(math.sqrt(sum(component**2 for component in item)) for item in velocity)
    return center, max_speed


def check() -> bool:
    required_root = (
        ROOT / "build_case.py",
        ROOT / "run_sweep.py",
        ROOT / "postprocess.py",
        ROOT / "summary.txt",
        ROOT / "sweep_results.csv",
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required_root):
        return False
    calculated = {}
    for reynolds in REYNOLDS:
        case = SWEEP / f"Re{reynolds}"
        required = (
            case / "log.blockMesh",
            case / "log.checkMesh",
            case / "log.icoFoam",
            case / "log.cellCentres",
            case / "30/U",
            case / "30/p",
            case / "30/C",
        )
        if any(not path.is_file() or path.stat().st_size == 0 for path in required):
            return False
        if any(not log_finished(path) for path in required[:4]):
            return False
        if "Mesh OK." not in read(case / "log.checkMesh") or not case_inputs(case, reynolds):
            return False
        mesh_check = subprocess.run(
            [
                "bash",
                "--noprofile",
                "--norc",
                "-c",
                f"trap - CHLD; . /opt/openfoam11/etc/bashrc && checkMesh -case {case}",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
        )
        if mesh_check.returncode != 0 or "Mesh OK." not in mesh_check.stdout:
            return False
        center, max_speed = center_result(case)
        if len(scalars(case / "30/p")) != 2500:
            return False
        if not (-0.5 < center[0] < 0 and 0.5 < max_speed < 1.2):
            return False
        calculated[reynolds] = (1.0 / reynolds, *center, max_speed)

    if not (
        calculated[100][1]
        < calculated[400][1]
        < calculated[1000][1]
        < 0
    ):
        return False

    with (ROOT / "sweep_results.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    keys = ("nu_m2_s", "center_ux", "center_uy", "center_uz", "max_speed")
    if [int(row["reynolds"]) for row in rows] != list(REYNOLDS):
        return False
    for row in rows:
        reynolds = int(row["reynolds"])
        actual = tuple(float(row[key]) for key in keys)
        if any(not close(a, b, 5.0e-7) for a, b in zip(actual, calculated[reynolds])):
            return False

    lines = [line.strip() for line in read(ROOT / "summary.txt").splitlines() if line.strip()]
    if len(lines) != 3:
        return False
    for line, reynolds in zip(lines, REYNOLDS):
        parts = [item.strip() for item in line.split(",")]
        if len(parts) != 2 or int(parts[0]) != reynolds:
            return False
        if not close(float(parts[1]), calculated[reynolds][1], 5.0e-7):
            return False
    return True


def main() -> int:
    try:
        result = check()
    except Exception:
        result = False
    print("True" if result else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
