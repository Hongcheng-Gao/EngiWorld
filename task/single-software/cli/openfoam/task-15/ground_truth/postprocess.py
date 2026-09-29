#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
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


final = latest_time()
centres = field(final / "C", "vector")
alpha = field(final / "alpha.water", "scalar")
if len(centres) != len(alpha):
    raise ValueError("cell-centre and phase-field counts differ")
selected_x = min((point[0] for point in centres), key=lambda value: abs(value - TARGET_X))
profile = sorted(
    ((point[1], value) for point, value in zip(centres, alpha) if abs(point[0] - selected_x) < 1e-9),
    key=lambda row: row[0],
)
if len(profile) < 10 or profile[0][1] < 0.5:
    raise RuntimeError("no bottom-connected water column at the sample location")

height = None
for lower, upper in zip(profile, profile[1:]):
    if lower[1] >= 0.5 and upper[1] < 0.5:
        fraction = (0.5 - lower[1]) / (upper[1] - lower[1])
        height = lower[0] + fraction * (upper[0] - lower[0])
        break
if height is None:
    raise RuntimeError("no alpha.water=0.5 free-surface crossing found")

with (ROOT / "interface_profile.csv").open("w", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(("y_m", "alpha_water"))
    for y, value in profile:
        writer.writerow((f"{y:.10g}", f"{value:.10g}"))

(ROOT / "summary.txt").write_text(f"{height:.9f}\n", encoding="utf-8")
print(f"interface_height={height:.9f} sample_x={selected_x:.9f} cells={len(profile)}")
