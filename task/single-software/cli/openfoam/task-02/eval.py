#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "cavity"


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


def vectors(path: Path) -> list[tuple[float, float, float]]:
    text = read(path)
    header = named_block(text, "FoamFile")
    match = re.search(
        r"internalField\s+nonuniform\s+List<vector>\s+(\d+)\s*\((.*?)\)\s*;",
        text,
        re.S,
    )
    if not match:
        raise ValueError(f"missing vector field in {path}")
    values = [
        tuple(float(value) for value in item.split())
        for item in re.findall(r"\(([^()]+)\)", match.group(2))
    ]
    if (
        len(values) != int(match.group(1))
        or not values
        or not all(len(value) == 3 and all(math.isfinite(item) for item in value) for value in values)
        or not has_entry(header, "class", r"volVectorField")
        or not has_entry(header, "object", re.escape(path.name))
    ):
        raise ValueError("invalid vector field")
    return values


def latest_time() -> Path:
    times = sorted(
        (float(path.name), path)
        for path in CASE.iterdir()
        if path.is_dir() and re.fullmatch(r"\d+(?:\.\d+)?", path.name)
    )
    if not times or abs(times[-1][0] - 30.0) > 1.0e-9:
        raise ValueError("final time must be 30 s")
    return times[-1][1]


def nearest(
    centres: list[tuple[float, float, float]],
    velocity: list[tuple[float, float, float]],
    point: tuple[float, float, float],
) -> tuple[float, float, float]:
    indices = sorted(
        range(len(centres)),
        key=lambda i: sum((centres[i][j] - point[j]) ** 2 for j in range(3)),
    )[:4]
    return tuple(sum(velocity[i][j] for i in indices) / 4.0 for j in range(3))


def velocity_signs_are_valid(
    calculated: dict[str, tuple[float, float, float]],
) -> bool:
    return (
        calculated["center"][0] < 0.0
        and calculated["left_mid"][1] > 0.0
        and calculated["right_mid"][1] < 0.0
    )


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    velocity = read(CASE / "0/U")
    pressure = read(CASE / "0/p")
    physical = read(CASE / "constant/physicalProperties")
    control = read(CASE / "system/controlDict")
    schemes = read(CASE / "system/fvSchemes")
    solution = read(CASE / "system/fvSolution")
    u_boundary = named_block(velocity, "boundaryField")
    p_boundary = named_block(pressure, "boundaryField")
    moving_u = named_block(u_boundary, "movingWall")
    walls_u = named_block(u_boundary, "fixedWalls")
    empty_u = named_block(u_boundary, "frontAndBack")
    moving_p = named_block(p_boundary, "movingWall")
    walls_p = named_block(p_boundary, "fixedWalls")
    empty_p = named_block(p_boundary, "frontAndBack")
    piso = named_block(solution, "PISO")
    return all(
        (
            "(1 1 0)" in mesh,
            "(1 1 0.01)" in mesh,
            "(50 50 1)" in mesh,
            "type empty;" in mesh,
            has_entry(moving_u, "type", r"fixedValue"),
            has_entry(moving_u, "value", r"uniform\s+\(1(?:\.0+)?\s+0(?:\.0+)?\s+0(?:\.0+)?\)"),
            has_entry(walls_u, "type", r"noSlip"),
            has_entry(empty_u, "type", r"empty"),
            has_entry(moving_p, "type", r"zeroGradient"),
            has_entry(walls_p, "type", r"zeroGradient"),
            has_entry(empty_p, "type", r"empty"),
            re.search(r"\bnu\s+\[0 2 -1 0 0 0 0\]\s+1(?:\.0)?e-?3\s*;", physical, re.I)
            is not None,
            re.search(r"\bendTime\s+30(?:\.0)?\s*;", control) is not None,
            re.search(r"\bdeltaT\s+0\.005\s*;", control) is not None,
            re.search(r"\bwriteInterval\s+1000\s*;", control) is not None,
            re.search(r"\bwriteFormat\s+ascii\s*;", control) is not None,
            has_entry(named_block(schemes, "ddtSchemes"), "default", r"Euler"),
            has_entry(named_block(schemes, "divSchemes"), "div(phi,U)", r"Gauss\s+linear"),
            has_entry(piso, "pRefCell", r"0"),
            has_entry(piso, "pRefValue", r"0(?:\.0+)?"),
        )
    )


def check() -> bool:
    required = (
        ROOT / "build_case.py",
        ROOT / "postprocess.py",
        ROOT / "summary.txt",
        ROOT / "center_velocity.csv",
        CASE / "log.blockMesh",
        CASE / "log.icoFoam",
        CASE / "log.cellCentres",
        CASE / "system/blockMeshDict",
        CASE / "system/controlDict",
        CASE / "system/fvSchemes",
        CASE / "system/fvSolution",
        CASE / "constant/physicalProperties",
        CASE / "0/U",
        CASE / "0/p",
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    if not python_script_is_valid(
        ROOT / "build_case.py",
        ("cavity", "blockMeshDict", "controlDict", "fvSchemes", "fvSolution", "0/U", "0/p"),
    ):
        return False
    if not python_script_is_valid(
        ROOT / "postprocess.py",
        ("cavity", "center_velocity.csv", "summary.txt", "nearest", "30"),
    ):
        return False
    if any(not log_finished(CASE / name) for name in ("log.blockMesh", "log.icoFoam", "log.cellCentres")):
        return False
    mesh_check = subprocess.run(
        ["bash", "-lc", ". /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/cavity"],
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

    latest = latest_time()
    centres = vectors(latest / "C")
    velocity = vectors(latest / "U")
    if len(centres) != 2500 or len(velocity) != len(centres):
        return False
    points = {
        "center": (0.5, 0.5, 0.005),
        "left_mid": (0.25, 0.5, 0.005),
        "right_mid": (0.75, 0.5, 0.005),
    }
    calculated = {name: nearest(centres, velocity, point) for name, point in points.items()}
    if not velocity_signs_are_valid(calculated):
        return False

    with (ROOT / "center_velocity.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if [row.get("location") for row in rows] != list(points):
        return False
    for row in rows:
        actual = tuple(float(row[key]) for key in ("ux_mps", "uy_mps", "uz_mps"))
        if any(
            not close(a, b, 5.0e-7)
            for a, b in zip(actual, calculated[row["location"]])
        ):
            return False

    summary_lines = [line.strip() for line in read(ROOT / "summary.txt").splitlines() if line.strip()]
    if len(summary_lines) != 1:
        return False
    reported = float(summary_lines[0])
    return math.isfinite(reported) and abs(reported - calculated["center"][0]) <= 5.0e-7


def main() -> int:
    try:
        result = check()
    except Exception:
        result = False
    print("True" if result else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
