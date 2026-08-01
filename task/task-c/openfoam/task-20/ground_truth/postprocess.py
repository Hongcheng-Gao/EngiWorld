#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path("/home/user/Desktop")
FORCES = ROOT / "dynamic/postProcessing/bodyForces/0/forces.dat"
NUMBER = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")


history = []
for line in FORCES.read_text(encoding="utf-8", errors="ignore").splitlines():
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        continue
    values = [float(value) for value in NUMBER.findall(stripped)]
    if len(values) < 10:
        raise ValueError("invalid forces.dat row")
    time = values[0]
    pressure_fx = values[1]
    viscous_fx = values[4]
    porous_fx = values[7]
    history.append((time, pressure_fx, viscous_fx, porous_fx, pressure_fx + viscous_fx + porous_fx))
if len(history) < 500 or abs(history[-1][0] - 2.0) > 1e-9:
    raise RuntimeError("incomplete force history")

with (ROOT / "force_history.csv").open("w", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(("time_s", "pressure_fx_n", "viscous_fx_n", "porous_fx_n", "total_fx_n"))
    for row in history:
        writer.writerow(f"{value:.12g}" for value in row)

final_fx = history[-1][4]
(ROOT / "summary.txt").write_text(f"{final_fx:.9f}\n", encoding="utf-8")
print(f"final_fx={final_fx:.9f} samples={len(history)}")
