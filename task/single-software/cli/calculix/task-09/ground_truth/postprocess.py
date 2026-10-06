#!/usr/bin/env python3
from __future__ import annotations

import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TIP_NODES = {11, 111, 211, 311}
FREQUENCY = re.compile(r"F R E Q U E N C Y\s+([+\-0-9.Ee]+) \(CYCLES/TIME\)")
DISPLACEMENT = re.compile(r"displacements .* for set TIP and time", re.I)
ROW = re.compile(r"^\s*(\d+)\s+([+\-0-9.Ee]+)\s+([+\-0-9.Ee]+)\s+([+\-0-9.Ee]+)")


def main() -> int:
    lines = (ROOT / "ssd.dat").read_text(encoding="utf-8", errors="ignore").splitlines()
    responses: list[tuple[float, float]] = []
    frequency: float | None = None
    components: list[float] = []
    for index, line in enumerate(lines):
        match = FREQUENCY.search(line)
        if match:
            frequency = float(match.group(1))
            components = []
        elif frequency is not None and DISPLACEMENT.search(line):
            uy: list[float] = []
            for candidate in lines[index + 1 : index + 10]:
                row = ROW.match(candidate)
                if row and int(row.group(1)) in TIP_NODES:
                    uy.append(float(row.group(3)))
                    if len(uy) == len(TIP_NODES):
                        break
            if len(uy) == len(TIP_NODES):
                components.append(sum(uy) / len(uy))
                if len(components) == 2:
                    responses.append((frequency, math.hypot(*components)))
                    frequency = None
    if not responses:
        raise RuntimeError("no complete real/imaginary Tip displacement pairs found")
    peak_frequency, peak_amplitude = max(responses, key=lambda point: point[1])
    (ROOT / "summary.txt").write_text(
        f"{peak_frequency:.9f},{peak_amplitude:.9f}\n", encoding="ascii"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
