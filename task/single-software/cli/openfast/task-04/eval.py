#!/usr/bin/env python3
from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np


ROOT = Path("/home/user/Desktop")
EXPECTED = {"fa": 0.332699, "ss": 0.321947}
ABS_TOL = 2e-5
REL_TOL = 2e-4
STATE_ROW = re.compile(r"^\s*(\d+)\s+.*?\s+[FT]\s+\d+\s+(.*)$")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def close(actual: float, expected: float) -> bool:
    return math.isfinite(actual) and abs(actual - expected) <= max(
        ABS_TOL, REL_TOL * max(1.0, abs(expected))
    )


def parameter(text: str, name: str) -> str:
    match = re.search(rf"^\s*(\S+).*?\s{name}\s+-", text, re.MULTILINE)
    if not match:
        raise ValueError(f"missing parameter {name}")
    return match.group(1).rstrip(",").lower()


def valid_inputs(main_path: Path, ed_path: Path) -> bool:
    main = read(main_path)
    ed = read(ed_path)
    main_expected = {
        "CompElast": "1",
        "CompInflow": "0",
        "CompAero": "0",
        "CompServo": "0",
        "TMax": "0.1",
        "Gravity": "0",
        "ModCoupling": "1",
        "Linearize": "true",
        "CalcSteady": "false",
        "NLinTimes": "1",
        "LinTimes": "0.09",
        "LinInputs": "0",
        "LinOutputs": "0",
        "LinOutMod": "false",
        "LinOutJac": "false",
    }
    ed_expected = {
        "FlapDOF1": "false",
        "FlapDOF2": "false",
        "EdgeDOF": "false",
        "DrTrDOF": "false",
        "GenDOF": "false",
        "YawDOF": "false",
        "TwFADOF1": "true",
        "TwFADOF2": "false",
        "TwSSDOF1": "true",
        "TwSSDOF2": "false",
        "RotSpeed": "0",
    }
    if any(parameter(main, key) != value for key, value in main_expected.items()):
        return False
    if any(parameter(ed, key) != value for key, value in ed_expected.items()):
        return False
    return True


def parse_linear_model(path: Path) -> tuple[np.ndarray, dict[str, int]]:
    text = read(path)
    if "at commit v5.0.0" not in text or "Number of continuous states:         4" not in text:
        raise ValueError("unexpected OpenFAST linearization header")
    if "Number of inputs:                    0" not in text:
        raise ValueError("linear model contains inputs")
    if "Number of outputs:                   0" not in text:
        raise ValueError("linear model contains outputs")

    lines = text.splitlines()
    state_indices: dict[str, int] = {}
    in_states = False
    for line in lines:
        if line.strip() == "Order of continuous states:":
            in_states = True
            continue
        if in_states and line.strip() == "Order of continuous state derivatives:":
            break
        if not in_states:
            continue
        match = STATE_ROW.match(line)
        if not match:
            continue
        description = match.group(2).lower()
        if "first time derivative" in description:
            continue
        if "1st tower fore-aft bending mode dof" in description:
            state_indices["fa"] = int(match.group(1)) - 1
        elif "1st tower side-to-side bending mode dof" in description:
            state_indices["ss"] = int(match.group(1)) - 1

    header_index = next(
        index for index, line in enumerate(lines) if re.fullmatch(r"\s*A:\s*4\s*x\s*4\s*", line)
    )
    matrix = np.array(
        [[float(value) for value in lines[header_index + row + 1].split()] for row in range(4)],
        dtype=float,
    )
    if matrix.shape != (4, 4) or set(state_indices) != {"fa", "ss"}:
        raise ValueError("incomplete tower-only state matrix")
    return matrix, state_indices


def modal_frequencies(matrix: np.ndarray, state_indices: dict[str, int]) -> dict[str, float]:
    eigenvalues, eigenvectors = np.linalg.eig(matrix)
    modes = [index for index, value in enumerate(eigenvalues) if value.imag > 1e-8]
    if len(modes) != 2:
        raise ValueError("expected two oscillatory modes")
    result: dict[str, float] = {}
    for index in modes:
        label = max(state_indices, key=lambda key: abs(eigenvectors[state_indices[key], index]))
        if label in result:
            raise ValueError("ambiguous tower mode participation")
        result[label] = abs(eigenvalues[index].imag) / (2.0 * math.pi)
    return result


def parse_summary(path: Path) -> dict[str, float]:
    lines = [line.strip() for line in read(path).splitlines() if line.strip()]
    if len(lines) != 1:
        raise ValueError("summary must contain exactly one nonblank line")
    values = [float(value.strip()) for value in lines[0].split(",")]
    if len(values) != 2:
        raise ValueError("summary must contain exactly two comma-separated values")
    return {"fa": values[0], "ss": values[1]}


def check() -> bool:
    required = (
        "linear.fst",
        "NRELOffshrBsline5MW_Linear_ElastoDyn.dat",
        "linear.1.lin",
        "linear.out",
        "postprocess.py",
        "summary.txt",
    )
    if any(not (ROOT / name).is_file() or (ROOT / name).stat().st_size == 0 for name in required):
        return False
    if not valid_inputs(
        ROOT / "linear.fst", ROOT / "NRELOffshrBsline5MW_Linear_ElastoDyn.dat"
    ):
        return False
    output = read(ROOT / "linear.out")
    if "at commit v5.0.0" not in output or not re.search(r"^Time\s+ConvIter", output, re.MULTILINE):
        return False
    matrix, state_indices = parse_linear_model(ROOT / "linear.1.lin")
    calculated = modal_frequencies(matrix, state_indices)
    reported = parse_summary(ROOT / "summary.txt")
    return all(
        close(calculated[name], EXPECTED[name]) and close(reported[name], EXPECTED[name])
        for name in ("fa", "ss")
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
