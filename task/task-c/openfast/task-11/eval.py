#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import numpy as np
from pathlib import Path


FLOAT_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?(?![A-Za-z0-9_])")
REL_TOL = 1e-2
ABS_TOL = 1e-4
REQUIRED_FILES = ['summary.txt', 'postprocess.py', 'blade_mode.fst',
                  'NRELOffshrBsline5MW_ElastoDyn_BladeMode.dat', 'blade_mode.log', 'blade_mode.1.BD1.lin']
EXPECTED_ROWS = [[0.740348, 1.111220]]
SUMMARY_FILE = 'summary.txt'


def parse_floats(text: str) -> list[float]:
    values: list[float] = []
    for token in FLOAT_RE.findall(text):
        try:
            values.append(float(token))
        except ValueError:
            continue
    return values


def parse_numeric_rows(path: Path) -> list[list[float]]:
    rows: list[list[float]] = []
    for raw in path.read_text(encoding='utf-8', errors='ignore').splitlines():
        line = raw.strip()
        if (not line) or line.startswith('#'):
            continue
        vals = parse_floats(line)
        if vals:
            rows.append(vals)
    return rows


def file_ok(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def close_enough(actual: float, expected: float) -> bool:
    return abs(actual - expected) <= max(ABS_TOL, REL_TOL * max(1.0, abs(expected)))


def lin_frequencies(path: Path) -> tuple[float, float]:
    lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    count = int(next(line.split(':', 1)[1] for line in lines if 'Number of continuous states:' in line))
    start = next(i for i, line in enumerate(lines) if line.startswith('A:')) + 1
    matrix = np.array([[float(value) for value in line.split()] for line in lines[start:start + count]])
    if matrix.shape != (count, count):
        raise ValueError('incomplete A matrix')
    frequencies = sorted(value.imag / (2 * np.pi) for value in np.linalg.eigvals(matrix) if value.imag > 1e-6)
    return frequencies[0], frequencies[1]


def check_task(root: Path) -> bool:
    for rel in REQUIRED_FILES:
        if not file_ok(root / rel):
            return False

    actual = parse_numeric_rows(root / SUMMARY_FILE)
    if len(actual) != len(EXPECTED_ROWS):
        return False

    for row_a, row_e in zip(actual, EXPECTED_ROWS):
        if len(row_a) != len(row_e):
            return False
        for a, e in zip(row_a, row_e):
            if not close_enough(a, e):
                return False

    fst = (root / 'blade_mode.fst').read_text(encoding='utf-8', errors='ignore')
    required_switches = ('          2   CompElast', '          0   CompInflow', '          0   CompAero',
                         '          0   CompServo', 'True          Linearize', '          1   NLinTimes')
    if not all(token in fst for token in required_switches):
        return False
    if 'OpenFAST terminated normally' not in (root / 'blade_mode.log').read_text(errors='ignore'):
        return False
    flap, edge = lin_frequencies(root / 'blade_mode.1.BD1.lin')
    if not close_enough(flap, actual[0][0]) or not close_enough(edge, actual[0][1]):
        return False

    return True


def evaluate() -> int:
    root = Path(os.environ.get('EVAL_OUTPUT_ROOT', '/home/user/Desktop'))
    try:
        ok = check_task(root)
    except Exception:
        ok = False
    return 1 if ok else 0


def main() -> int:
    result = evaluate()
    print('True' if result == 1 else 'False')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
