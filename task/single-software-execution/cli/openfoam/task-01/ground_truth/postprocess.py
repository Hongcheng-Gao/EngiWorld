#!/usr/bin/env python3
from __future__ import annotations

import csv
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "channel"
HEIGHT = 0.1
MEAN_SPEED = 0.1
THEORY_MAX = 1.5 * MEAN_SPEED


def sample() -> Path:
    command = (
        ". /opt/openfoam11/etc/bashrc && "
        "postProcess -case /home/user/Desktop/channel -latestTime -func sampleDict "
        "> /home/user/Desktop/channel/log.sample 2>&1"
    )
    subprocess.run(["bash", "-lc", command], check=True, timeout=120)
    candidates = list((CASE / "postProcessing/sampleDict").glob("*/outletLine.xy"))
    if not candidates:
        raise FileNotFoundError("OpenFOAM did not create outletLine.xy")
    return max(candidates, key=lambda path: float(path.parent.name))


def read_profile(path: Path) -> list[tuple[float, float, float, float]]:
    rows: list[tuple[float, float, float, float]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        fields = line.split()
        if len(fields) < 4 or fields[0].startswith("#"):
            continue
        values = [float(value) for value in fields[:4]]
        y, ux, uy, uz = values
        rows.append((y, ux, uy, uz))
    if len(rows) != 80:
        raise ValueError(f"expected 80 sampled points, got {len(rows)}")
    return rows


def main() -> None:
    profile = read_profile(sample())
    output_rows: list[tuple[float, float, float, float]] = []
    for y, ux, uy, uz in profile:
        if abs(uy) > 1.0e-5 or abs(uz) > 1.0e-5:
            raise ValueError("unexpected transverse outlet velocity")
        theory = 6.0 * MEAN_SPEED * y * (HEIGHT - y) / HEIGHT**2
        output_rows.append((y, ux, theory, abs(ux - theory)))
    cfd_max = max(row[1] for row in output_rows)
    max_error_percent = max(row[3] for row in output_rows) / THEORY_MAX * 100.0

    with (ROOT / "outlet_profile.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("y_m", "ux_cfd_mps", "ux_theory_mps", "abs_error_mps"))
        writer.writerows(output_rows)
    (ROOT / "summary.txt").write_text(
        f"{cfd_max:.9f},{THEORY_MAX:.9f},{max_error_percent:.6f}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
