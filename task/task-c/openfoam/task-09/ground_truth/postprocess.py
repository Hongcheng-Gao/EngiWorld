#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "heat"


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


centres = field(CASE / "50/C", "vector")
temperature = field(CASE / "50/T", "scalar")
if len(centres) != 4000 or len(temperature) != 4000:
    raise RuntimeError("expected 4000 cells")
theoretical = [400.0 - 100.0 * centre[0] for centre in centres]
rms_error = math.sqrt(sum((value - theory) ** 2 for value, theory in zip(temperature, theoretical)) / len(temperature))
if rms_error > 1.0:
    raise RuntimeError(f"linear-profile RMS error is {rms_error}")

target_a = min(range(len(centres)), key=lambda i: (centres[i][0] - 0.25) ** 2 + (centres[i][1] - 0.25) ** 2)
target_b = min(range(len(centres)), key=lambda i: (centres[i][0] - 0.75) ** 2 + (centres[i][1] - 0.25) ** 2)
centerline = sorted(
    (i for i, centre in enumerate(centres) if abs(centre[1] - centres[target_a][1]) < 1e-9),
    key=lambda i: centres[i][0],
)
with (ROOT / "temperature_profile.csv").open("w", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(("x_m", "temperature_K", "linear_theory_K"))
    for i in centerline:
        writer.writerow((f"{centres[i][0]:.10g}", f"{temperature[i]:.10g}", f"{theoretical[i]:.10g}"))

(ROOT / "summary.txt").write_text(f"{temperature[target_a]:.9f}, {temperature[target_b]:.9f}\n", encoding="utf-8")
print(f"temp_a={temperature[target_a]:.9f} temp_b={temperature[target_b]:.9f} rms_error={rms_error:.9f}")
