#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
from pathlib import Path


ROOT = Path("/home/user/Desktop")
COEFFICIENTS = ROOT / "cylinder/postProcessing/forces/0/forceCoeffs.dat"


history = []
for line in COEFFICIENTS.read_text(encoding="utf-8", errors="ignore").splitlines():
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        continue
    values = [float(value) for value in stripped.split()]
    if len(values) >= 4:
        history.append((values[0], values[2], values[3]))

window = [row for row in history if row[0] >= 10.0]
if len(window) < 100:
    raise RuntimeError("insufficient force-coefficient samples after t=10 s")
cl_mean = sum(row[2] for row in window) / len(window)
cl_rms = math.sqrt(sum((row[2] - cl_mean) ** 2 for row in window) / len(window))
zero_crossings = sum(
    (left[2] - cl_mean) * (right[2] - cl_mean) < 0
    for left, right in zip(window, window[1:])
)
cl_max = max(abs(row[2]) for row in window)
if zero_crossings < 5 or cl_rms <= 0.05:
    raise RuntimeError("periodic vortex shedding was not established")

with (ROOT / "lift_history.csv").open("w", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(("time_s", "cd", "cl"))
    for row in history:
        writer.writerow(f"{value:.10g}" for value in row)

(ROOT / "summary.txt").write_text(f"{cl_max:.9f}\n", encoding="utf-8")
print(f"cl_max={cl_max:.9f} cl_rms={cl_rms:.9f} zero_crossings={zero_crossings}")
