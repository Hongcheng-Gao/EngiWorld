#!/usr/bin/env python3
from __future__ import annotations

import cmath
import math
from pathlib import Path


ROOT = Path("/home/user/Desktop")
ONE_P_HZ = 9.0 / 60.0


def metrics(path: Path) -> tuple[float, float]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.split()[:1] == ["Time"])
    headers = lines[header_index].split()
    units = lines[header_index + 1].split()
    time_i = headers.index("Time")
    power_i = headers.index("RtAeroPwr")
    if units[power_i] != "(W)":
        raise ValueError("RtAeroPwr must be reported in watts")
    samples: list[tuple[float, float]] = []
    for line in lines[header_index + 2 :]:
        fields = line.split()
        if len(fields) != len(headers):
            continue
        try:
            row = [float(value) for value in fields]
        except ValueError:
            continue
        if row[time_i] >= 10.0:
            samples.append((row[time_i], row[power_i] / 1000.0))
    if len(samples) < 190:
        raise ValueError("insufficient samples for 1P analysis")
    mean = sum(value for _, value in samples) / len(samples)
    std = math.sqrt(sum((value - mean) ** 2 for _, value in samples) / len(samples))
    coefficient = sum(
        (value - mean) * cmath.exp(-2j * math.pi * ONE_P_HZ * time)
        for time, value in samples
    )
    amplitude = 2.0 * abs(coefficient) / len(samples)
    return std, amplitude


def main() -> None:
    no_tower_std, no_tower_amp = metrics(ROOT / "case_notower.out")
    tower_std, tower_amp = metrics(ROOT / "case_tower.out")
    ratio = tower_std / no_tower_std
    (ROOT / "summary.txt").write_text(
        f"{no_tower_std:.6f},{tower_std:.6f},{ratio:.6f},"
        f"{no_tower_amp:.6f},{tower_amp:.6f}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
