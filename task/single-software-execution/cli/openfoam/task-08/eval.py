#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "airfoil"
COEFFICIENTS = CASE / "postProcessing/forces/0/forceCoeffs.dat"


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


def patch(text: str, name: str) -> str:
    return named_block(named_block(text, "boundaryField"), name)


def face_count(block: str) -> int:
    match = re.search(r"\bfaces\s*\((.*?)\)\s*;", block, re.S)
    return len(re.findall(r"\([^()]+\)", match.group(1))) if match else 0


def mesh_vertices(mesh: str) -> list[tuple[float, float, float]]:
    number = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
    return [
        tuple(float(value) for value in match)
        for match in re.findall(
            rf"\(\s*({number})\s+({number})\s+({number})\s*\)",
            paren_section(mesh, "vertices"),
        )
    ]


def airfoil_geometry_is_valid(mesh: str) -> bool:
    count = 161
    vertices = mesh_vertices(mesh)
    if len(vertices) != 4 * count:
        return False
    inner0 = vertices[:count]
    outer0 = vertices[count : 2 * count]
    inner1 = vertices[2 * count : 3 * count]
    outer1 = vertices[3 * count :]

    expected: list[tuple[float, float]] = []
    for index in range(81):
        x = 0.5 * (1.0 + math.cos(math.pi * index / 80.0))
        y = 5.0 * 0.12 * (
            0.2969 * math.sqrt(x)
            - 0.1260 * x
            - 0.3516 * x**2
            + 0.2843 * x**3
            - 0.1015 * x**4
        )
        expected.append((x, y))
    for index in range(79, -1, -1):
        x = 0.5 * (1.0 + math.cos(math.pi * index / 80.0))
        y = -5.0 * 0.12 * (
            0.2969 * math.sqrt(x)
            - 0.1260 * x
            - 0.3516 * x**2
            + 0.2843 * x**3
            - 0.1015 * x**4
        )
        expected.append((x, y))

    for actual, target in zip(inner0, expected):
        if abs(actual[0] - target[0]) > 2.0e-10 or abs(actual[1] - target[1]) > 2.0e-10 or abs(actual[2]) > 1.0e-12:
            return False
    for lower, upper in zip(inner0, inner1):
        if abs(lower[0] - upper[0]) > 1.0e-12 or abs(lower[1] - upper[1]) > 1.0e-12 or abs(upper[2] - 0.01) > 1.0e-12:
            return False

    for index, (x, y, _) in enumerate(inner0):
        lower_outer = outer0[index]
        upper_outer = outer1[index]
        if (
            not all(math.isfinite(value) for value in lower_outer + upper_outer)
            or abs(lower_outer[0] - upper_outer[0]) > 1.0e-10
            or abs(lower_outer[1] - upper_outer[1]) > 1.0e-10
            or abs(lower_outer[2]) > 1.0e-12
            or abs(upper_outer[2] - 0.01) > 1.0e-12
        ):
            return False
        offset_x = lower_outer[0] - x
        offset_y = lower_outer[1] - y
        if abs(math.hypot(offset_x, offset_y) - 5.0) > 5.0e-6:
            return False
        if offset_x * (x - 0.5) + offset_y * y <= 0.0:
            return False
    return True


def internal_field(path: Path, kind: str) -> list:
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


def coefficient_history() -> list[tuple[float, float, float]]:
    history = []
    header = None
    for line in read(COEFFICIENTS).splitlines():
        stripped = line.strip()
        if stripped.startswith("# Time"):
            header = " ".join(stripped.split())
            continue
        if not stripped or stripped.startswith("#"):
            continue
        values = [float(value) for value in stripped.split()]
        if len(values) >= 4:
            history.append((values[0], values[2], values[3]))
    if header != "# Time Cm Cd Cl Cl(f) Cl(r)":
        raise ValueError("unexpected OpenFOAM 11 forceCoeffs header")
    return history


