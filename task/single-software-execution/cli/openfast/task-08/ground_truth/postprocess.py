#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path("/home/user/Desktop")


def main() -> None:
    lines = (ROOT / "eog_case.out").read_text(encoding="utf-8", errors="ignore").splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.split()[:1] == ["Time"])
    headers = lines[header_index].split()
    units = lines[header_index + 1].split()
    time_i = headers.index("Time")
    root_i = headers.index("RootMyb1")
    disp_i = headers.index("TTDspFA")
    if units[root_i] != "(kN-m)" or units[disp_i] != "(m)":
        raise ValueError("unexpected load or displacement units")
    rows: list[list[float]] = []
    for line in lines[header_index + 2 :]:
        fields = line.split()
        if len(fields) != len(headers):
            continue
        try:
            row = [float(value) for value in fields]
        except ValueError:
            continue
        if 10.0 <= row[time_i] <= 30.0:
            rows.append(row)
    if len(rows) < 190:
        raise ValueError("insufficient gust-period samples")
    root_peak = max(abs(row[root_i]) for row in rows)
    displacement_peak = max(abs(row[disp_i]) for row in rows)
    (ROOT / "summary.txt").write_text(
        f"{root_peak:.6f},{displacement_peak:.6f}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
