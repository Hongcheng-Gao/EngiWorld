#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import math
import re
import shlex
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "pipe_laminar"
RADIUS = 0.05
U_BULK = 1.0


def read(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if path.name in {"blockMeshDict", "controlDict", "fvSchemes", "fvSolution", "physicalProperties", "transportProperties", "momentumTransport", "U", "p", "C"} and ("#include" in text or "$" in text or "#calc" in text):
        completed = subprocess.run(["bash", "-lc", ". /opt/openfoam11/etc/bashrc && foamDictionary -expand " + shlex.quote(str(path))], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
        if completed.returncode != 0:
            raise ValueError("OpenFOAM dictionary expansion failed: " + str(path))
        return completed.stdout
    return text


def named_block(text: str, name: str) -> str:
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    match = re.search(rf"(?<![\w.-]){re.escape(name)}\s*\{{", text)
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
    return bool(tree.body)


def log_finished(path: Path) -> bool:
    text = read(path)
    return "foam fatal" not in text.lower() and text.rstrip().endswith("End")


def paren_section(text: str, name: str) -> str:
    match = re.search(rf"(?<![\w.-]){re.escape(name)}\s*(?:\d+\s*)?\(", text)
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
    vertices = list(dict.fromkeys(tuple(round(x, 10) for x in v) for v in vertices))
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
        section = [vertex for vertex in wall if close(vertex[0], x, 1.0e-8)]
        if len(section) != 2:
            return False
        radii = [math.hypot(v[1], v[2]) for v in section]
        if not all(close(r, RADIUS, 1e-7) or close(r * math.cos(half_angle), RADIUS, 1e-7) for r in radii):
            return False
        cosine = sum(section[0][i] * section[1][i] for i in (1, 2)) / (radii[0] * radii[1])
        separation = math.acos(max(-1.0, min(1.0, cosine)))
        if not close(separation, 2 * half_angle, 1e-5):
            return False
    return True


def patch(text: str, name: str, patch_type: str | None = None) -> str:
    body = named_block(text, "boundaryField")
    try:
        return named_block(body, name)
    except ValueError:
        pass
    for pattern, content in re.findall(r'"([^"\n]+)"\s*\{([^{}]*)\}', body, re.S):
        if re.fullmatch(pattern, name):
            return content
    # Native OpenFOAM constraint groups are created for empty/wedge patches.
    if patch_type in ("empty", "wedge"):
        return named_block(body, patch_type)
    raise ValueError("missing boundary condition for " + name)


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


def scalar_entry(text: str, key: str) -> float:
    clean = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    match = re.search(rf"(?<!\w){re.escape(key)}\s+(?:\[[^\]]+\]\s*)?([^;]+);", clean)
    if not match:
        raise ValueError(f"missing scalar {key}")
    return float(match.group(1).strip())


def uniform_vector(text: str, expected: tuple) -> bool:
    match = re.search(r"\bvalue\s+uniform\s*\(([^()]*)\)\s*;", text)
    if not match:
        return False
    values = [float(x) for x in match.group(1).split()]
    return len(values) == 3 and all(close(a, b, 1e-10) for a, b in zip(values, expected))


def boundary_roles(mesh: str) -> dict:
    clean = re.sub(r"/\*.*?\*/|//[^\n]*", "", mesh, flags=re.S)
    number = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
    vertices = [tuple(float(x) for x in row) for row in re.findall(
        rf"\(\s*({number})\s+({number})\s+({number})\s*\)", paren_section(clean, "vertices"))]
    boundary = paren_section(clean, "boundary")
    roles = {"axis": [], "wall": [], "wedge": [], "inlet": [], "outlet": []}
    for name, content in re.findall(r'([A-Za-z_][\w.-]*)\s*\{([^{}]*)\}', boundary, re.S):
        faces = paren_section(content, "faces")
        indices = [int(x) for x in re.findall(r"\d+", faces)]
        if not indices or any(i >= len(vertices) for i in indices):
            raise ValueError("invalid boundary face")
        coords = [vertices[i] for i in indices]
        if has_entry(content, "type", "empty") and all(math.hypot(v[1], v[2]) < 1e-9 for v in coords):
            role = "axis"
        elif has_entry(content, "type", "wall") and all((close(math.hypot(v[1], v[2]), RADIUS, 1e-7) or close(math.hypot(v[1], v[2]) * math.cos(math.radians(2.5)), RADIUS, 1e-7)) for v in coords):
            role = "wall"
        elif has_entry(content, "type", "wedge"):
            role = "wedge"
        elif has_entry(content, "type", "patch") and all(close(v[0], 0.0, 1e-9) for v in coords):
            role = "inlet"
        elif has_entry(content, "type", "patch") and all(close(v[0], 5.0, 1e-9) for v in coords):
            role = "outlet"
        else:
            raise ValueError("boundary does not match required pipe geometry")
        roles[role].append(name)
    if any(len(roles[k]) != n for k, n in (("axis", 1), ("wall", 1), ("wedge", 2), ("inlet", 1), ("outlet", 1))):
        raise ValueError("required boundary roles missing or ambiguous")
    return roles


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    velocity = read(CASE / "0/U")
    pressure = read(CASE / "0/p")
    physical_path = CASE / "constant/physicalProperties"
    if not physical_path.is_file():
        physical_path = CASE / "constant/transportProperties"
    physical = read(physical_path)
    momentum = read(CASE / "constant/momentumTransport")
    control = read(CASE / "system/controlDict")
    schemes = read(CASE / "system/fvSchemes")
    if not wedge_geometry_is_valid(mesh) or re.search(r"\(\s*500\s+(?:40\s+1|1\s+40)\s*\)", mesh) is None:
        return False
    roles = boundary_roles(mesh)
    axis, wall, inlet, outlet = (roles[k][0] for k in ("axis", "wall", "inlet", "outlet"))
    wall_velocity = patch(velocity, wall)
    wall_no_slip = has_entry(wall_velocity, "type", "noSlip") or (
        has_entry(wall_velocity, "type", "fixedValue") and uniform_vector(wall_velocity, (0.0, 0.0, 0.0)))
    outlet_pressure = patch(pressure, outlet)
    pressure_zero = re.search(r"\bvalue\s+uniform\s+([^;]+);", outlet_pressure)
    return all((
        has_entry(patch(velocity, axis, "empty"), "type", "empty"),
        has_entry(patch(pressure, axis, "empty"), "type", "empty"),
        has_entry(patch(velocity, inlet), "type", "fixedValue"),
        uniform_vector(patch(velocity, inlet), (1.0, 0.0, 0.0)),
        has_entry(patch(velocity, outlet), "type", "zeroGradient"),
        wall_no_slip,
        all(has_entry(patch(velocity, n, "wedge"), "type", "wedge") and has_entry(patch(pressure, n, "wedge"), "type", "wedge") for n in roles["wedge"]),
        has_entry(patch(pressure, inlet), "type", "zeroGradient"),
        has_entry(outlet_pressure, "type", "fixedValue"),
        bool(pressure_zero) and close(float(pressure_zero.group(1)), 0.0, 1e-10),
        has_entry(patch(pressure, wall), "type", "zeroGradient"),
        has_entry(physical, "viscosityModel", "constant"),
        close(scalar_entry(physical, "nu"), 1e-4, 1e-12),
        re.search(r"\bnu\s+\[\s*0\s+2\s+-1\s+0\s+0\s+0\s+0\s*\]", physical) is not None,
        has_entry(momentum, "simulationType", "laminar"),
        close(scalar_entry(control, "endTime"), 2000.0, 1e-9),
        close(scalar_entry(control, "writeInterval"), 2000.0, 1e-9),
        has_entry(schemes, "div(phi,U)", r"bounded\s+Gauss\s+linearUpwind\s+grad\(U\)"),
    ))


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
        if any(not math.isclose(a, b, rel_tol=5.0e-6, abs_tol=5.0e-7) for a, b in zip(actual[:2], expected[:2])):
            return False
        rounded_radius_reference = 2.0 * U_BULK * (1.0 - (actual[0] / RADIUS) ** 2)
        if not any(math.isclose(actual[2], reference, rel_tol=5.0e-6, abs_tol=5.0e-7) for reference in (expected[2], rounded_radius_reference)):
            return False

    values = [line.strip() for line in read(ROOT / "summary.txt").splitlines() if line.strip()]
    if len(values) != 1:
        return False
    reported = float(values[0])
    return math.isfinite(reported) and math.isclose(reported, u_max, rel_tol=5.0e-6, abs_tol=5.0e-7)


def main() -> int:
    try:
        result = check()
    except Exception:
        result = False
    print("True" if result else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
