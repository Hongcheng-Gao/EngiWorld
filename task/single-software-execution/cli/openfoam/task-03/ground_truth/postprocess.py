#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "bfs"
U_REF = 10.0


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
pressure = field(latest / "p", "scalar")
if not (len(centres) == len(velocity) == len(pressure)):
    raise RuntimeError("field lengths differ")

indices = sorted(
    (i for i, c in enumerate(centres) if 0.0 < c[0] < 1.0 and c[1] < 0.003),
    key=lambda i: centres[i][0],
)
if len(indices) != 200:
    raise RuntimeError(f"expected 200 downstream-wall-adjacent cells, got {len(indices)}")

rows = []
for i in indices:
    cp = pressure[i] / (0.5 * U_REF**2)
    rows.append((centres[i][0], pressure[i], cp, velocity[i][0]))

with (ROOT / "downstream_wall_pressure.csv").open("w", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(("x_m", "p_kinematic_m2ps2", "cp", "ux_mps"))
    for row in rows:
        writer.writerow(f"{value:.10g}" for value in row)

min_cp = min(row[2] for row in rows)
(ROOT / "summary.txt").write_text(f"{min_cp:.9f}\n", encoding="utf-8")
