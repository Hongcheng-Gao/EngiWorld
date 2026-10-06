#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "porous"
RHO = 1000.0


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


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


centres = field(CASE / "500/C", "vector")
pressure = field(CASE / "500/p", "scalar")
if len(centres) != len(pressure):
    raise ValueError("cell-centre and pressure counts differ")
stations: dict[float, list[float]] = {}
for point, value in zip(centres, pressure):
    stations.setdefault(point[0], []).append(value)
profile = [(x, sum(values) / len(values)) for x, values in sorted(stations.items())]
if len(profile) != 100 or any(len(values) != 10 for values in stations.values()):
    raise RuntimeError("unexpected axial stations")
delta_p = RHO * (profile[0][1] - profile[-1][1])

with (ROOT / "axial_pressure.csv").open("w", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(("x_m", "p_kinematic_m2ps2", "p_pa"))
    for x, value in profile:
        writer.writerow((f"{x:.12g}", f"{value:.12g}", f"{RHO * value:.12g}"))

(ROOT / "summary.txt").write_text(f"{delta_p:.9f}\n", encoding="utf-8")
print(f"delta_p={delta_p:.9f} Pa stations={len(profile)}")
