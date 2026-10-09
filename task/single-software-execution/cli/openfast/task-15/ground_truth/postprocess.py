#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path("/home/user/Desktop")


def main() -> None:
    lines = (ROOT / "minimal.out").read_text(encoding="utf-8", errors="ignore").splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.split()[:1] == ["Time"])
    headers = lines[header_index].split()
    units = lines[header_index + 1].split()
    time_i = headers.index("Time")
    power_i = headers.index("RtAeroPwr")
    thrust_i = headers.index("RtAeroFxh")
    if units[power_i] != "(W)" or units[thrust_i] != "(N)":
        raise ValueError("unexpected AeroDyn output units")
    rows: list[list[float]] = []
    for line in lines[header_index + 2 :]:
        fields = line.split()
        if len(fields) != len(headers):
            continue
        try:
            row = [float(value) for value in fields]
        except ValueError:
            continue
        if row[time_i] >= 20.0:
            rows.append(row)
    if len(rows) < 90:
        raise ValueError("insufficient samples in final 10 seconds")
    mean_power_kw = sum(row[power_i] for row in rows) / len(rows) / 1000.0
    max_thrust_kn = max(abs(row[thrust_i]) for row in rows) / 1000.0
    (ROOT / "summary.txt").write_text(
        f"{mean_power_kw:.6f},{max_thrust_kn:.6f}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
