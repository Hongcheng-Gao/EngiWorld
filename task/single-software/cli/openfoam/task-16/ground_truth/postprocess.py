#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
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


final = latest_time()
centres = field(final / "C", "vector")
pressure = field(final / "p", "scalar")
if len(centres) != len(pressure):
    raise ValueError("cell-centre and pressure counts differ")
profile = sorted(((point[0], value) for point, value in zip(centres, pressure)), key=lambda row: row[0])
plateau = [value for x, value in profile if PLATEAU_MIN <= x <= PLATEAU_MAX]
if len(plateau) < 20:
    raise RuntimeError("insufficient plateau cells")
average = sum(plateau) / len(plateau)
relative_std = math.sqrt(sum((value - average) ** 2 for value in plateau) / len(plateau)) / average
if relative_std >= 0.05:
    raise RuntimeError("fixed pressure interval is not a plateau")

with (ROOT / "pressure_profile.csv").open("w", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(("x_m", "p_pa"))
    for x, value in profile:
        writer.writerow((f"{x:.10g}", f"{value:.10g}"))

(ROOT / "summary.txt").write_text(f"{average:.9f}\n", encoding="utf-8")
print(f"shock_pressure={average:.9f} plateau_cells={len(plateau)} relative_std={relative_std:.9f}")
