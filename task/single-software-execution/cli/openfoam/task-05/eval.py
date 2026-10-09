#!/usr/bin/env python3
from __future__ import annotations

import ast
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
    expected_x = [0.0, 3.0]
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


def volume_field(path: Path, kind: str) -> list:
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


def vector_field(path: Path) -> list[tuple[float, float, float]]:
    return volume_field(path, "vector")


def scalar_field(path: Path) -> list[float]:
    return volume_field(path, "scalar")


def wall_yplus(path: Path) -> list[float]:
    text = read(path)
    header = named_block(text, "FoamFile")
    wall = patch(text, "wall")
    match = re.search(
        r"\bvalue\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)\s*;",
        wall,
        re.S,
    )
    if not match:
        raise ValueError("missing wall yPlus values")
    values = [float(value) for value in match.group(2).split()]
    if (
        len(values) != int(match.group(1))
        or not all(math.isfinite(value) for value in values)
        or not has_entry(header, "format", r"ascii")
        or not has_entry(header, "class", r"volScalarField")
        or not has_entry(header, "object", r"yPlus")
    ):
        raise ValueError("wall yPlus count mismatch")
    return values


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    velocity = read(CASE / "0/U")
    pressure = read(CASE / "0/p")
    kinetic = read(CASE / "0/k")
    omega = read(CASE / "0/omega")
    nut = read(CASE / "0/nut")
    physical = read(CASE / "constant/physicalProperties")
    momentum = read(CASE / "constant/momentumTransport")
    control = read(CASE / "system/controlDict")
    schemes = read(CASE / "system/fvSchemes")
    ras = named_block(momentum, "RAS")
    div_schemes = named_block(schemes, "divSchemes")
    return all(
        (
            wedge_geometry_is_valid(mesh),
            re.search(r"\(\s*300\s+20\s+1\s*\)", mesh) is not None,
            all(
                has_entry(named_block(mesh, name), "type", r"wedge")
                for name in ("wedgeLow", "wedgeHigh")
            ),
            has_entry(patch(velocity, "axis"), "type", r"empty"),
            has_entry(patch(velocity, "inlet"), "value", r"uniform\s+\(15(?:\.0+)?\s+0(?:\.0+)?\s+0(?:\.0+)?\)"),
            has_entry(patch(velocity, "outlet"), "type", r"zeroGradient"),
            has_entry(patch(velocity, "wall"), "type", r"noSlip"),
            all(has_entry(patch(velocity, name), "type", r"wedge") for name in ("wedgeLow", "wedgeHigh")),
            has_entry(patch(pressure, "outlet"), "type", r"fixedValue"),
            has_entry(patch(pressure, "outlet"), "value", r"uniform\s+0(?:\.0+)?"),
            has_entry(patch(kinetic, "inlet"), "value", r"uniform\s+0\.84375"),
            has_entry(patch(kinetic, "wall"), "type", r"kqRWallFunction"),
            has_entry(patch(omega, "inlet"), "value", r"uniform\s+250(?:\.0+)?"),
            has_entry(patch(omega, "wall"), "type", r"omegaWallFunction"),
            has_entry(patch(nut, "wall"), "type", r"nutkWallFunction"),
            all(has_entry(patch(field_text, "axis"), "type", r"empty") for field_text in (pressure, kinetic, omega, nut)),
            all(has_entry(patch(field_text, name), "type", r"wedge") for field_text in (pressure, kinetic, omega, nut) for name in ("wedgeLow", "wedgeHigh")),
            re.search(r"\bnu\s+\[0 2 -1 0 0 0 0\]\s+1\.5e-?5\s*;", physical, re.I)
            is not None,
            re.search(r"\brho\s+\[1 -3 0 0 0 0 0\]\s+1\.225\s*;", physical) is not None,
            has_entry(momentum, "simulationType", r"RAS"),
            has_entry(ras, "model", r"kOmegaSST"),
            re.search(r"\bendTime\s+2000\s*;", control) is not None,
            re.search(r"\bwriteInterval\s+2000\s*;", control) is not None,
            has_entry(div_schemes, "div(phi,U)", r"bounded\s+Gauss\s+linearUpwind\s+grad\(U\)"),
            has_entry(div_schemes, "div(phi,k)", r"bounded\s+Gauss\s+upwind"),
            has_entry(div_schemes, "div(phi,omega)", r"bounded\s+Gauss\s+upwind"),
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
    if not python_script_is_valid(
        ROOT / "build_case.py",
        (
            "pipe_turb",
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
        ("pipe_turb", "2000", "outlet_profile.csv", "wall_yplus.csv", "summary.txt", "yPlus"),
    ):
        return False
    solve_log = read(CASE / "log.simpleFoam")
    if any(not log_finished(path) for path in (CASE / "log.blockMesh", CASE / "log.cellCentres", CASE / "log.yPlus")):
        return False
    if not log_finished(CASE / "log.simpleFoam") or "Time = 2000" not in solve_log:
        return False
    mesh_check = subprocess.run(
        ["bash", "-lc", ". /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/pipe_turb"],
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
        if any(not close(a, b, 5.0e-7) for a, b in zip(actual, expected)):
            return False

    with (ROOT / "wall_yplus.csv").open(encoding="utf-8", newline="") as stream:
        yplus_rows = list(csv.DictReader(stream))
    if len(yplus_rows) != 300 or set(yplus_rows[0]) != {"wall_face_index", "yplus"}:
        return False
    if any(
        int(row["wall_face_index"]) != index
        or not close(float(row["yplus"]), expected, 5.0e-7)
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
