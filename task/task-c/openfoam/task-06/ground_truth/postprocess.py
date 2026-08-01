#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "plate"
U_REF = 10.0
NU = 1.5e-5
STATION = 0.5


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def patch_vectors(path: Path, patch: str) -> list[tuple[float, float, float]]:
    match = re.search(
        rf"\b{re.escape(patch)}\s*\{{.*?value\s+nonuniform\s+List<vector>\s+(\d+)\s*\((.*?)\)\s*;",
        read(path),
        re.S,
    )
    if not match:
        raise ValueError(f"missing {patch} vectors in {path}")
    values = [
        tuple(float(value) for value in item.split())
        for item in re.findall(r"\(([^()]+)\)", match.group(2))
    ]
    if len(values) != int(match.group(1)):
        raise ValueError(f"{patch} vector count mismatch")
    return values


centres = patch_vectors(CASE / "2000/C", "plate")
shear = patch_vectors(CASE / "2000/wallShearStress", "plate")
if len(centres) != 200 or len(shear) != 200:
    raise RuntimeError("expected 200 plate faces")

rows = []
for centre, stress in sorted(zip(centres, shear), key=lambda item: item[0][0]):
    x = centre[0]
    tau_x = stress[0]
    cf = 2.0 * abs(tau_x) / U_REF**2
    theory = 0.664 / math.sqrt(U_REF * x / NU)
    error_percent = abs(cf - theory) / theory * 100.0
    rows.append((x, tau_x, cf, theory, error_percent))

with (ROOT / "plate_shear.csv").open("w", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(("x_m", "wall_shear_kinematic_m2ps2", "cf", "blasius_cf", "error_percent"))
    for row in rows:
        writer.writerow(f"{value:.10g}" for value in row)

sample = min(rows, key=lambda row: abs(row[0] - STATION))
(ROOT / "summary.txt").write_text(f"{sample[2]:.9f}, {sample[4]:.9f}\n", encoding="utf-8")
print(f"x={sample[0]:.9f} cf={sample[2]:.9f} error_percent={sample[4]:.9f}")
