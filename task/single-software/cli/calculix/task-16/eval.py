#!/usr/bin/env python3
from __future__ import annotations

import math
import re
from pathlib import Path


ROOT = Path("/home/user/Desktop")
EXPECTED = (33.69477, 0.024675711)
ABS_TOL = 2e-6
REL_TOL = 2e-4
MODE = re.compile(
    r"^\s*1\s+([+\-0-9.Ee]+)\s+([+\-0-9.Ee]+)\s+([+\-0-9.Ee]+)\s+([+\-0-9.Ee]+)",
    re.M,
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def close(actual: float, expected: float) -> bool:
    return math.isfinite(actual) and abs(actual - expected) <= max(
        ABS_TOL, REL_TOL * max(1.0, abs(expected))
    )


def parse_result(path: Path) -> tuple[float, float]:
    match = MODE.search(read(path))
    if not match:
        raise ValueError("first eigenmode row missing")
    frequency = float(match.group(3))
    omega = 2.0 * math.pi * frequency
    return frequency, 10.0 / (2.0 * omega) + 1.0e-5 * omega / 2.0


def parse_summary(path: Path) -> tuple[float, float]:
    values = [float(value.strip()) for value in read(path).strip().split(",")]
    if len(values) != 2:
        raise ValueError("summary must contain two values")
    return values[0], values[1]


def valid_input(path: Path) -> bool:
    text = re.sub(r"\s+", "", read(path).lower())
    return all(
        token in text
        for token in (
            "*damping,alpha=10.0,beta=1.0e-5",
            "*frequency,storage=yes",
            "\n5\n".replace("\n", ""),
            "fixed,1,3,0.0",
            "*nodefile,nset=tip",
        )
    )


def check() -> bool:
    required = ("complex.inp", "complex.dat", "complex.frd", "complex.eig", "complex.sta", "postprocess.py", "summary.txt")
    if any(not (ROOT / name).is_file() or (ROOT / name).stat().st_size == 0 for name in required):
        return False
    if not valid_input(ROOT / "complex.inp"):
        return False
    calculated = parse_result(ROOT / "complex.dat")
    reported = parse_summary(ROOT / "summary.txt")
    return all(
        close(actual, expected)
        for actual, expected in zip((*calculated, *reported), (*EXPECTED, *EXPECTED))
    )


def main() -> int:
    try:
        result = check()
    except Exception:
        result = False
    print("True" if result else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
