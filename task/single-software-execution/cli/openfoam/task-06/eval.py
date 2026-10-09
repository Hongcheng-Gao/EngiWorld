#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "plate"
U_REF = 10.0
NU = 1.5e-5
STATION = 0.5


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


def patch_vectors(path: Path, patch_name: str) -> list[tuple[float, float, float]]:
    text = read(path)
    header = named_block(text, "FoamFile")
    patch_block = patch(text, patch_name)
    match = re.search(
        r"\bvalue\s+nonuniform\s+List<vector>\s+(\d+)\s*\((.*?)\)\s*;",
        patch_block,
        re.S,
    )
    if not match:
        raise ValueError(f"missing {patch_name} vectors")
    values = [
        tuple(float(value) for value in item.split())
        for item in re.findall(r"\(([^()]+)\)", match.group(2))
    ]
    if (
        len(values) != int(match.group(1))
        or not all(
            len(value) == 3 and all(math.isfinite(item) for item in value)
            for value in values
        )
        or not has_entry(header, "format", r"ascii")
        or not has_entry(header, "class", r"volVectorField")
        or not has_entry(header, "object", re.escape(path.name))
    ):
        raise ValueError(f"{patch_name} vector count mismatch")
    return values


def downstream_station_sample(rows: list[tuple[float, ...]]) -> tuple[float, ...]:
    candidates = [row for row in rows if row[0] >= STATION]
    if not candidates:
        raise ValueError("missing downstream station sample")
    return min(candidates, key=lambda row: (abs(row[0] - STATION), row[0]))


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
            "(-0.2 0 0)" in mesh,
            "(1 0.2 0)" in mesh,
            "(40 60 1)" in mesh,
            "(200 60 1)" in mesh,
            mesh.count("simpleGrading (1 50 1)") == 2,
            has_entry(named_block(mesh, "upstreamBottom"), "type", r"symmetryPlane"),
            has_entry(named_block(mesh, "plate"), "type", r"wall"),
            has_entry(named_block(mesh, "frontAndBack"), "type", r"empty"),
            all(has_entry(patch(velocity, name), "value", r"uniform\s+\(10(?:\.0+)?\s+0(?:\.0+)?\s+0(?:\.0+)?\)") for name in ("inlet", "freeStream")),
            has_entry(patch(velocity, "outlet"), "type", r"zeroGradient"),
            has_entry(patch(velocity, "upstreamBottom"), "type", r"symmetryPlane"),
            has_entry(patch(velocity, "plate"), "type", r"noSlip"),
            has_entry(patch(velocity, "frontAndBack"), "type", r"empty"),
            has_entry(patch(pressure, "outlet"), "type", r"fixedValue"),
            has_entry(patch(pressure, "outlet"), "value", r"uniform\s+0(?:\.0+)?"),
            has_entry(patch(pressure, "upstreamBottom"), "type", r"symmetryPlane"),
            has_entry(patch(pressure, "frontAndBack"), "type", r"empty"),
            re.search(r"\bnu\s+\[0 2 -1 0 0 0 0\]\s+1\.5e-?5\s*;", physical, re.I)
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
        ROOT / "plate_shear.csv",
        CASE / "log.blockMesh",
        CASE / "log.simpleFoam",
        CASE / "log.cellCentres",
        CASE / "log.wallShearStress",
        CASE / "2000/C",
        CASE / "2000/U",
        CASE / "2000/p",
        CASE / "2000/wallShearStress",
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    if not python_script_is_valid(
        ROOT / "build_case.py",
        ("plate", "blockMeshDict", "controlDict", "fvSchemes", "fvSolution", "0/U", "0/p"),
    ):
        return False
    if not python_script_is_valid(
        ROOT / "postprocess.py",
        ("plate", "2000", "wallShearStress", "plate_shear.csv", "summary.txt", "STATION"),
    ):
        return False
    solve_log = read(CASE / "log.simpleFoam")
    if any(not log_finished(path) for path in (CASE / "log.blockMesh", CASE / "log.cellCentres", CASE / "log.wallShearStress")):
        return False
    if not log_finished(CASE / "log.simpleFoam") or "Time = 2000" not in solve_log:
        return False
    mesh_check = subprocess.run(
        ["bash", "-lc", ". /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/plate"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if mesh_check.returncode != 0 or "Mesh OK." not in mesh_check.stdout or not check_case():
        return False

    centres_internal = internal_field(CASE / "2000/C", "vector")
    velocity = internal_field(CASE / "2000/U", "vector")
    pressure = internal_field(CASE / "2000/p", "scalar")
    if not (len(centres_internal) == len(velocity) == len(pressure) == 14400):
        return False

    centres = patch_vectors(CASE / "2000/C", "plate")
    shear = patch_vectors(CASE / "2000/wallShearStress", "plate")
    if len(centres) != 200 or len(shear) != 200:
        return False
    calculated = []
    for centre, stress in sorted(zip(centres, shear), key=lambda item: item[0][0]):
        x = centre[0]
        tau_x = stress[0]
        cf = 2.0 * abs(tau_x) / U_REF**2
        theory = 0.664 / math.sqrt(U_REF * x / NU)
        error_percent = abs(cf - theory) / theory * 100.0
        calculated.append((x, tau_x, cf, theory, error_percent))
    sample = downstream_station_sample(calculated)
    if abs(sample[0] - STATION) > 0.003 or not (8e-4 < sample[2] < 1.5e-3 and sample[4] <= 15.0):
        return False

    keys = ("x_m", "wall_shear_kinematic_m2ps2", "cf", "blasius_cf", "error_percent")
    with (ROOT / "plate_shear.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 200 or set(rows[0]) != set(keys):
        return False
    for row, expected in zip(rows, calculated):
        actual = tuple(float(row[key]) for key in keys)
        if any(not close(a, b, 5.0e-7) for a, b in zip(actual, expected)):
            return False

    values = [item.strip() for item in read(ROOT / "summary.txt").strip().split(",")]
    if len(values) != 2:
        return False
    reported = tuple(float(value) for value in values)
    return all(math.isfinite(value) for value in reported) and all(
        abs(actual - expected) <= 5.0e-7
        for actual, expected in zip(reported, (sample[2], sample[4]))
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