def history_is_complete(history: list[tuple[float, float, float]]) -> bool:
    if len(history) != 1001:
        return False
    return all(
        close(iteration, float(index), 1.0e-9)
        and math.isfinite(cd)
        and math.isfinite(cl)
        for index, (iteration, cd, cl) in enumerate(history)
    )


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    build_script = read(ROOT / "build_case.py")
    velocity = read(CASE / "0/U")
    pressure = read(CASE / "0/p")
    kinetic = read(CASE / "0/k")
    omega = read(CASE / "0/omega")
    nut = read(CASE / "0/nut")
    physical = read(CASE / "constant/physicalProperties")
    momentum = read(CASE / "constant/momentumTransport")
    control = read(CASE / "system/controlDict")
    schemes = read(CASE / "system/fvSchemes")
    solution = read(CASE / "system/fvSolution")
    boundary = read(CASE / "constant/polyMesh/boundary")
    mesh_boundary = mesh
    forces = named_block(named_block(control, "functions"), "forces")
    simple = named_block(solution, "SIMPLE")
    return all(
        (
            airfoil_geometry_is_valid(mesh),
            mesh.count("hex (") == 161,
            len(re.findall(r"\(\s*80\s+1\s+1\s*\)\s*simpleGrading\s*\(\s*80\s+1\s+1\s*\)", mesh)) == 161,
            has_entry(named_block(mesh_boundary, "FARFIELD"), "type", r"patch"),
            has_entry(named_block(mesh_boundary, "WALL10"), "type", r"wall"),
            has_entry(named_block(mesh_boundary, "SYMP3"), "type", r"empty"),
            face_count(named_block(mesh_boundary, "FARFIELD")) == 161,
            face_count(named_block(mesh_boundary, "WALL10")) == 161,
            face_count(named_block(mesh_boundary, "SYMP3")) == 322,
            any(
                re.search(r"\binternalField\s+uniform\s+\(0\.9961946981\s+0\.08715574275\s+0(?:\.0+)?\)\s*;", text) is not None
                for text in (velocity, build_script)
            ),
            has_entry(patch(velocity, "FARFIELD"), "type", r"freestreamVelocity"),
            has_entry(patch(velocity, "FARFIELD"), "freestreamValue", r"uniform\s+\(0\.9961946981\s+0\.08715574275\s+0(?:\.0+)?\)"),
            has_entry(patch(velocity, "WALL10"), "type", r"noSlip"),
            has_entry(patch(velocity, "SYMP3"), "type", r"empty"),
            has_entry(patch(pressure, "FARFIELD"), "type", r"freestreamPressure"),
            has_entry(patch(pressure, "FARFIELD"), "freestreamValue", r"uniform\s+0(?:\.0+)?"),
            has_entry(patch(pressure, "WALL10"), "type", r"zeroGradient"),
            has_entry(patch(kinetic, "FARFIELD"), "type", r"inletOutlet"),
            has_entry(patch(kinetic, "FARFIELD"), "inletValue", r"uniform\s+0\.001"),
            has_entry(patch(kinetic, "WALL10"), "type", r"kqRWallFunction"),
            has_entry(patch(omega, "FARFIELD"), "type", r"inletOutlet"),
            has_entry(patch(omega, "FARFIELD"), "inletValue", r"uniform\s+10(?:\.0+)?"),
            has_entry(patch(omega, "WALL10"), "type", r"omegaWallFunction"),
            has_entry(patch(nut, "WALL10"), "type", r"nutkWallFunction"),
            all(has_entry(patch(field_text, "SYMP3"), "type", r"empty") for field_text in (pressure, kinetic, omega, nut)),
            re.search(r"\bnu\s+\[0 2 -1 0 0 0 0\]\s+1e-?5\s*;", physical, re.I)
            is not None,
            has_entry(momentum, "model", r"kOmegaSST"),
            re.search(r"\bendTime\s+1000\s*;", control) is not None,
            re.search(r"\bwriteFormat\s+ascii\s*;", control) is not None,
            has_entry(forces, "type", r"forceCoeffs"),
            has_entry(forces, "writeInterval", r"1"),
            has_entry(forces, "patches", r"\(\s*WALL10\s*\)"),
            has_entry(forces, "rhoInf", r"1(?:\.0+)?"),
            has_entry(forces, "magUInf", r"1(?:\.0+)?"),
            has_entry(forces, "lRef", r"1(?:\.0+)?"),
            has_entry(forces, "Aref", r"0\.01"),
            has_entry(forces, "dragDir", r"\(0\.9961946981\s+0\.08715574275\s+0(?:\.0+)?\)"),
            has_entry(forces, "liftDir", r"\(-0\.08715574275\s+0\.9961946981\s+0(?:\.0+)?\)"),
            all(has_entry(named_block(schemes, "divSchemes"), key, r"bounded\s+Gauss\s+upwind") for key in ("div(phi,U)", "div(phi,k)", "div(phi,omega)")),
            "corrected" in named_block(schemes, "laplacianSchemes"),
            has_entry(named_block(named_block(solution, "solvers"), "p"), "solver", r"GAMG"),
            has_entry(simple, "nNonOrthogonalCorrectors", r"1"),
            re.search(r"\bSYMP3\b.*?type\s+empty;", boundary, re.S) is not None,
        )
    )


