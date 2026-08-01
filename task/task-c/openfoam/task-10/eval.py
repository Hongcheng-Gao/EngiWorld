#!/usr/bin/env python3
from __future__ import annotations

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


def field(path: Path, kind: str) -> list:
    match = re.search(
        rf"internalField\s+nonuniform\s+List<{kind}>\s+\d+\s*\((.*?)\)\s*;",
        read(path),
        re.S,
    )
    if not match:
        raise ValueError(f"missing {kind} field")
    if kind == "vector":
        return [
            tuple(float(value) for value in item.split())
            for item in re.findall(r"\(([^()]+)\)", match.group(1))
        ]
    return [float(value) for value in match.group(1).split()]


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    temperature = read(CASE / "0/T")
    physical = read(CASE / "constant/physicalProperties")
    momentum = read(CASE / "constant/momentumTransport")
    gravity = read(CASE / "constant/g")
    control = read(CASE / "system/controlDict")
    boundary = read(CASE / "constant/polyMesh/boundary")
    return all(
        (
            "(0.1 0.1 0.01)" in mesh,
            "(41 41 1)" in mesh,
            "hot { type fixedValue; value uniform 310; }" in temperature,
            "cold { type fixedValue; value uniform 290; }" in temperature,
            re.search(r"\bmolWeight\s+28\.96\s*;", physical) is not None,
            re.search(r"\bCp\s+1004\.4\s*;", physical) is not None,
            re.search(r"\bmu\s+1\.846e-0?5\s*;", physical, re.I) is not None,
            re.search(r"\bPr\s+0\.71\s*;", physical) is not None,
            "simulationType laminar;" in momentum,
            "value (0 -9.81 0);" in gravity,
            re.search(r"\bendTime\s+1000\s*;", control) is not None,
            re.search(r"\bwriteInterval\s+1000\s*;", control) is not None,
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
    if any("End" not in read(path) for path in required[4:8]):
        return False
    solve_log = read(CASE / "log.foamRun")
    if "Time = 1000" not in solve_log:
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

    centres = field(TIME / "C", "vector")
    temperatures = field(TIME / "T", "scalar")
    velocity = field(TIME / "U", "vector")
    if not (len(centres) == len(temperatures) == len(velocity) == 1681):
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
    if any(abs(a - b) > 1.0e-10 for a, b in zip(sample, point)):
        return False
    if abs(float(row["temperature_k"]) - center_temp) > 5.0e-7:
        return False
    if abs(float(row["max_speed_m_s"]) - max_speed) > 5.0e-7:
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
