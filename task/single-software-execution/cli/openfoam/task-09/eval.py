#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "heat"


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


def completed_log(path: Path, required_fragment: str | None = None) -> bool:
    text = read(path)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return (
        bool(lines)
        and lines[-1] == "End"
        and "FOAM FATAL" not in text
        and (required_fragment is None or required_fragment in text)
    )


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


def nearest_cell(centres: list[tuple[float, float, float]], x: float, y: float) -> int:
    return min(
        range(len(centres)),
        key=lambda index: (
            (centres[index][0] - x) ** 2 + (centres[index][1] - y) ** 2,
            centres[index][0],
            centres[index][1],
            centres[index][2],
        ),
    )


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    initial = read(CASE / "0/T")
    physical = read(CASE / "constant/physicalProperties")
    control = read(CASE / "system/controlDict")
    schemes = read(CASE / "system/fvSchemes")
    return all(
        (
            "(1 0.5 0)" in mesh,
            "(200 20 1)" in mesh,
            has_entry(named_block(mesh, "hot"), "type", r"wall"),
            face_count(named_block(mesh, "hot")) == 1,
            has_entry(named_block(mesh, "cold"), "type", r"wall"),
            face_count(named_block(mesh, "cold")) == 1,
            has_entry(named_block(mesh, "adiabatic"), "type", r"wall"),
            face_count(named_block(mesh, "adiabatic")) == 2,
            has_entry(named_block(mesh, "frontAndBack"), "type", r"empty"),
            face_count(named_block(mesh, "frontAndBack")) == 2,
            re.search(r"\binternalField\s+uniform\s+350(?:\.0+)?\s*;", initial) is not None,
            has_entry(patch(initial, "hot"), "value", r"uniform\s+400(?:\.0+)?"),
            has_entry(patch(initial, "cold"), "value", r"uniform\s+300(?:\.0+)?"),
            has_entry(patch(initial, "adiabatic"), "type", r"zeroGradient"),
            has_entry(patch(initial, "frontAndBack"), "type", r"empty"),
            "DT DT [0 2 -1 0 0 0 0] 0.01;" in physical,
            re.search(r"\bendTime\s+50\s*;", control) is not None,
            re.search(r"\bdeltaT\s+0\.05\s*;", control) is not None,
            re.search(r"\bwriteControl\s+runTime\s*;", control) is not None,
            re.search(r"\bwriteInterval\s+50(?:\.0+)?\s*;", control) is not None,
            re.search(r"\bwriteFormat\s+ascii\s*;", control) is not None,
            has_entry(named_block(schemes, "ddtSchemes"), "default", r"Euler"),
            "laplacian(DT,T) Gauss linear corrected;" in schemes,
        )
    )


def check() -> bool:
    required = (
        ROOT / "build_case.py",
        ROOT / "postprocess.py",
        ROOT / "summary.txt",
        ROOT / "temperature_profile.csv",
        CASE / "log.blockMesh",
        CASE / "log.laplacianFoam",
        CASE / "log.cellCentres",
        CASE / "50/C",
        CASE / "50/T",
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    if not python_script_is_valid(
        ROOT / "build_case.py",
        ("heat", "blockMeshDict", "physicalProperties", "laplacianFoam", "0/T"),
    ):
        return False
    if not python_script_is_valid(
        ROOT / "postprocess.py",
        ("heat", "50/C", "50/T", "temperature_profile.csv", "summary.txt"),
    ):
        return False
    if not all(
        (
            completed_log(CASE / "log.blockMesh"),
            completed_log(CASE / "log.laplacianFoam", "Time = 50"),
            completed_log(CASE / "log.cellCentres"),
        )
    ):
        return False
    mesh_check = subprocess.run(
        ["bash", "-lc", ". /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/heat"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if mesh_check.returncode != 0 or "Mesh OK." not in mesh_check.stdout or not check_case():
        return False

    centres = internal_field(CASE / "50/C", "vector")
    temperature = internal_field(CASE / "50/T", "scalar")
    if len(centres) != 4000 or len(temperature) != 4000:
        return False
    theoretical = [400.0 - 100.0 * centre[0] for centre in centres]
    rms_error = math.sqrt(sum((value - theory) ** 2 for value, theory in zip(temperature, theoretical)) / len(temperature))
    if rms_error > 1.0:
        return False
    target_a = nearest_cell(centres, 0.25, 0.25)
    target_b = nearest_cell(centres, 0.75, 0.25)
    if max(abs(centres[target_a][0] - 0.25), abs(centres[target_b][0] - 0.75)) > 0.006:
        return False

    centerline_y = min({centre[1] for centre in centres}, key=lambda value: (abs(value - 0.25), value))
    centerline = sorted(
        (i for i, centre in enumerate(centres) if abs(centre[1] - centerline_y) < 1e-9),
        key=lambda i: centres[i][0],
    )
    keys = ("x_m", "temperature_K", "linear_theory_K")
    with (ROOT / "temperature_profile.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 200 or set(rows[0]) != set(keys):
        return False
    expected_rows = [(centres[i][0], temperature[i], theoretical[i]) for i in centerline]
    for row, expected in zip(rows, expected_rows):
        actual = tuple(float(row[key]) for key in keys)
        if any(not close(a, b, 5.0e-7) for a, b in zip(actual, expected)):
            return False

    values = [item.strip() for item in read(ROOT / "summary.txt").strip().split(",")]
    if len(values) != 2:
        return False
    reported = tuple(float(value) for value in values)
    expected = (temperature[target_a], temperature[target_b])
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
