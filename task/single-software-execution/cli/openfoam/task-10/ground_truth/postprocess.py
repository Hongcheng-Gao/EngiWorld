#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
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
        raise ValueError(f"missing {kind} field: {path}")
    if kind == "vector":
        return [
            tuple(float(value) for value in item.split())
            for item in re.findall(r"\(([^()]+)\)", match.group(1))
        ]
    return [float(value) for value in match.group(1).split()]


centres = field(TIME / "C", "vector")
temperatures = field(TIME / "T", "scalar")
velocity = field(TIME / "U", "vector")
if not (len(centres) == len(temperatures) == len(velocity) == 1681):
    raise RuntimeError("unexpected final field size")

target = (0.05, 0.05, 0.005)
index = min(
    range(len(centres)),
    key=lambda i: sum((centres[i][j] - target[j]) ** 2 for j in range(3)),
)
point = centres[index]
if math.sqrt(sum((point[j] - target[j]) ** 2 for j in range(3))) > 1.0e-9:
    raise RuntimeError("the 41 by 41 mesh has no geometric-center cell")
center_temp = temperatures[index]
max_speed = max(math.sqrt(sum(component**2 for component in item)) for item in velocity)
if not (295.0 < center_temp < 305.0 and 1.0e-4 < max_speed < 1.0):
    raise RuntimeError("natural-convection result is not physical")

with (ROOT / "center_sample.csv").open("w", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(("x", "y", "z", "temperature_k", "max_speed_m_s"))
    writer.writerow((*point, center_temp, max_speed))

(ROOT / "summary.txt").write_text(f"{center_temp:.9f}\n", encoding="utf-8")
print(f"center_temp={center_temp:.9f} max_speed={max_speed:.9f}")
