#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path("/home/user/Desktop")


def main() -> None:
    output = ROOT / "earthquake_sd.SD.out"
    lines = output.read_text(encoding="utf-8", errors="ignore").splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.split()[:1] == ["Time"])
    headers = lines[header_index].split()
    units = lines[header_index + 1].split()
    time_i = headers.index("Time")
    displacement_i = headers.index("Intf1TDXss")
    moment_i = headers.index("ReactMYss")
    if units[displacement_i] != "(m)" or units[moment_i] != "(N*m)":
        raise ValueError("unexpected SubDyn output units")
    rows: list[list[float]] = []
    for line in lines[header_index + 2 :]:
        fields = line.split()
        if len(fields) != len(headers):
            continue
        try:
            row = [float(value) for value in fields]
        except ValueError:
            continue
        if row[time_i] >= 30.0:
            rows.append(row)
    if len(rows) < 2990:
        raise ValueError("insufficient samples in the excitation interval")
    peak_displacement = max(abs(row[displacement_i]) for row in rows)
    peak_moment_mnm = max(abs(row[moment_i]) for row in rows) / 1.0e6
    (ROOT / "summary.txt").write_text(
        f"{peak_displacement:.6f},{peak_moment_mnm:.6f}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
