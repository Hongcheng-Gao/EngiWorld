#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
from pathlib import Path


ROOT = Path("/home/user/Desktop")
SWEEP = ROOT / "cavity_sweep"


def vectors(path: Path) -> list[tuple[float, float, float]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(
        r"internalField\s+nonuniform\s+List<vector>\s+\d+\s*\((.*?)\)\s*;",
        text,
        re.S,
    )
    if not match:
        raise ValueError(f"missing vector field: {path}")
    return [
        tuple(float(value) for value in item.split())
        for item in re.findall(r"\(([^()]+)\)", match.group(1))
    ]


records = []
for reynolds in (100, 400, 1000):
    final = SWEEP / f"Re{reynolds}" / "30"
    centres = vectors(final / "C")
    velocity = vectors(final / "U")
    if len(centres) != 2500 or len(velocity) != len(centres):
        raise RuntimeError("unexpected field size")
    indices = sorted(
        range(len(centres)),
        key=lambda i: sum((centres[i][j] - (0.5, 0.5, 0.005)[j]) ** 2 for j in range(3)),
    )[:4]
    center = tuple(sum(velocity[i][j] for i in indices) / 4.0 for j in range(3))
    max_speed = max(math.sqrt(sum(component**2 for component in item)) for item in velocity)
    if not (-0.5 < center[0] < 0 and 0.5 < max_speed < 1.2):
        raise RuntimeError("cavity result is not physical")
    records.append((reynolds, 1.0 / reynolds, *center, max_speed))

if not (records[0][2] < records[1][2] < records[2][2] < 0):
    raise RuntimeError("center velocity does not vary consistently with Reynolds number")

with (ROOT / "sweep_results.csv").open("w", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(("reynolds", "nu_m2_s", "center_ux", "center_uy", "center_uz", "max_speed"))
    writer.writerows(records)

(ROOT / "summary.txt").write_text(
    "".join(f"{reynolds}, {center_ux:.9f}\n" for reynolds, _, center_ux, *_ in records),
    encoding="utf-8",
)
for record in records:
    print(f"Re={record[0]} center_ux={record[2]:.9f} max_speed={record[-1]:.9f}")
