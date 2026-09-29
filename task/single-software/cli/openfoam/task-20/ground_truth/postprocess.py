#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import os
import re
from pathlib import Path


ROOT = Path(os.environ.get("ENGIWORLD_TASK_ROOT", "/home/user/Desktop"))
FORCES = ROOT / "dynamic/postProcessing/bodyForces/0/forces.dat"
NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
VECTOR = re.compile(rf"\(\s*({NUMBER})\s+({NUMBER})\s+({NUMBER})\s*\)")
TIME = re.compile(rf"^\s*({NUMBER})\s+")


def parse_forces(path: Path) -> list[tuple[float, float, float, float]]:
    header = None
    history = []
    for line in path.read_text(encoding="utf-8", errors="strict").splitlines():
        stripped = line.strip()
        if stripped.startswith("# Time"):
            header = " ".join(stripped.split())
            continue
        if not stripped or stripped.startswith("#"):
            continue
        time_match = TIME.match(stripped)
        vectors = VECTOR.findall(stripped)
        if time_match is None or len(vectors) != 4:
            raise ValueError("forces.dat row must contain pressure/viscous force and moment vectors")
        time_s = float(time_match.group(1))
        pressure_fx = float(vectors[0][0])
        viscous_fx = float(vectors[1][0])
        row = (time_s, pressure_fx, viscous_fx, pressure_fx + viscous_fx)
        if not all(math.isfinite(value) for value in row):
            raise ValueError("forces.dat contains a non-finite value")
        history.append(row)

    if header is None:
        raise ValueError("forces.dat is missing its component header")
    if "forces(pressure viscous)" not in header or "moments(pressure viscous)" not in header:
        raise ValueError(f"unexpected OpenFOAM 11 forces header: {header}")
    if "porous" in header.lower():
        raise ValueError("this non-porous case must not contain a porous-force component")
    if len(history) != 2001:
        raise RuntimeError(f"incomplete force history: expected 2001 rows, got {len(history)}")
    for index, row in enumerate(history):
        if abs(row[0] - index * 0.001) > 1.0e-9:
            raise RuntimeError(f"unexpected time at row {index}: {row[0]}")
    return history


history = parse_forces(FORCES)

with (ROOT / "force_history.csv").open("w", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(("time_s", "pressure_fx_n", "viscous_fx_n", "total_fx_n"))
    for row in history:
        writer.writerow(f"{value:.12g}" for value in row)

final_fx = history[-1][3]
(ROOT / "summary.txt").write_text(f"{final_fx:.9f}\n", encoding="utf-8")
print(f"final_fx={final_fx:.9f} samples={len(history)}")
