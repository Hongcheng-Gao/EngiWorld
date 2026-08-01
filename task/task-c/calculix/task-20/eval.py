#!/usr/bin/env python3
from __future__ import annotations

import math
import re
from pathlib import Path


ROOT = Path("/home/user/Desktop")
EXPECTED = (-0.01341792, 12.67647074)
ABS_TOL = 2e-6
REL_TOL = 2e-4
NODE_ROW = re.compile(r"^\s*(\d+)\s+([+\-0-9.Ee]+)\s+([+\-0-9.Ee]+)\s+([+\-0-9.Ee]+)")
STRESS_ROW = re.compile(r"^\s*\d+\s+\d+\s+" + r"\s+".join([r"([+\-0-9.Ee]+)"] * 6))


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def close(actual: float, expected: float) -> bool:
    return math.isfinite(actual) and abs(actual - expected) <= max(
        ABS_TOL, REL_TOL * max(1.0, abs(expected))
    )


def mises(values: tuple[float, float, float, float, float, float]) -> float:
    sx, sy, sz, txy, txz, tyz = values
    return math.sqrt(
        ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2) / 2.0
        + 3.0 * (txy**2 + txz**2 + tyz**2)
    )


def parse_result(path: Path) -> tuple[float, float]:
    lines = read(path).splitlines()
    node2_uy: list[float] = []
    stresses: list[float] = []
    for index, line in enumerate(lines):
        if re.search(r"displacements .* for set NALL", line, re.I):
            for candidate in lines[index + 1 : index + 14]:
                row = NODE_ROW.match(candidate)
                if row and int(row.group(1)) == 2:
                    node2_uy.append(float(row.group(3)))
                    break
        elif re.search(r"stresses .* for set EALL", line, re.I):
            for candidate in lines[index + 1 :]:
                row = STRESS_ROW.match(candidate)
                if row:
                    stresses.append(mises(tuple(float(value) for value in row.groups())))
                elif stresses and not candidate.strip():
                    break
    if not node2_uy or not stresses:
        raise ValueError("incomplete displacement or stress output")
    return node2_uy[-1], max(stresses)


def parse_summary(path: Path) -> tuple[float, float]:
    values = [float(value.strip()) for value in read(path).strip().split(",")]
    if len(values) != 2:
        raise ValueError("summary must contain two values")
    return values[0], values[1]


def valid_inputs(step1: Path, step2: Path) -> bool:
    first = re.sub(r"\s+", "", read(step1).lower())
    second = re.sub(r"\s+", "", read(step2).lower())
    return all(
        token in first
        for token in ("*restart,write,frequency=1", "*cload2,2,-100.0")
    ) and all(
        token in second
        for token in (
            "*restart,read",
            "*cload2,2,-200.0",
            "*nodeprint,nset=nall,frequency=999",
            "*elprint,elset=eall,frequency=999",
        )
    )


def check() -> bool:
    required = (
        "step1.inp", "step1.frd", "step1.rout", "step1.sta",
        "step2.inp", "step2.rin", "step2.dat", "step2.frd", "step2.sta",
        "postprocess.py", "summary.txt",
    )
    if any(not (ROOT / name).is_file() or (ROOT / name).stat().st_size == 0 for name in required):
        return False
    if (ROOT / "step1.rout").read_bytes() != (ROOT / "step2.rin").read_bytes():
        return False
    if not valid_inputs(ROOT / "step1.inp", ROOT / "step2.inp"):
        return False
    calculated = parse_result(ROOT / "step2.dat")
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
