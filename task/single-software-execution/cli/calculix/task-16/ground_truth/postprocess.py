#!/usr/bin/env python3
from __future__ import annotations

import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MODE = re.compile(
    r"^\s*1\s+([+\-0-9.Ee]+)\s+([+\-0-9.Ee]+)\s+([+\-0-9.Ee]+)\s+([+\-0-9.Ee]+)",
    re.M,
)
ALPHA = 10.0
BETA = 1.0e-5


def main() -> int:
    text = (ROOT / "complex.dat").read_text(encoding="utf-8", errors="ignore")
    match = MODE.search(text)
    if not match:
        raise RuntimeError("first eigenmode row not found")
    frequency = float(match.group(3))
    omega = 2.0 * math.pi * frequency
    damping_ratio = ALPHA / (2.0 * omega) + BETA * omega / 2.0
    (ROOT / "summary.txt").write_text(
        f"{frequency:.9f},{damping_ratio:.9f}\n", encoding="ascii"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
