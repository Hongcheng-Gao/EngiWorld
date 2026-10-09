#!/usr/bin/env python3
from __future__ import annotations

import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DISPLACEMENT_HEADER = re.compile(r"displacements .* for set NALL", re.I)
STRESS_HEADER = re.compile(r"stresses .* for set EALL", re.I)
NODE_ROW = re.compile(r"^\s*(\d+)\s+([+\-0-9.Ee]+)\s+([+\-0-9.Ee]+)\s+([+\-0-9.Ee]+)")
STRESS_ROW = re.compile(
    r"^\s*\d+\s+\d+\s+" + r"\s+".join([r"([+\-0-9.Ee]+)"] * 6)
)


def mises(values: tuple[float, float, float, float, float, float]) -> float:
    sx, sy, sz, txy, txz, tyz = values
    return math.sqrt(
        ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2) / 2.0
        + 3.0 * (txy**2 + txz**2 + tyz**2)
    )


def main() -> int:
    lines = (ROOT / "step2.dat").read_text(encoding="utf-8", errors="ignore").splitlines()
    node2_uy: list[float] = []
    stress_values: list[float] = []
    for index, line in enumerate(lines):
        if DISPLACEMENT_HEADER.search(line):
            for candidate in lines[index + 1 : index + 14]:
                row = NODE_ROW.match(candidate)
                if row and int(row.group(1)) == 2:
                    node2_uy.append(float(row.group(3)))
                    break
        elif STRESS_HEADER.search(line):
            for candidate in lines[index + 1 :]:
                row = STRESS_ROW.match(candidate)
                if row:
                    stress_values.append(mises(tuple(float(value) for value in row.groups())))
                elif stress_values and not candidate.strip():
                    break
    if not node2_uy or not stress_values:
        raise RuntimeError("incomplete displacement or stress output")
    (ROOT / "summary.txt").write_text(
        f"{node2_uy[-1]:.9f},{max(stress_values):.9f}\n", encoding="ascii"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
