#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "shock_tube"
PLATEAU_MIN = 0.64
PLATEAU_MAX = 0.72


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


def pressure_profile(final: Path) -> tuple[float, list[tuple[float, float]]]:
    centres = field(final / "C", "vector")
    pressure = field(final / "p", "scalar")
    if not (len(centres) == len(pressure) == 1000):
        raise ValueError("unexpected cell count")
    profile = sorted(((point[0], value) for point, value in zip(centres, pressure)), key=lambda row: row[0])
    plateau = [value for x, value in profile if PLATEAU_MIN <= x <= PLATEAU_MAX]
    if len(plateau) != 80 or any(not math.isfinite(value) or value <= 0 for value in pressure):
        raise ValueError("invalid pressure field")
    average = sum(plateau) / len(plateau)
    relative_std = math.sqrt(sum((value - average) ** 2 for value in plateau) / len(plateau)) / average
    if not (20000 < average < 50000 and relative_std < 0.05):
        raise ValueError("fixed interval is not the expected post-shock plateau")
    return average, profile


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    control = read(CASE / "system/controlDict")
    initial = read(CASE / "system/setFieldsDict")
    thermo = read(CASE / "constant/physicalProperties")
    return all(
        (
            "(1000 1 1)" in mesh,
            "application rhoCentralFoam;" in control,
            re.search(r"\bendTime\s+0\.0005\s*;", control) is not None,
            re.search(r"\bmaxCo\s+0\.2\s*;", control) is not None,
            "writeFormat ascii;" in control,
            "box (0 0 0) (0.5 0.01 0.01);" in initial,
            "volScalarFieldValue T 278.646992162988" in initial,
            "volScalarFieldValue p 10000" in initial,
            "volScalarFieldValue T 348.308740203735" in initial,
            "volScalarFieldValue p 100000" in initial,
            "equationOfState perfectGas;" in thermo,
            re.search(r"\bmolWeight\s+28\.96\s*;", thermo) is not None,
            re.search(r"\bCp\s+1004\.5\s*;", thermo) is not None,
        )
    )


def check() -> bool:
    final = latest_time()
    required = (
        ROOT / "build_case.py",
        ROOT / "postprocess.py",
        ROOT / "summary.txt",
        ROOT / "pressure_profile.csv",
        CASE / "log.blockMesh",
        CASE / "log.checkMesh",
        CASE / "log.setFields",
        CASE / "log.rhoCentralFoam",
        final / "C",
        final / "p",
        final / "T",
        final / "U",
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    if final.name != "0.0005":
        return False
    mesh_log = read(CASE / "log.checkMesh")
    solve_log = read(CASE / "log.rhoCentralFoam")
    if not (
        "Mesh OK." in mesh_log
        and "End" in mesh_log
        and "Time = 0.0005" in solve_log
        and "End" in solve_log
    ):
        return False
    mesh_check = subprocess.run(
        [
            "bash",
            "--noprofile",
            "--norc",
            "-c",
            "trap - CHLD; . /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/shock_tube",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if mesh_check.returncode != 0 or "Mesh OK." not in mesh_check.stdout or not check_case():
        return False

    average, profile = pressure_profile(final)
    with (ROOT / "pressure_profile.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != len(profile) or set(rows[0]) != {"x_m", "p_pa"}:
        return False
    for row, expected in zip(rows, profile):
        actual = (float(row["x_m"]), float(row["p_pa"]))
        if any(abs(left - right) > 5e-7 for left, right in zip(actual, expected)):
            return False

    lines = [line.strip() for line in read(ROOT / "summary.txt").splitlines() if line.strip()]
    if len(lines) != 1:
        return False
    reported = float(lines[0])
    return math.isfinite(reported) and abs(reported - average) <= 5e-7


def main() -> int:
    try:
        result = check()
    except Exception:
        result = False
    print("True" if result else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
