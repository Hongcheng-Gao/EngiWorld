#!/usr/bin/env python3
from __future__ import annotations

import math
import re
from pathlib import Path


ROOT = Path("/home/user/Desktop")
TIP_NODES = {11, 111, 211, 311}
EXPECTED = (0.1008207, 0.000007788)
ABS_TOL = 2e-6
REL_TOL = 2e-4


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def close(actual: float, expected: float) -> bool:
    return math.isfinite(actual) and abs(actual - expected) <= max(
        ABS_TOL, REL_TOL * max(1.0, abs(expected))
    )


def summary(path: Path) -> tuple[float, float]:
    values = [float(value.strip()) for value in read(path).strip().split(",")]
    if len(values) != 2:
        raise ValueError("summary must contain two values")
    return values[0], values[1]


def history(path: Path) -> list[tuple[float, float]]:
    lines = read(path).splitlines()
    header = re.compile(r"displacements .* for set TIP and time\s+([+\-0-9.Ee]+)", re.I)
    row = re.compile(r"^\s*(\d+)\s+([+\-0-9.Ee]+)\s+([+\-0-9.Ee]+)\s+([+\-0-9.Ee]+)")
    result: list[tuple[float, float]] = []
    for index, line in enumerate(lines):
        match = header.search(line)
        if not match:
            continue
        uy: list[float] = []
        for candidate in lines[index + 1 : index + 10]:
            node = row.match(candidate)
            if node and int(node.group(1)) in TIP_NODES:
                uy.append(float(node.group(3)))
                if len(uy) == len(TIP_NODES):
                    break
        if len(uy) == len(TIP_NODES):
            result.append((float(match.group(1)), sum(uy) / len(uy)))
    if len(result) < 200:
        raise ValueError("incomplete fixed-increment transient history")
    return result


def valid_input(path: Path) -> bool:
    text = re.sub(r"\s+", "", read(path).lower())
    return "*basemotion" not in text and all(
        token in text
        for token in (
            "*amplitude,name=amp-1,time=totaltime",
            "0.0,0.0,0.5,1.0,1.0,0.0,2.0,0.0",
            "*dynamic,direct",
            "0.01,2.0",
            "*boundary,amplitude=amp-1",
            "base,2,2,0.1",
            "base,1,1,0.0",
            "base,3,3,0.0",
            "*nodeprint,nset=tip,frequency=1",
            "*nodefile,nset=tip",
        )
    )


def check() -> bool:
    required = ("earthquake.inp", "earthquake.dat", "earthquake.frd", "earthquake.sta", "postprocess.py", "summary.txt")
    if any(not (ROOT / name).is_file() or (ROOT / name).stat().st_size == 0 for name in required):
        return False
    if not valid_input(ROOT / "earthquake.inp"):
        return False
    response = history(ROOT / "earthquake.dat")
    peak = max(abs(uy) for _, uy in response)
    final_time, final = max(response, key=lambda point: point[0])
    reported = summary(ROOT / "summary.txt")
    return close(final_time, 2.0) and all(
        close(actual, expected)
        for actual, expected in zip((peak, final, *reported), (*EXPECTED, *EXPECTED))
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
