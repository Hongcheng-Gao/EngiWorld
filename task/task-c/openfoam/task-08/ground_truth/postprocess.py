#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
from pathlib import Path


ROOT = Path("/home/user/Desktop")
COEFFICIENTS = ROOT / "airfoil/postProcessing/forces/0/forceCoeffs.dat"


history = []
for line in COEFFICIENTS.read_text(encoding="utf-8", errors="ignore").splitlines():
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        continue
    values = [float(value) for value in stripped.split()]
    if len(values) >= 4:
        history.append((values[0], values[2], values[3]))
window = [row for row in history if 800 <= row[0] <= 1000]
if len(window) < 200:
    raise RuntimeError("insufficient converged force-coefficient samples")
avg_cd = sum(row[1] for row in window) / len(window)
avg_cl = sum(row[2] for row in window) / len(window)
std_cd = math.sqrt(sum((row[1] - avg_cd) ** 2 for row in window) / len(window))
std_cl = math.sqrt(sum((row[2] - avg_cl) ** 2 for row in window) / len(window))
if not (0.1 < avg_cl < 2.0 and 0.001 < avg_cd < 0.2 and std_cl < 0.02 and std_cd < 0.01):
    raise RuntimeError("airfoil coefficients are not physical and converged")

with (ROOT / "force_coefficients.csv").open("w", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(("iteration", "cd", "cl"))
    for row in history:
        writer.writerow(f"{value:.10g}" for value in row)

(ROOT / "summary.txt").write_text(f"{avg_cl:.9f}, {avg_cd:.9f}\n", encoding="utf-8")
print(f"cl={avg_cl:.9f} cd={avg_cd:.9f} std_cl={std_cl:.9f} std_cd={std_cd:.9f}")
