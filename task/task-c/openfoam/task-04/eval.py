#!/usr/bin/env python3
from __future__ import annotations

import ast
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


def wedge_geometry_is_valid(mesh: str) -> bool:
    number = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
    vertices = [
        tuple(float(value) for value in match)
        for match in re.findall(
            rf"\(\s*({number})\s+({number})\s+({number})\s*\)",
            paren_section(mesh, "vertices"),
        )
    ]
    if len(vertices) != 6:
        return False
    axis = [vertex for vertex in vertices if math.hypot(vertex[1], vertex[2]) <= 1.0e-10]
    wall = [vertex for vertex in vertices if math.hypot(vertex[1], vertex[2]) > 1.0e-10]
    if len(axis) != 2 or len(wall) != 4:
        return False
    expected_x = [0.0, 5.0]
    if any(not close(vertex[0], target, 1.0e-10) for vertex, target in zip(sorted(axis), expected_x)):
        return False
    half_angle = math.radians(2.5)
    for x in expected_x:
        section = [vertex for vertex in wall if close(vertex[0], x, 1.0e-10)]
        if len(section) != 2:
            return False
        angles = sorted(math.atan2(vertex[2], vertex[1]) for vertex in section)
        if any(not close(math.hypot(vertex[1], vertex[2]), RADIUS, 1.0e-9) for vertex in section):
            return False
        if not all(
            close(actual, expected, 1.0e-9)
            for actual, expected in zip(angles, (-half_angle, half_angle))
        ):
            return False
    return True


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


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    velocity = read(CASE / "0/U")
    pressure = read(CASE / "0/p")
    physical = read(CASE / "constant/physicalProperties")
    momentum = read(CASE / "constant/momentumTransport")
    control = read(CASE / "system/controlDict")
    schemes = read(CASE / "system/fvSchemes")
    return all(
        (
            wedge_geometry_is_valid(mesh),
            re.search(r"\(\s*500\s+40\s+1\s*\)", mesh) is not None,
            has_entry(named_block(mesh, "axis"), "type", r"empty"),
            has_entry(named_block(mesh, "wall"), "type", r"wall"),
            all(
                has_entry(named_block(mesh, name), "type", r"wedge")
                for name in ("wedgeLow", "wedgeHigh")
            ),
            has_entry(patch(velocity, "axis"), "type", r"empty"),
            has_entry(patch(velocity, "inlet"), "type", r"fixedValue"),
            has_entry(patch(velocity, "inlet"), "value", r"uniform\s+\(1(?:\.0+)?\s+0(?:\.0+)?\s+0(?:\.0+)?\)"),
            has_entry(patch(velocity, "outlet"), "type", r"zeroGradient"),
            has_entry(patch(velocity, "wall"), "type", r"noSlip"),
            all(has_entry(patch(velocity, name), "type", r"wedge") for name in ("wedgeLow", "wedgeHigh")),
            has_entry(patch(pressure, "axis"), "type", r"empty"),
            has_entry(patch(pressure, "inlet"), "type", r"zeroGradient"),
            has_entry(patch(pressure, "outlet"), "type", r"fixedValue"),
            has_entry(patch(pressure, "outlet"), "value", r"uniform\s+0(?:\.0+)?"),
            has_entry(patch(pressure, "wall"), "type", r"zeroGradient"),
            all(has_entry(patch(pressure, name), "type", r"wedge") for name in ("wedgeLow", "wedgeHigh")),
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
    if not python_script_is_valid(
        ROOT / "build_case.py",
        ("pipe_laminar", "blockMeshDict", "controlDict", "fvSchemes", "fvSolution", "0/U", "0/p"),
    ):
        return False
    if not python_script_is_valid(
        ROOT / "postprocess.py",
        ("pipe_laminar", "2000", "outlet_profile.csv", "summary.txt", "poiseuille_ux_mps"),
    ):
        return False
    solve_log = read(CASE / "log.simpleFoam")
    if (
        not log_finished(CASE / "log.blockMesh")
        or not log_finished(CASE / "log.simpleFoam")
        or not log_finished(CASE / "log.cellCentres")
        or "Time = 2000" not in solve_log
    ):
        return False
    mesh_check = subprocess.run(
        ["bash", "-lc", ". /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/pipe_laminar"],
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
        if any(not close(a, b, 5.0e-7) for a, b in zip(actual, expected)):
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
