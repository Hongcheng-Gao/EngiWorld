#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "cavity_graph"
SAMPLES = CASE / "postProcessing/sampleDict/30"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def internal_count(path: Path, kind: str) -> int:
    match = re.search(rf"internalField\s+nonuniform\s+List<{kind}>\s+(\d+)", read(path))
    if not match:
        raise ValueError(f"missing nonuniform {kind} field")
    return int(match.group(1))


def profile(path: Path) -> list[tuple[float, float, float]]:
    rows = []
    for line in read(path).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        values = [float(value) for value in stripped.split()]
        if len(values) < 4:
            raise ValueError("invalid sampled profile")
        rows.append((values[0], values[1], values[2]))
    if len(rows) != 99:
        raise ValueError("unexpected profile length")
    expected_coordinates = [0.01 * index for index in range(1, 100)]
    if any(abs(row[0] - expected) > 1e-9 for row, expected in zip(rows, expected_coordinates)):
        raise ValueError("unexpected profile coordinates")
    return rows


def csv_profile(path: Path, keys: tuple[str, str, str]) -> list[tuple[float, float, float]]:
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 99 or set(rows[0]) != set(keys):
        raise ValueError("invalid CSV profile")
    return [tuple(float(row[key]) for key in keys) for row in rows]


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    velocity = read(CASE / "0/U")
    physical = read(CASE / "constant/physicalProperties")
    control = read(CASE / "system/controlDict")
    sampling = read(CASE / "system/sampleDict")
    return all(
        (
            re.search(r"convertToMeters\s+1\s*;", mesh) is not None,
            "(64 64 1)" in mesh,
            "value uniform (1 0 0);" in velocity,
            re.search(r"\bnu\s+\[0 2 -1 0 0 0 0\]\s+0\.01\s*;", physical) is not None,
            "application icoFoam;" in control,
            re.search(r"\bendTime\s+30\s*;", control) is not None,
            "interpolationScheme cellPoint;" in sampling,
            "start (0.5 0.01 0.005);" in sampling,
            "end (0.5 0.99 0.005);" in sampling,
            "start (0.01 0.5 0.005);" in sampling,
            "end (0.99 0.5 0.005);" in sampling,
            sampling.count("nPoints 99;") == 2,
        )
    )


def check() -> bool:
    required = (
        ROOT / "build_case.py",
        ROOT / "postprocess.py",
        ROOT / "summary.txt",
        ROOT / "vertical_centerline.csv",
        ROOT / "horizontal_centerline.csv",
        CASE / "log.blockMesh",
        CASE / "log.checkMesh",
        CASE / "log.icoFoam",
        CASE / "log.sample",
        CASE / "30/U",
        CASE / "30/p",
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    mesh_log = read(CASE / "log.checkMesh")
    solve_log = read(CASE / "log.icoFoam")
    if not (
        "Mesh OK." in mesh_log
        and "End" in mesh_log
        and "Time = 30" in solve_log
        and "End" in solve_log
        and internal_count(CASE / "30/U", "vector") == 4096
        and internal_count(CASE / "30/p", "scalar") == 4096
    ):
        return False
    mesh_check = subprocess.run(
        [
            "bash",
            "--noprofile",
            "--norc",
            "-c",
            "trap - CHLD; . /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/cavity_graph",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if mesh_check.returncode != 0 or "Mesh OK." not in mesh_check.stdout or not check_case():
        return False
    sampler = subprocess.run(
        [
            "bash",
            "--noprofile",
            "--norc",
            "-c",
            "trap - CHLD; . /opt/openfoam11/etc/bashrc && postProcess -case /home/user/Desktop/cavity_graph -func sampleDict -latestTime",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if sampler.returncode != 0 or "End" not in sampler.stdout:
        return False

    vertical = profile(SAMPLES / "vertical.xy")
    horizontal = profile(SAMPLES / "horizontal.xy")
    stored_vertical = csv_profile(ROOT / "vertical_centerline.csv", ("y_m", "ux_mps", "uy_mps"))
    stored_horizontal = csv_profile(ROOT / "horizontal_centerline.csv", ("x_m", "ux_mps", "uy_mps"))
    for stored, actual in ((stored_vertical, vertical), (stored_horizontal, horizontal)):
        if any(any(abs(left - right) > 5e-7 for left, right in zip(row, expected)) for row, expected in zip(stored, actual)):
            return False

    ux_center = next(row[1] for row in vertical if abs(row[0] - 0.5) < 1e-9)
    uy_center = next(row[2] for row in horizontal if abs(row[0] - 0.5) < 1e-9)
    if not (-0.5 < ux_center < 0 and -0.3 < uy_center < 0.3):
        return False
    lines = [line.strip() for line in read(ROOT / "summary.txt").splitlines() if line.strip()]
    if len(lines) != 1:
        return False
    parts = [float(value.strip()) for value in lines[0].split(",")]
    return len(parts) == 2 and all(math.isfinite(value) for value in parts) and all(
        abs(value - expected) <= 5e-7 for value, expected in zip(parts, (ux_center, uy_center))
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
