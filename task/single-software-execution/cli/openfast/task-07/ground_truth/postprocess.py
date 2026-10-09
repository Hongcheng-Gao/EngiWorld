#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path("/home/user/Desktop")


def mean_power(path: Path) -> float:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.split()[:1] == ["Time"])
    headers = lines[header_index].split()
    units = lines[header_index + 1].split()
    time_i = headers.index("Time")
    power_i = headers.index("RtAeroPwr")
    if units[power_i] != "(W)":
        raise ValueError("RtAeroPwr must be reported in watts")
    values: list[float] = []
    for line in lines[header_index + 2 :]:
        fields = line.split()
        if len(fields) != len(headers):
            continue
        try:
            row = [float(value) for value in fields]
        except ValueError:
            continue
        if row[time_i] >= 570.0:
            values.append(row[power_i])
    if len(values) < 590:
        raise ValueError("insufficient samples in final 60 seconds")
    return sum(values) / len(values) / 1000.0


def main() -> None:
    powers = [mean_power(ROOT / f"farm.T{i}.out") for i in (1, 2)]
    (ROOT / "summary.txt").write_text(
        f"{powers[0]:.6f},{powers[1]:.6f}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
