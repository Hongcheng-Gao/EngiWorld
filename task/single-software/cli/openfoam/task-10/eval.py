#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "buoyant"
TIME = CASE / "1000"


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


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    temperature = read(CASE / "0/T")
    velocity = read(CASE / "0/U")
    pressure = read(CASE / "0/p")
    physical = read(CASE / "constant/physicalProperties")
    momentum = read(CASE / "constant/momentumTransport")
    gravity = read(CASE / "constant/g")
    control = read(CASE / "system/controlDict")
    schemes = read(CASE / "system/fvSchemes")
    solution = read(CASE / "system/fvSolution")
    boundary = read(CASE / "constant/polyMesh/boundary")
    return all(
        (
            "(0.1 0.1 0.01)" in mesh,
            "(41 41 1)" in mesh,
            has_entry(named_block(mesh, "hot"), "type", r"wall"),
            face_count(named_block(mesh, "hot")) == 1,
            has_entry(named_block(mesh, "cold"), "type", r"wall"),
            face_count(named_block(mesh, "cold")) == 1,
            has_entry(named_block(mesh, "topAndBottom"), "type", r"wall"),
            face_count(named_block(mesh, "topAndBottom")) == 2,
            has_entry(named_block(mesh, "frontAndBack"), "type", r"empty"),
            face_count(named_block(mesh, "frontAndBack")) == 2,
            re.search(r"\binternalField\s+uniform\s+300(?:\.0+)?\s*;", temperature) is not None,
            has_entry(patch(temperature, "hot"), "value", r"uniform\s+310(?:\.0+)?"),
            has_entry(patch(temperature, "cold"), "value", r"uniform\s+290(?:\.0+)?"),
            has_entry(patch(temperature, "topAndBottom"), "type", r"zeroGradient"),
            has_entry(patch(temperature, "frontAndBack"), "type", r"empty"),
            re.search(r"\binternalField\s+uniform\s+\(0(?:\.0+)?\s+0(?:\.0+)?\s+0(?:\.0+)?\)\s*;", velocity) is not None,
            all(has_entry(patch(velocity, name), "type", r"noSlip") for name in ("hot", "cold", "topAndBottom")),
            has_entry(patch(velocity, "frontAndBack"), "type", r"empty"),
            re.search(r"\binternalField\s+uniform\s+100000(?:\.0+)?\s*;", pressure) is not None,
            re.search(r"\bmolWeight\s+28\.96\s*;", physical) is not None,
            re.search(r"\bCp\s+1004\.4\s*;", physical) is not None,
            re.search(r"\bmu\s+1\.846e-0?5\s*;", physical, re.I) is not None,
            re.search(r"\bPr\s+0\.71\s*;", physical) is not None,
            "simulationType laminar;" in momentum,
            "value (0 -9.81 0);" in gravity,
            re.search(r"\bendTime\s+1000\s*;", control) is not None,
            re.search(r"\bwriteInterval\s+1000\s*;", control) is not None,
            re.search(r"\bapplication\s+foamRun\s*;", control) is not None,
            re.search(r"\bsolver\s+fluid\s*;", control) is not None,
            re.search(r"\bwriteFormat\s+ascii\s*;", control) is not None,
            has_entry(named_block(schemes, "ddtSchemes"), "default", r"steadyState"),
            has_entry(named_block(schemes, "divSchemes"), "div(phi,U)", r"bounded\s+Gauss\s+upwind"),
            has_entry(named_block(schemes, "divSchemes"), "div(phi,h)", r"bounded\s+Gauss\s+upwind"),
            has_entry(named_block(named_block(solution, "solvers"), "p_rgh"), "solver", r"GAMG"),
            re.search(r"\bfrontAndBack\b.*?type\s+empty;", boundary, re.S)
            is not None,
        )
    )


def check() -> bool:
    required = (
        ROOT / "build_case.py",
        ROOT / "postprocess.py",
        ROOT / "summary.txt",
        ROOT / "center_sample.csv",
        CASE / "log.blockMesh",
        CASE / "log.checkMesh",
        CASE / "log.foamRun",
        CASE / "log.cellCentres",
        TIME / "T",
        TIME / "U",
        TIME / "p",
        TIME / "p_rgh",
        TIME / "C",
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    if not python_script_is_valid(
        ROOT / "build_case.py",
        ("buoyant", "blockMeshDict", "physicalProperties", "foamRun", "p_rgh", "0/T", "0/U"),
    ):
        return False
    if not python_script_is_valid(
        ROOT / "postprocess.py",
        ("buoyant", "1000", "center_sample.csv", "summary.txt", "max_speed"),
    ):
        return False
    if not all(
        (
            completed_log(CASE / "log.blockMesh"),
            completed_log(CASE / "log.checkMesh"),
            completed_log(CASE / "log.foamRun", "Time = 1000"),
            completed_log(CASE / "log.cellCentres"),
        )
    ):
        return False
    mesh_check = subprocess.run(
        [
            "bash",
            "--noprofile",
            "--norc",
            "-c",
            "trap - CHLD; . /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/buoyant",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if mesh_check.returncode != 0 or "Mesh OK." not in mesh_check.stdout or not check_case():
        return False

    centres = internal_field(TIME / "C", "vector")
    temperatures = internal_field(TIME / "T", "scalar")
    velocity = internal_field(TIME / "U", "vector")
    pressure = internal_field(TIME / "p", "scalar")
    pressure_rgh = internal_field(TIME / "p_rgh", "scalar")
    if not (
        len(centres)
        == len(temperatures)
        == len(velocity)
        == len(pressure)
        == len(pressure_rgh)
        == 1681
    ):
        return False
    target = (0.05, 0.05, 0.005)
    index = min(
        range(len(centres)),
        key=lambda i: sum((centres[i][j] - target[j]) ** 2 for j in range(3)),
    )
    point = centres[index]
    if math.sqrt(sum((point[j] - target[j]) ** 2 for j in range(3))) > 1.0e-9:
        return False
    center_temp = temperatures[index]
    max_speed = max(math.sqrt(sum(component**2 for component in item)) for item in velocity)
    if not (
        295.0 < center_temp < 305.0
        and min(temperatures) > 289.0
        and max(temperatures) < 311.0
        and max(temperatures) - min(temperatures) > 15.0
        and 1.0e-4 < max_speed < 1.0
    ):
        return False

    with (ROOT / "center_sample.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1 or set(rows[0]) != {
        "x",
        "y",
        "z",
        "temperature_k",
        "max_speed_m_s",
    }:
        return False
    row = rows[0]
    sample = tuple(float(row[key]) for key in ("x", "y", "z"))
    if any(not close(a, b, 1.0e-10) for a, b in zip(sample, point)):
        return False
    if not close(float(row["temperature_k"]), center_temp, 5.0e-7):
        return False
    if not close(float(row["max_speed_m_s"]), max_speed, 5.0e-7):
        return False

    reported = float(read(ROOT / "summary.txt").strip())
    return math.isfinite(reported) and abs(reported - center_temp) <= 5.0e-7


def main() -> int:
    try:
        result = check()
    except Exception:
        result = False
    print("True" if result else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
