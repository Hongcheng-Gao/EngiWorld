#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TIP_NODES = {11, 111, 211, 311}
HEADER = re.compile(r"displacements .* for set TIP and time\s+([+\-0-9.Ee]+)", re.I)
ROW = re.compile(r"^\s*(\d+)\s+([+\-0-9.Ee]+)\s+([+\-0-9.Ee]+)\s+([+\-0-9.Ee]+)")


def main() -> int:
    lines = (ROOT / "modal_dyn.dat").read_text(encoding="utf-8", errors="ignore").splitlines()
    history: list[tuple[float, float]] = []
    for index, line in enumerate(lines):
        match = HEADER.search(line)
        if not match:
            continue
        uy: list[float] = []
        for candidate in lines[index + 1 : index + 10]:
            row = ROW.match(candidate)
            if row and int(row.group(1)) in TIP_NODES:
                uy.append(float(row.group(3)))
                if len(uy) == len(TIP_NODES):
                    break
        if len(uy) == len(TIP_NODES):
            history.append((float(match.group(1)), sum(uy) / len(uy)))
    if not history:
        raise RuntimeError("no complete Tip displacement blocks found")
    peak = max(abs(uy) for _, uy in history)
    final = max(history, key=lambda point: point[0])[1]
    (ROOT / "summary.txt").write_text(f"{peak:.9f},{final:.9f}\n", encoding="ascii")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
