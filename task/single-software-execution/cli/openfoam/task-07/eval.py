#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "cylinder"
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


def face_count(block: str) -> int:
    match = re.search(r"\bfaces\s*\((.*?)\)\s*;", block, re.S)
    return len(re.findall(r"\([^()]+\)", match.group(1))) if match else 0


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
    values = []
    header = None
    for line in read(COEFFICIENTS).splitlines():
        stripped = line.strip()
        if stripped.startswith("# Time"):
            header = " ".join(stripped.split())
            continue
        if not stripped or stripped.startswith("#"):
            continue
        row = [float(value) for value in stripped.split()]
        if len(row) >= 4:
            values.append((row[0], row[2], row[3]))
    if header != "# Time Cm Cd Cl Cl(f) Cl(r)":
        raise ValueError("unexpected OpenFOAM 11 forceCoeffs header")
    return values


def history_is_complete(history: list[tuple[float, float, float]]) -> bool:
    if len(history) != 8001:
        return False
    return all(
        close(time, index * 0.0025, 5.0e-10)
        and math.isfinite(cd)
        and math.isfinite(cl)
        for index, (time, cd, cl) in enumerate(history)
    )


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    velocity = read(CASE / "0/U")
    pressure = read(CASE / "0/p")
    physical = read(CASE / "constant/physicalProperties")
    momentum = read(CASE / "constant/momentumTransport")
    control = read(CASE / "system/controlDict")
    schemes = read(CASE / "system/fvSchemes")
    solution = read(CASE / "system/fvSolution")
    mesh_boundary = mesh
    forces = named_block(named_block(control, "functions"), "forces")
    pimple = named_block(solution, "PIMPLE")
    return all(
        (
            mesh.count("hex (") == 8,
            mesh.count("(40 12 1)") == 8,
            mesh.count("simpleGrading (10 1 1)") == 8,
            mesh.count("arc ") == 32,
            face_count(named_block(mesh_boundary, "inlet")) == 4,
            face_count(named_block(mesh_boundary, "outlet")) == 4,
            face_count(named_block(mesh_boundary, "cylinder")) == 8,
            has_entry(named_block(mesh_boundary, "cylinder"), "type", r"wall"),
            has_entry(named_block(mesh_boundary, "frontAndBack"), "type", r"empty"),
            "internalField uniform (1 0.01 0);" in velocity,
            has_entry(patch(velocity, "inlet"), "value", r"uniform\s+\(1(?:\.0+)?\s+0(?:\.0+)?\s+0(?:\.0+)?\)"),
            has_entry(patch(velocity, "outlet"), "type", r"zeroGradient"),
            has_entry(patch(velocity, "cylinder"), "type", r"noSlip"),
            has_entry(patch(velocity, "frontAndBack"), "type", r"empty"),
            has_entry(patch(pressure, "inlet"), "type", r"zeroGradient"),
            has_entry(patch(pressure, "outlet"), "type", r"fixedValue"),
            has_entry(patch(pressure, "outlet"), "value", r"uniform\s+0(?:\.0+)?"),
            has_entry(patch(pressure, "frontAndBack"), "type", r"empty"),
            re.search(r"\bnu\s+\[0 2 -1 0 0 0 0\]\s+1e-?3\s*;", physical, re.I)
            is not None,
            "simulationType laminar;" in momentum,
            re.search(r"\bendTime\s+20\s*;", control) is not None,
            re.search(r"\bdeltaT\s+0\.0025\s*;", control) is not None,
            re.search(r"\bwriteFormat\s+ascii\s*;", control) is not None,
            has_entry(named_block(schemes, "divSchemes"), "div(phi,U)", r"bounded\s+Gauss\s+linearUpwind\s+grad\(U\)"),
            has_entry(pimple, "nOuterCorrectors", r"1"),
            has_entry(pimple, "nCorrectors", r"2"),
            has_entry(forces, "type", r"forceCoeffs"),
            has_entry(forces, "writeControl", r"timeStep"),
            has_entry(forces, "writeInterval", r"1"),
            has_entry(forces, "patches", r"\(\s*cylinder\s*\)"),
            has_entry(forces, "rhoInf", r"1(?:\.0+)?"),
            has_entry(forces, "magUInf", r"1(?:\.0+)?"),
            has_entry(forces, "lRef", r"0\.1"),
            has_entry(forces, "Aref", r"0\.001"),
            has_entry(forces, "dragDir", r"\(1(?:\.0+)?\s+0(?:\.0+)?\s+0(?:\.0+)?\)"),
            has_entry(forces, "liftDir", r"\(0(?:\.0+)?\s+1(?:\.0+)?\s+0(?:\.0+)?\)"),
        )
    )


def check() -> bool:
    required = (
        ROOT / "build_case.py",
        ROOT / "postprocess.py",
        ROOT / "summary.txt",
        ROOT / "lift_history.csv",
        CASE / "log.blockMesh",
        CASE / "log.pimpleFoam",
        CASE / "20/U",
        CASE / "20/p",
        COEFFICIENTS,
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    if not python_script_is_valid(
        ROOT / "build_case.py",
        ("cylinder", "blockMeshDict", "controlDict", "forceCoeffs", "0/U", "0/p"),
    ):
        return False
    if not python_script_is_valid(
        ROOT / "postprocess.py",
        ("forceCoeffs.dat", "lift_history.csv", "summary.txt", "zero_crossings", "cl_rms"),
    ):
        return False
    solve_log = read(CASE / "log.pimpleFoam")
    if not log_finished(CASE / "log.blockMesh") or not log_finished(CASE / "log.pimpleFoam") or "Time = 20" not in solve_log:
        return False
    mesh_check = subprocess.run(
        ["bash", "-lc", ". /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/cylinder"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if mesh_check.returncode != 0 or "Mesh OK." not in mesh_check.stdout or not check_case():
        return False
    velocity = internal_field(CASE / "20/U", "vector")
    pressure = internal_field(CASE / "20/p", "scalar")
    if not (len(velocity) == len(pressure) == 3840):
        return False

    history = coefficient_history()
    if not history_is_complete(history):
        return False
    window = [row for row in history if 10.0 <= row[0] <= 20.0]
    cl_mean = sum(row[2] for row in window) / len(window)
    cl_rms = math.sqrt(sum((row[2] - cl_mean) ** 2 for row in window) / len(window))
    zero_crossings = sum(
        (left[2] - cl_mean) * (right[2] - cl_mean) < 0
        for left, right in zip(window, window[1:])
    )
    cl_max = max(abs(row[2]) for row in window)
    if not (0.05 < cl_max < 3.0 and cl_rms > 0.05 and zero_crossings >= 5):
        return False

    keys = ("time_s", "cd", "cl")
    with (ROOT / "lift_history.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != len(history) or set(rows[0]) != set(keys):
        return False
    for row, expected in zip(rows, history):
        actual = tuple(float(row[key]) for key in keys)
        if any(not close(a, b, 5.0e-7) for a, b in zip(actual, expected)):
            return False

    values = [line.strip() for line in read(ROOT / "summary.txt").splitlines() if line.strip()]
    if len(values) != 1:
        return False
    reported = float(values[0])
    return math.isfinite(reported) and abs(reported - cl_max) <= 5.0e-7


def main() -> int:
    try:
        result = check()
    except Exception:
        result = False
    print("True" if result else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
