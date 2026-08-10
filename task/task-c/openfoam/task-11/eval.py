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


def patch(text: str, name: str) -> str:
    return named_block(named_block(text, "boundaryField"), name)


def ordered_tokens(text: str, tokens: tuple[str, ...]) -> bool:
    position = -1
    for token in tokens:
        position = text.find(token, position + 1)
        if position < 0:
            return False
    return True


def vectors(path: Path) -> list[tuple[float, float, float]]:
    match = re.search(
        r"internalField\s+nonuniform\s+List<vector>\s+\d+\s*\((.*?)\)\s*;",
        read(path),
        re.S,
    )
    if not match:
        raise ValueError(f"missing vector field: {path}")
    return [
        tuple(float(value) for value in item.split())
        for item in re.findall(r"\(([^()]+)\)", match.group(1))
    ]


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
            "(1 1 0.01)" in mesh,
            "(50 50 1)" in mesh,
            has_entry(patch(velocity, "movingWall"), "value", r"uniform\s+\(1(?:\.0+)?\s+0(?:\.0+)?\s+0(?:\.0+)?\)"),
            has_entry(patch(velocity, "fixedWalls"), "type", r"noSlip"),
            has_entry(patch(velocity, "frontAndBack"), "type", r"empty"),
            has_entry(patch(pressure, "movingWall"), "type", r"zeroGradient"),
            has_entry(patch(pressure, "fixedWalls"), "type", r"zeroGradient"),
            has_entry(patch(pressure, "frontAndBack"), "type", r"empty"),
            match is not None and abs(float(match.group(1)) - 1.0 / reynolds) < 1.0e-12,
            re.search(r"\bendTime\s+30\s*;", control) is not None,
            re.search(r"\bdeltaT\s+0\.005\s*;", control) is not None,
            re.search(r"\bwriteInterval\s+6000\s*;", control) is not None,
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
    run_script = read(ROOT / "run_sweep.py")
    if not (
        re.search(r"for\s+\w+\s+in\s*\(\s*100\s*,\s*400\s*,\s*1000\s*\)", run_script)
        and ordered_tokens(run_script, ('"blockMesh"', '"checkMesh"', '"icoFoam"', '"postProcess"'))
        and all(token in run_script for token in ('"-latestTime"', '"-func"', '"writeCellCentres"'))
    ):
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
        if any("End" not in read(path) for path in required[:4]):
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
        if any(abs(a - b) > 5.0e-7 for a, b in zip(actual, calculated[reynolds])):
            return False

    lines = [line.strip() for line in read(ROOT / "summary.txt").splitlines() if line.strip()]
    if len(lines) != 3:
        return False
    for line, reynolds in zip(lines, REYNOLDS):
        parts = [item.strip() for item in line.split(",")]
        if len(parts) != 2 or int(parts[0]) != reynolds:
            return False
        if abs(float(parts[1]) - calculated[reynolds][1]) > 5.0e-7:
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
