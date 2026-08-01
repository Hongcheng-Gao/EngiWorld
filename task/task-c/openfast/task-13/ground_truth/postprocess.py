#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path("/home/user/Desktop")


def main() -> None:
    lines = (ROOT / "shutdown_case.out").read_text(encoding="utf-8", errors="ignore").splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.split()[:1] == ["Time"])
    headers = lines[header_index].split()
    units = lines[header_index + 1].split()
    time_i = headers.index("Time")
    speed_i = headers.index("RotSpeed")
    power_i = headers.index("GenPwr")
    pitch_indices = [headers.index(f"BldPitch{blade}") for blade in (1, 2, 3)]
    if (
        units[speed_i] != "(rpm)"
        or units[power_i] != "(kW)"
        or any(units[index] != "(deg)" for index in pitch_indices)
    ):
        raise ValueError("unexpected shutdown output units")
    all_rows: list[list[float]] = []
    for line in lines[header_index + 2 :]:
        fields = line.split()
        if len(fields) != len(headers):
            continue
        try:
            row = [float(value) for value in fields]
        except ValueError:
            continue
        all_rows.append(row)
    if len(all_rows) != 901 or abs(all_rows[-1][time_i] - 90.0) > 1.0e-9:
        raise ValueError("incomplete 90-second OpenFAST output")
    rows = [row for row in all_rows if row[time_i] >= 20.0]
    power_time = next(row[time_i] - 20.0 for row in rows if abs(row[power_i]) < 100.0)
    feather_time = next(
        row[time_i] - 20.0
        for row in rows
        if all(row[index] >= 89.9 for index in pitch_indices)
    )
    final_speed = abs(all_rows[-1][speed_i])
    (ROOT / "summary.txt").write_text(
        f"{power_time:.6f},{feather_time:.6f},{final_speed:.6f}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
