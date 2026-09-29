#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path("/home/user/Desktop")
SAMPLES = ROOT / "cavity_graph/postProcessing/sampleDict/30"


def profile(path: Path) -> list[tuple[float, float, float]]:
    rows = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        values = [float(value) for value in stripped.split()]
        if len(values) < 4:
            raise ValueError(f"invalid raw sample row in {path}")
        rows.append((values[0], values[1], values[2]))
    if len(rows) != 99:
        raise ValueError(f"expected 99 samples in {path}")
    return rows


vertical = profile(SAMPLES / "vertical.xy")
horizontal = profile(SAMPLES / "horizontal.xy")

with (ROOT / "vertical_centerline.csv").open("w", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(("y_m", "ux_mps", "uy_mps"))
    for row in vertical:
        writer.writerow(f"{value:.10g}" for value in row)

with (ROOT / "horizontal_centerline.csv").open("w", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(("x_m", "ux_mps", "uy_mps"))
    for row in horizontal:
        writer.writerow(f"{value:.10g}" for value in row)

vertical_center = next(row for row in vertical if abs(row[0] - 0.5) < 1e-9)
horizontal_center = next(row for row in horizontal if abs(row[0] - 0.5) < 1e-9)
ux_center = vertical_center[1]
uy_center = horizontal_center[2]
(ROOT / "summary.txt").write_text(f"{ux_center:.9f}, {uy_center:.9f}\n", encoding="utf-8")
print(f"ux_center={ux_center:.9f} uy_center={uy_center:.9f}")
