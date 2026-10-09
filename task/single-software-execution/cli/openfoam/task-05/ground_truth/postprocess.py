#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "pipe_turb"
RADIUS = 0.05
RHO = 1.225
RADIAL_CELLS = 20


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def vector_field(path: Path) -> list[tuple[float, float, float]]:
    match = re.search(
        r"internalField\s+nonuniform\s+List<vector>\s+\d+\s*\((.*?)\)\s*;",
        read(path),
        re.S,
    )
    if not match:
        raise ValueError(f"missing vector field in {path}")
    return [
        tuple(float(value) for value in item.split())
        for item in re.findall(r"\(([^()]+)\)", match.group(1))
    ]


def wall_yplus(path: Path) -> list[float]:
    match = re.search(
        r"\bwall\s*\{.*?value\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)\s*;",
        read(path),
        re.S,
    )
    if not match:
        raise ValueError("missing wall yPlus values")
    values = [float(value) for value in match.group(2).split()]
    if len(values) != int(match.group(1)):
        raise ValueError("wall yPlus count mismatch")
    return values


latest = CASE / "2000"
centres = vector_field(latest / "C")
velocity = vector_field(latest / "U")
if len(centres) != len(velocity):
    raise RuntimeError("field lengths differ")

indices = sorted(
    (i for i, c in enumerate(centres) if c[0] > 2.99),
    key=lambda i: math.hypot(centres[i][1], centres[i][2]),
)
if len(indices) != RADIAL_CELLS:
    raise RuntimeError(f"expected {RADIAL_CELLS} outlet cells, got {len(indices)}")

profile_rows = []
mass_flow = 0.0
for radial_index, i in enumerate(indices):
    radius = math.hypot(centres[i][1], centres[i][2])
    inner = radial_index * RADIUS / RADIAL_CELLS
    outer = (radial_index + 1) * RADIUS / RADIAL_CELLS
    annulus_area = math.pi * (outer**2 - inner**2)
    contribution = RHO * velocity[i][0] * annulus_area
    mass_flow += contribution
    profile_rows.append((radius, velocity[i][0], annulus_area, contribution))

with (ROOT / "outlet_profile.csv").open("w", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(("radius_m", "ux_mps", "annulus_area_m2", "mass_flow_kgps"))
    for row in profile_rows:
        writer.writerow(f"{value:.10g}" for value in row)

yplus = wall_yplus(latest / "yPlus")
if len(yplus) != 300:
    raise RuntimeError(f"expected 300 wall yPlus values, got {len(yplus)}")
avg_yplus = sum(yplus) / len(yplus)
with (ROOT / "wall_yplus.csv").open("w", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(("wall_face_index", "yplus"))
    for index, value in enumerate(yplus):
        writer.writerow((index, f"{value:.10g}"))

(ROOT / "summary.txt").write_text(f"{mass_flow:.9f}, {avg_yplus:.9f}\n", encoding="utf-8")
print(f"mass_flow={mass_flow:.9f} avg_yplus={avg_yplus:.9f}")
