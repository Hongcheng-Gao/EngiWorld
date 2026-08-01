#!/usr/bin/env python3
from __future__ import annotations

import math
import re
from pathlib import Path


ROOT = Path("/home/user/Desktop")
ABS_TOL = 1e-5
REL_TOL = 2e-4
TIP_NODES = {11, 111, 211, 311}
EXPECTED = (45.26359, -35.27836)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def close(actual: float, expected: float) -> bool:
    return math.isfinite(actual) and abs(actual - expected) <= max(
        ABS_TOL, REL_TOL * max(1.0, abs(expected))
    )


def parse_summary(path: Path) -> tuple[float, float]:
    values = [float(value.strip()) for value in read(path).strip().split(",")]
    if len(values) != 2:
        raise ValueError("summary must contain two comma-separated values")
    return values[0], values[1]


def parse_tip_history(path: Path) -> list[tuple[float, float]]:
    lines = read(path).splitlines()
    history: list[tuple[float, float]] = []
    header = re.compile(r"displacements .* for set TIP and time\s+([+\-0-9.Ee]+)", re.I)
    row = re.compile(r"^\s*(\d+)\s+([+\-0-9.Ee]+)\s+([+\-0-9.Ee]+)\s+([+\-0-9.Ee]+)")
    for index, line in enumerate(lines):
        match = header.search(line)
        if not match:
            continue
        time = float(match.group(1))
        uy: list[float] = []
        for candidate in lines[index + 1 : index + 10]:
            result = row.match(candidate)
            if result and int(result.group(1)) in TIP_NODES:
                uy.append(float(result.group(3)))
                if len(uy) == len(TIP_NODES):
                    break
        if len(uy) == len(TIP_NODES):
            history.append((time, sum(uy) / len(uy)))
    if len(history) < 100:
        raise ValueError("incomplete modal-dynamic displacement history")
    return history


def valid_input(path: Path) -> bool:
    text = re.sub(r"\s+", "", read(path).lower())
    return all(
        token in text
        for token in (
            "*frequency,storage=yes",
            "*modaldynamic",
            "0.001,0.1",
            "*modal damping,rayleigh".replace(" ", ""),
            "*nodeprint,nset=tip,frequency=1",
            "*nodefile,nset=tip",
            "fixed,1,3,0.0",
        )
    ) and sum(
        float(value)
        for value in re.findall(r"(?:^|\n)\s*(?:11|111|211|311)\s*,\s*2\s*,\s*([+\-0-9.eE]+)", read(path))
        if float(value) < 0.0
    ) == -100.0


def check() -> bool:
    required = (
        "modal_dyn.inp",
        "modal_dyn.dat",
        "modal_dyn.frd",
        "modal_dyn.eig",
        "postprocess.py",
        "summary.txt",
    )
    if any(not (ROOT / name).is_file() or (ROOT / name).stat().st_size == 0 for name in required):
        return False
    if not valid_input(ROOT / "modal_dyn.inp"):
        return False

    history = parse_tip_history(ROOT / "modal_dyn.dat")
    peak = max(abs(uy) for _, uy in history)
    final_time, final = max(history, key=lambda point: point[0])
    summary = parse_summary(ROOT / "summary.txt")
    return close(final_time, 0.1) and all(
        close(actual, expected)
        for actual, expected in zip((peak, final, *summary), (*EXPECTED, *EXPECTED))
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
