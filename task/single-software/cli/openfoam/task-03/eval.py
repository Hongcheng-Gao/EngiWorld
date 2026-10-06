#!/usr/bin/env python3
from __future__ import annotations

import ast
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


def python_script_is_valid(path: Path, required_fragments: tuple[str, ...]) -> bool:
    text = read(path)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    return bool(tree.body) and all(fragment in text for fragment in required_fragments)


def log_finished(path: Path) -> bool:
    text = read(path)
    return "foam fatal" not in text.lower() and text.rstrip().endswith("End")


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
        valid_values = all(
            len(value) == 3 and all(math.isfinite(item) for item in value)
            for value in values
        )
    elif kind == "scalar":
        values = [float(value) for value in match.group(2).split()]
        valid_values = all(math.isfinite(value) for value in values)
    else:
        raise ValueError(f"unsupported field kind {kind}")
    if (
        len(values) != int(match.group(1))
        or not values
        or not valid_values
        or not has_entry(header, "format", r"ascii")
        or not has_entry(header, "class", rf"vol{kind.capitalize()}Field")
        or not has_entry(header, "object", re.escape(path.name))
    ):
        raise ValueError(f"invalid {kind} field")
    return values


def separated(velocity: list[tuple[float, float, float]], indices: list[int]) -> bool:
    return min(velocity[index][0] for index in indices) < 0.0


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    velocity = read(CASE / "0/U")
    pressure = read(CASE / "0/p")
    kinetic = read(CASE / "0/k")
    omega = read(CASE / "0/omega")
    nut = read(CASE / "0/nut")
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
            has_entry(patch(velocity, "inlet"), "type", r"fixedValue"),
            has_entry(patch(velocity, "inlet"), "value", r"uniform\s+\(10(?:\.0+)?\s+0(?:\.0+)?\s+0(?:\.0+)?\)"),
            has_entry(patch(velocity, "outlet"), "type", r"zeroGradient"),
            has_entry(patch(velocity, "walls"), "type", r"noSlip"),
            has_entry(patch(velocity, "frontAndBack"), "type", r"empty"),
            has_entry(patch(pressure, "inlet"), "type", r"zeroGradient"),
            has_entry(patch(pressure, "outlet"), "type", r"fixedValue"),
            has_entry(patch(pressure, "outlet"), "value", r"uniform\s+0(?:\.0+)?"),
            has_entry(patch(pressure, "walls"), "type", r"zeroGradient"),
            has_entry(patch(pressure, "frontAndBack"), "type", r"empty"),
            has_entry(patch(kinetic, "inlet"), "value", r"uniform\s+0\.375"),
            has_entry(patch(kinetic, "walls"), "type", r"kqRWallFunction"),
            has_entry(patch(omega, "inlet"), "value", r"uniform\s+1000(?:\.0+)?"),
            has_entry(patch(omega, "walls"), "type", r"omegaWallFunction"),
            has_entry(patch(nut, "walls"), "type", r"nutkWallFunction"),
            all(has_entry(patch(field_text, "frontAndBack"), "type", r"empty") for field_text in (kinetic, omega, nut)),
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
    if not python_script_is_valid(
        ROOT / "build_case.py",
        (
            "bfs",
            "blockMeshDict",
            "controlDict",
            "fvSchemes",
            "fvSolution",
            "0/U",
            "0/p",
            "0/k",
            "0/omega",
            "0/nut",
        ),
    ):
        return False
    if not python_script_is_valid(
        ROOT / "postprocess.py",
        ("bfs", "2000", "downstream_wall_pressure.csv", "summary.txt", "min_cp"),
    ):
        return False
    if any(not log_finished(CASE / name) for name in ("log.blockMesh", "log.simpleFoam", "log.cellCentres")):
        return False
    mesh_check = subprocess.run(
        ["bash", "-lc", ". /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/bfs"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if (
        mesh_check.returncode != 0
        or "Mesh OK." not in mesh_check.stdout
        or "Failed " in mesh_check.stdout
        or "foam fatal" in mesh_check.stdout.lower()
        or not mesh_check.stdout.rstrip().endswith("End")
        or not check_case()
    ):
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
    if len(indices) != 200 or not separated(velocity, indices):
        return False
    calculated = [
        (centres[i][0], pressure[i], pressure[i] / (0.5 * U_REF**2), velocity[i][0])
        for i in indices
    ]
    min_cp = min(row[2] for row in calculated)
    if max(row[1] for row in calculated) - min(row[1] for row in calculated) <= 1.0e-8:
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
        if any(not close(a, b, 5.0e-7) for a, b in zip(actual, expected)):
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
