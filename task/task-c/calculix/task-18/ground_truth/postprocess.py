#!/usr/bin/env python3
from __future__ import annotations

import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FIXED_NODES = {1, 4, 5, 8}
FORCE_HEADER = re.compile(r"forces .* for set FIXNODES", re.I)
STRESS_HEADER = re.compile(r"stresses .* for set ALL_ELEMENTS", re.I)
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
    lines = (ROOT / "pretension.dat").read_text(encoding="utf-8", errors="ignore").splitlines()
    reaction_fx: list[float] = []
    stress_values: list[float] = []
    for index, line in enumerate(lines):
        if FORCE_HEADER.search(line):
            for candidate in lines[index + 1 : index + 10]:
                row = NODE_ROW.match(candidate)
                if row and int(row.group(1)) in FIXED_NODES:
                    reaction_fx.append(float(row.group(2)))
                    if len(reaction_fx) == len(FIXED_NODES):
                        break
        elif STRESS_HEADER.search(line):
            for candidate in lines[index + 1 :]:
                row = STRESS_ROW.match(candidate)
                if row:
                    stress_values.append(mises(tuple(float(value) for value in row.groups())))
                elif stress_values and not candidate.strip():
                    break
    if len(reaction_fx) != len(FIXED_NODES) or not stress_values:
        raise RuntimeError("incomplete force or stress output")
    (ROOT / "summary.txt").write_text(
        f"{sum(reaction_fx):.9f},{max(stress_values):.9f}\n", encoding="ascii"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