def check() -> bool:
    required = (
        ROOT / "build_case.py",
        ROOT / "postprocess.py",
        ROOT / "summary.txt",
        ROOT / "force_coefficients.csv",
        CASE / "log.blockMesh",
        CASE / "log.checkMesh",
        CASE / "log.potentialFoam",
        CASE / "log.simpleFoam",
        CASE / "1000/U",
        CASE / "1000/p",
        CASE / "1000/k",
        CASE / "1000/omega",
        COEFFICIENTS,
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    if not python_script_is_valid(
        ROOT / "build_case.py",
        ("airfoil", "naca_thickness", "blockMeshDict", "forceCoeffs", "0/U", "0/p"),
    ):
        return False
    if not python_script_is_valid(
        ROOT / "postprocess.py",
        ("forceCoeffs.dat", "force_coefficients.csv", "summary.txt", "avg_cd", "avg_cl"),
    ):
        return False
    solve_log = read(CASE / "log.simpleFoam")
    if any(
        not log_finished(path)
        for path in (CASE / "log.blockMesh", CASE / "log.checkMesh", CASE / "log.potentialFoam")
    ):
        return False
    if not log_finished(CASE / "log.simpleFoam") or "Time = 1000" not in solve_log:
        return False
    mesh_check = subprocess.run(
        [
            "bash",
            "--noprofile",
            "--norc",
            "-c",
            "trap - CHLD; . /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/airfoil",
        ],
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
    velocity = internal_field(CASE / "1000/U", "vector")
    pressure = internal_field(CASE / "1000/p", "scalar")
    turbulent_k = internal_field(CASE / "1000/k", "scalar")
    omega = internal_field(CASE / "1000/omega", "scalar")
    if not (len(velocity) == len(pressure) == len(turbulent_k) == len(omega) == 12880):
        return False

    history = coefficient_history()
    if not history_is_complete(history):
        return False
    window = [row for row in history if 800.0 <= row[0] <= 1000.0]
    avg_cd = sum(row[1] for row in window) / len(window)
    avg_cl = sum(row[2] for row in window) / len(window)
    std_cd = math.sqrt(sum((row[1] - avg_cd) ** 2 for row in window) / len(window))
    std_cl = math.sqrt(sum((row[2] - avg_cl) ** 2 for row in window) / len(window))
    if not (0.1 < avg_cl < 2.0 and 0.001 < avg_cd < 0.2 and std_cl < 0.02 and std_cd < 0.01):
        return False

    keys = ("iteration", "cd", "cl")
    with (ROOT / "force_coefficients.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != len(history) or set(rows[0]) != set(keys):
        return False
    for row, expected in zip(rows, history):
        actual = tuple(float(row[key]) for key in keys)
        if any(not close(a, b, 5.0e-7) for a, b in zip(actual, expected)):
            return False

    values = [item.strip() for item in read(ROOT / "summary.txt").strip().split(",")]
    if len(values) != 2:
        return False
    reported = tuple(float(value) for value in values)
    expected = (avg_cl, avg_cd)
    return all(math.isfinite(value) for value in reported) and all(
        abs(actual - target) <= 5.0e-7 for actual, target in zip(reported, expected)
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
