#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "cavity"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def vectors(path: Path) -> list[tuple[float, float, float]]:
    match = re.search(
        r"internalField\s+nonuniform\s+List<vector>\s+\d+\s*\((.*?)\)\s*;",
        read(path),
        re.S,
    )
    if not match:
        raise ValueError(f"missing vector field in {path}")
    values = [
        tuple(float(value) for value in item.split())
        for item in re.findall(r"\(([^()]+)\)", match.group(1))
    ]
    if not values or not all(len(value) == 3 for value in values):
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


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    velocity = read(CASE / "0/U")
    physical = read(CASE / "constant/physicalProperties")
    control = read(CASE / "system/controlDict")
    schemes = read(CASE / "system/fvSchemes")
    return all(
        (
            "(1 1 0)" in mesh,
            "(1 1 0.01)" in mesh,
            "(50 50 1)" in mesh,
            "type empty;" in mesh,
            "movingWall" in velocity,
            "value uniform (1 0 0);" in velocity,
            "type noSlip;" in velocity,
            re.search(r"\bnu\s+\[0 2 -1 0 0 0 0\]\s+1(?:\.0)?e-?3\s*;", physical, re.I)
            is not None,
            re.search(r"\bendTime\s+30(?:\.0)?\s*;", control) is not None,
            re.search(r"\bdeltaT\s+0\.005\s*;", control) is not None,
            re.search(r"\bwriteInterval\s+1000\s*;", control) is not None,
            "div(phi,U) Gauss linear;" in schemes,
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
    if "End" not in read(CASE / "log.blockMesh") or "End" not in read(CASE / "log.icoFoam"):
        return False
    mesh_check = subprocess.run(
        ["bash", "-lc", ". /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/cavity"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if mesh_check.returncode != 0 or "Mesh OK." not in mesh_check.stdout or not check_case():
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
    if not (
        -0.10 < calculated["center"][0] < -0.02
        and calculated["left_mid"][1] > 0.01
        and calculated["right_mid"][1] < -0.01
    ):
        return False

    with (ROOT / "center_velocity.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if [row.get("location") for row in rows] != list(points):
        return False
    for row in rows:
        actual = tuple(float(row[key]) for key in ("ux_mps", "uy_mps", "uz_mps"))
        if any(abs(a - b) > 5.0e-7 for a, b in zip(actual, calculated[row["location"]])):
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
