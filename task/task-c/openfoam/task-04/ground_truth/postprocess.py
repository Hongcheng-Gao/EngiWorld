#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "pipe_laminar"
RADIUS = 0.05
U_BULK = 1.0


def field(path: Path, kind: str) -> list:
    text = path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(
        rf"internalField\s+nonuniform\s+List<{kind}>\s+\d+\s*\((.*?)\)\s*;",
        text,
        re.S,
    )
    if not match:
        raise ValueError(f"missing {kind} field in {path}")
    if kind == "vector":
        return [
            tuple(float(value) for value in item.split())
            for item in re.findall(r"\(([^()]+)\)", match.group(1))
        ]
    return [float(value) for value in match.group(1).split()]


latest = CASE / "2000"
centres = field(latest / "C", "vector")
velocity = field(latest / "U", "vector")
if len(centres) != len(velocity):
    raise RuntimeError("field lengths differ")

indices = sorted(
    (i for i, c in enumerate(centres) if c[0] > 4.99),
    key=lambda i: math.hypot(centres[i][1], centres[i][2]),
)
if len(indices) != 40:
    raise RuntimeError(f"expected 40 outlet-adjacent cells, got {len(indices)}")

rows = []
weighted_square_error = 0.0
weight_sum = 0.0
for i in indices:
    radius = math.hypot(centres[i][1], centres[i][2])
    theoretical = 2.0 * U_BULK * (1.0 - (radius / RADIUS) ** 2)
    ux = velocity[i][0]
    weight = radius
    weighted_square_error += weight * (ux - theoretical) ** 2
    weight_sum += weight
    rows.append((radius, ux, theoretical))

profile_error = math.sqrt(weighted_square_error / weight_sum) / U_BULK
u_max = max(row[1] for row in rows)
with (ROOT / "outlet_profile.csv").open("w", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(("radius_m", "ux_mps", "poiseuille_ux_mps"))
    for row in rows:
        writer.writerow(f"{value:.10g}" for value in row)

(ROOT / "summary.txt").write_text(f"{u_max:.9f}\n", encoding="utf-8")
print(f"u_max={u_max:.9f} profile_error={profile_error:.9f}")
