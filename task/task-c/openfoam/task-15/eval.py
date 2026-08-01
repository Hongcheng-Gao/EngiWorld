#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "dam_break"
TARGET_X = 0.25


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def latest_time() -> Path:
    times = [
        path
        for path in CASE.iterdir()
        if path.is_dir() and re.fullmatch(r"\d+(?:\.\d+)?", path.name) and float(path.name) > 0
    ]
    if not times:
        raise FileNotFoundError("no computed time directory")
    return max(times, key=lambda path: float(path.name))


def field(path: Path, kind: str) -> list:
    match = re.search(
        rf"internalField\s+nonuniform\s+List<{kind}>\s+(\d+)\s*\((.*?)\)\s*;",
        read(path),
        re.S,
    )
    if not match:
        raise ValueError(f"missing nonuniform {kind} field")
    if kind == "vector":
        values = [
            tuple(float(value) for value in item.split())
            for item in re.findall(r"\(([^()]+)\)", match.group(2))
        ]
    else:
        values = [float(value) for value in match.group(2).split()]
    if len(values) != int(match.group(1)):
        raise ValueError("field count mismatch")
    return values


def interface_profile(final: Path) -> tuple[float, list[tuple[float, float]]]:
    centres = field(final / "C", "vector")
    alpha = field(final / "alpha.water", "scalar")
    if not (len(centres) == len(alpha) == 2268):
        raise ValueError("unexpected cell count")
    if any(not math.isfinite(value) or value < -1e-6 or value > 1.000001 for value in alpha):
        raise ValueError("unbounded phase fraction")
    selected_x = min((point[0] for point in centres), key=lambda value: abs(value - TARGET_X))
    profile = sorted(
        ((point[1], value) for point, value in zip(centres, alpha) if abs(point[0] - selected_x) < 1e-9),
        key=lambda row: row[0],
    )
    if len(profile) != 50 or profile[0][1] < 0.5:
        raise ValueError("invalid sample column")
    for lower, upper in zip(profile, profile[1:]):
        if lower[1] >= 0.5 and upper[1] < 0.5:
            fraction = (0.5 - lower[1]) / (upper[1] - lower[1])
            return lower[0] + fraction * (upper[0] - lower[0]), profile
    raise ValueError("missing bottom-connected interface crossing")


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    control = read(CASE / "system/controlDict")
    initial = read(CASE / "system/setFieldsDict")
    gravity = read(CASE / "constant/g")
    water = read(CASE / "constant/physicalProperties.water")
    air = read(CASE / "constant/physicalProperties.air")
    return all(
        (
            re.search(r"convertToMeters\s+0\.146\s*;", mesh) is not None,
            mesh.count("hex (") == 5,
            "application interFoam;" in control,
            re.search(r"\bendTime\s+0\.5\s*;", control) is not None,
            re.search(r"\bmaxCo\s+0\.5\s*;", control) is not None,
            "writeFormat ascii;" in control,
            "box (0 0 -1) (0.1461 0.292 1);" in initial,
            "value           (0 -9.81 0);" in gravity,
            re.search(r"\bnu\s+1e-?06\s*;", water, re.I) is not None,
            re.search(r"\brho\s+1000\s*;", water) is not None,
            re.search(r"\bnu\s+1\.48e-?05\s*;", air, re.I) is not None,
            re.search(r"\brho\s+1\s*;", air) is not None,
        )
    )


def check() -> bool:
    final = latest_time()
    required = (
        ROOT / "build_case.py",
        ROOT / "postprocess.py",
        ROOT / "summary.txt",
        ROOT / "interface_profile.csv",
        CASE / "log.blockMesh",
        CASE / "log.checkMesh",
        CASE / "log.setFields",
        CASE / "log.interFoam",
        final / "alpha.water",
        final / "U",
        final / "p_rgh",
        final / "C",
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    if final.name != "0.5":
        return False
    mesh_log = read(CASE / "log.checkMesh")
    solve_log = read(CASE / "log.interFoam")
    if not (
        "Mesh OK." in mesh_log
        and "End" in mesh_log
        and "Time = 0.5" in solve_log
        and "End" in solve_log
    ):
        return False
    mesh_check = subprocess.run(
        [
            "bash",
            "--noprofile",
            "--norc",
            "-c",
            "trap - CHLD; . /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/dam_break",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if mesh_check.returncode != 0 or "Mesh OK." not in mesh_check.stdout or not check_case():
        return False

    height, profile = interface_profile(final)
    if not (0.0 < height < 0.584):
        return False
    with (ROOT / "interface_profile.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != len(profile) or set(rows[0]) != {"y_m", "alpha_water"}:
        return False
    for row, expected in zip(rows, profile):
        actual = (float(row["y_m"]), float(row["alpha_water"]))
        if any(abs(left - right) > 5e-7 for left, right in zip(actual, expected)):
            return False

    lines = [line.strip() for line in read(ROOT / "summary.txt").splitlines() if line.strip()]
    if len(lines) != 1:
        return False
    reported = float(lines[0])
    return math.isfinite(reported) and abs(reported - height) <= 5e-7


def main() -> int:
    try:
        result = check()
    except Exception:
        result = False
    print("True" if result else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
