#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path


ROOT = Path("/home/user/Desktop")


def population_std(values: list[float]) -> float:
    if not values:
        raise ValueError("empty sample window")
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def output_metrics(path: Path) -> tuple[float, float, float]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    header_index = next(
        index for index, line in enumerate(lines) if line.split()[:1] == ["Time"]
    )
    headers = lines[header_index].split()
    units = lines[header_index + 1].split()
    indices = {name: headers.index(name) for name in (
        "Time",
        "Wind1VelX",
        "RotSpeed",
        "BldPitch1",
        "GenPwr",
    )}
    expected_units = {
        "Time": "(s)",
        "Wind1VelX": "(m/s)",
        "RotSpeed": "(rpm)",
        "BldPitch1": "(deg)",
        "GenPwr": "(kW)",
    }
    for name, unit in expected_units.items():
        if units[indices[name]] != unit:
            raise ValueError(f"unexpected {name} unit")

    rows: list[list[float]] = []
    for line in lines[header_index + 2 :]:
        fields = line.split()
        if len(fields) != len(headers):
            continue
        try:
            rows.append([float(value) for value in fields])
        except ValueError:
            continue
    if len(rows) != 601:
        raise ValueError("expected 601 native 0.1-second samples")
    for index, row in enumerate(rows):
        if abs(row[indices["Time"]] - index / 10.0) > 2.0e-8:
            raise ValueError("unexpected output timestamps")

    wind = [row[indices["Wind1VelX"]] for row in rows]
    if population_std(wind) < 0.5:
        raise ValueError("output does not contain the supplied turbulent wind")
    window = [row for row in rows if row[indices["Time"]] >= 10.0]
    if len(window) != 501:
        raise ValueError("expected 501 samples from 10.0 through 60.0 seconds")
    return tuple(
        population_std([row[indices[channel]] for row in window])
        for channel in ("RotSpeed", "BldPitch1", "GenPwr")
    )


def main() -> None:
    soft = output_metrics(ROOT / "rosco_soft.out")
    stiff = output_metrics(ROOT / "rosco_stiff.out")
    summary = (soft[0], stiff[0], soft[1], stiff[1], soft[2], stiff[2])
    (ROOT / "summary.txt").write_text(
        ",".join(f"{value:.6f}" for value in summary) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
