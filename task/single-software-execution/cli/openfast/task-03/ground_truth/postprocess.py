#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path("/home/user/Desktop")


def read_output(path: Path) -> tuple[list[str], list[str], list[list[float]]]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.split()[:1] == ["Time"])
    headers = lines[header_index].split()
    units = lines[header_index + 1].split()
    rows: list[list[float]] = []
    for line in lines[header_index + 2 :]:
        fields = line.split()
        if len(fields) != len(headers):
            continue
        try:
            rows.append([float(value) for value in fields])
        except ValueError:
            continue
    return headers, units, rows


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("empty averaging window")
    return sum(values) / len(values)


def main() -> None:
    headers, units, rows = read_output(ROOT / "case.out")
    indexes = {name: headers.index(name) for name in ("Time", "BldPitch1", "BldPitch2", "BldPitch3", "GenPwr")}
    if units[indexes["Time"]] != "(s)" or units[indexes["GenPwr"]] != "(kW)":
        raise ValueError("unexpected output units")

    pre_power = mean([row[indexes["GenPwr"]] for row in rows if 20.0 <= row[indexes["Time"]] < 30.0])
    post_power = mean([row[indexes["GenPwr"]] for row in rows if 40.0 <= row[indexes["Time"]] <= 50.0])
    pre_pitch = mean(
        [
            sum(row[indexes[name]] for name in ("BldPitch1", "BldPitch2", "BldPitch3")) / 3.0
            for row in rows
            if 20.0 <= row[indexes["Time"]] < 30.0
        ]
    )
    low = pre_pitch + 0.1 * (10.0 - pre_pitch)
    high = pre_pitch + 0.9 * (10.0 - pre_pitch)
    maneuver = [
        (
            row[indexes["Time"]],
            sum(row[indexes[name]] for name in ("BldPitch1", "BldPitch2", "BldPitch3")) / 3.0,
        )
        for row in rows
        if row[indexes["Time"]] >= 30.0
    ]
    t10 = next(time for time, pitch in maneuver if pitch >= low)
    t90 = next(time for time, pitch in maneuver if pitch >= high)
    (ROOT / "summary.txt").write_text(
        f"{pre_power:.6f},{post_power:.6f},{t90 - t10:.6f}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
