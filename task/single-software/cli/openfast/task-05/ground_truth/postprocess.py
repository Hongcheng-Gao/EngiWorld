#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path("/home/user/Desktop")


def main() -> None:
    lines = (ROOT / "subdyn_case.out").read_text(encoding="utf-8", errors="ignore").splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.split()[:1] == ["Time"])
    headers = lines[header_index].split()
    units = lines[header_index + 1].split()
    time_i = headers.index("Time")
    force_i = headers.index("ReactFXss")
    moment_i = headers.index("ReactMYss")
    if units[force_i] != "(N)" or units[moment_i] != "(N*m)":
        raise ValueError("unexpected SubDyn reaction units")
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
    mean_moment_mnm = sum(row[moment_i] for row in rows) / len(rows) / 1.0e6
    mean_force_kn = sum(row[force_i] for row in rows) / len(rows) / 1000.0
    (ROOT / "summary.txt").write_text(
        f"{mean_moment_mnm:.6f},{mean_force_kn:.6f}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
