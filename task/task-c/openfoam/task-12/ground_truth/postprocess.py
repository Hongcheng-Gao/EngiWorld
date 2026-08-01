#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "pipe_parallel"
RADIUS = 0.05
RHO = 1.0
RADIAL_CELLS = 20


def field(path: Path, kind: str) -> list:
    text = path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(
        rf"internalField\s+nonuniform\s+List<{kind}>\s+\d+\s*\((.*?)\)\s*;",
        text,
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


centres = field(CASE / "1000/C", "vector")
velocity = field(CASE / "1000/U", "vector")
if len(centres) != 4800 or len(velocity) != len(centres):
    raise RuntimeError("unexpected reconstructed field size")

indices = sorted(
    (i for i, centre in enumerate(centres) if centre[0] > 2.99),
    key=lambda i: math.hypot(centres[i][1], centres[i][2]),
)
if len(indices) != RADIAL_CELLS:
    raise RuntimeError("unexpected outlet-cell count")

mass_flow = 0.0
square_error = 0.0
area_sum = 0.0
rows = []
for radial_index, index in enumerate(indices):
    radius = math.hypot(centres[index][1], centres[index][2])
    inner = radial_index * RADIUS / RADIAL_CELLS
    outer = (radial_index + 1) * RADIUS / RADIAL_CELLS
    area = math.pi * (outer**2 - inner**2)
    ux = velocity[index][0]
    theoretical = 2.0 * (1.0 - (radius / RADIUS) ** 2)
    contribution = RHO * ux * area
    mass_flow += contribution
    square_error += area * (ux - theoretical) ** 2
    area_sum += area
    rows.append((radius, ux, theoretical, area, contribution))
profile_rms_error = math.sqrt(square_error / area_sum)
theoretical_flow = RHO * math.pi * RADIUS**2
if not (
    abs(mass_flow - theoretical_flow) / theoretical_flow < 0.02
    and profile_rms_error < 0.08
):
    raise RuntimeError("parallel pipe result is not fully developed or mass-conservative")

with (ROOT / "outlet_mass_flow.csv").open("w", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(("radius_m", "ux_m_s", "poiseuille_ux_m_s", "annulus_area_m2", "mass_flow_kg_s"))
    writer.writerows(rows)

(ROOT / "summary.txt").write_text(f"{mass_flow:.9f}\n", encoding="utf-8")
print(f"mass_flow={mass_flow:.9f} profile_rms_error={profile_rms_error:.9f}")
