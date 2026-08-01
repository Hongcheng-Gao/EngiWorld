#!/usr/bin/env python3
from __future__ import annotations

import math
import re
from pathlib import Path


ROOT = Path("/home/user/Desktop")
ABS_TOL = 1e-5
REL_TOL = 2e-4
TIP_NODES = {11, 111, 211, 311}
EXPECTED = (33.694774019, 887.666260495)


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


def parse_frequency_response(path: Path) -> list[tuple[float, float]]:
    lines = read(path).splitlines()
    frequency_header = re.compile(r"F R E Q U E N C Y\s+([+\-0-9.Ee]+) \(CYCLES/TIME\)")
    displacement_header = re.compile(r"displacements .* for set TIP and time", re.I)
    row = re.compile(r"^\s*(\d+)\s+([+\-0-9.Ee]+)\s+([+\-0-9.Ee]+)\s+([+\-0-9.Ee]+)")
    response: list[tuple[float, float]] = []
    frequency: float | None = None
    components: list[float] = []
    index = 0
    while index < len(lines):
        match = frequency_header.search(lines[index])
        if match:
            frequency = float(match.group(1))
            components = []
        elif frequency is not None and displacement_header.search(lines[index]):
            uy: list[float] = []
            for candidate in lines[index + 1 : index + 10]:
                result = row.match(candidate)
                if result and int(result.group(1)) in TIP_NODES:
                    uy.append(float(result.group(3)))
                    if len(uy) == len(TIP_NODES):
                        break
            if len(uy) == len(TIP_NODES):
                components.append(sum(uy) / len(uy))
                if len(components) == 2:
                    response.append((frequency, math.hypot(components[0], components[1])))
                    frequency = None
        index += 1
    if len(response) < 20:
        raise ValueError("incomplete steady-state response data")
    return response


def valid_input(path: Path) -> bool:
    raw = read(path)
    text = re.sub(r"\s+", "", raw.lower())
    loads = [
        float(value)
        for value in re.findall(r"(?:^|\n)\s*(?:11|111|211|311)\s*,\s*2\s*,\s*([+\-0-9.eE]+)", raw)
        if float(value) > 0.0
    ]
    return all(
        token in text
        for token in (
            "*frequency,storage=yes",
            "*steadystatedynamics",
            "1.0,100.0,20",
            "*modaldamping,rayleigh",
            ",,5.0,1.0e-5",
            "*nodeprint,nset=tip",
            "*nodefile,nset=tip",
            "fixed,1,3,0.0",
        )
    ) and math.isclose(sum(loads), 100.0, abs_tol=1e-9)


def check() -> bool:
    required = (
        "ssd.inp",
        "ssd.dat",
        "ssd.frd",
        "ssd.eig",
        "postprocess.py",
        "summary.txt",
    )
    if any(not (ROOT / name).is_file() or (ROOT / name).stat().st_size == 0 for name in required):
        return False
    if not valid_input(ROOT / "ssd.inp"):
        return False

    peak = max(parse_frequency_response(ROOT / "ssd.dat"), key=lambda point: point[1])
    summary = parse_summary(ROOT / "summary.txt")
    return all(
        close(actual, expected)
        for actual, expected in zip((*peak, *summary), (*EXPECTED, *EXPECTED))
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
