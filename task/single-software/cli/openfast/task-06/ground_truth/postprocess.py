#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path


ROOT = Path("/home/user/Desktop")


def main() -> None:
    lines = (ROOT / "moordyn_case.out").read_text(encoding="utf-8", errors="ignore").splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.split()[:1] == ["Time"])
    headers = lines[header_index].split()
    units = lines[header_index + 1].split()
    time_i = headers.index("Time")
    tension_i = [headers.index(f"FAIRTEN{i}") for i in (1, 2, 3)]
    if any(units[index] != "(N)" for index in tension_i):
        raise ValueError("unexpected fairlead-tension units")
    rows: list[list[float]] = []
    for line in lines[header_index + 2 :]:
        fields = line.split()
        if len(fields) != len(headers):
            continue
        try:
            row = [float(value) for value in fields]
        except ValueError:
            continue
        if row[time_i] >= 60.0:
            rows.append(row)
    if len(rows) < 590:
        raise ValueError("insufficient samples in final 60 seconds")
    means = [sum(row[index] for row in rows) / len(rows) / 1000.0 for index in tension_i]
    stds = [
        math.sqrt(
            sum((row[index] / 1000.0 - means[j]) ** 2 for row in rows) / len(rows)
        )
        for j, index in enumerate(tension_i)
    ]
    (ROOT / "summary.txt").write_text(
        f"{means[0]:.6f},{max(stds):.6f}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
