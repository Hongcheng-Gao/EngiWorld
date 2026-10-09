#!/usr/bin/env python3
from __future__ import annotations

import math
import re
from pathlib import Path


ROOT = Path("/home/user/Desktop")
EXPECTED = (-21030.264, 209.7981888)
FIXED_NODES = {1, 4, 5, 8}
ABS_TOL = 2e-5
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
    reaction: list[float] = []
    stresses: list[float] = []
    for index, line in enumerate(lines):
        if re.search(r"forces .* for set FIXNODES", line, re.I):
            for candidate in lines[index + 1 : index + 10]:
                row = NODE_ROW.match(candidate)
                if row and int(row.group(1)) in FIXED_NODES:
                    reaction.append(float(row.group(2)))
                    if len(reaction) == len(FIXED_NODES):
                        break
        elif re.search(r"stresses .* for set ALL_ELEMENTS", line, re.I):
            for candidate in lines[index + 1 :]:
                row = STRESS_ROW.match(candidate)
                if row:
                    stresses.append(mises(tuple(float(value) for value in row.groups())))
                elif stresses and not candidate.strip():
                    break
    if len(reaction) != len(FIXED_NODES) or not stresses:
        raise ValueError("incomplete force or stress output")
    return sum(reaction), max(stresses)


def parse_summary(path: Path) -> tuple[float, float]:
    values = [float(value.strip()) for value in read(path).strip().split(",")]
    if len(values) != 2:
        raise ValueError("summary must contain two values")
    return values[0], values[1]


def valid_input(path: Path) -> bool:
    text = re.sub(r"\s+", "", read(path).lower())
    return "type=displacement" not in text and all(
        token in text
        for token in (
            "*nset,nset=fixnodes1,4,5,8",
            "*nset,nset=pullnodes2,3,6,7",
            "fixnodes,1,3,0.",
            "pullnodes,1,1,0.1",
            "*nodeprint,nset=fixnodes",
            "rf,u",
            "*elprint,elset=all_elements",
        )
    )


def check() -> bool:
    required = ("pretension.inp", "pretension.dat", "pretension.frd", "pretension.sta", "postprocess.py", "summary.txt")
    if any(not (ROOT / name).is_file() or (ROOT / name).stat().st_size == 0 for name in required):
        return False
    if not valid_input(ROOT / "pretension.inp"):
        return False
    calculated = parse_result(ROOT / "pretension.dat")
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
