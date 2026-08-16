#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from pathlib import Path


FLOAT_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?(?![A-Za-z0-9_])")
REL_TOL = 1e-2
ABS_TOL = 1e-4
SPEEDS = (4, 8, 11, 15, 20)
REQUIRED_FILES = ['summary.txt', 'batch_run.py', 'batch_post.py'] + [
    f'case_ws{speed}{suffix}' for speed in SPEEDS for suffix in ('.fst', '.out', '.log')
] + [f'NRELOffshrBsline5MW_InflowWind_{speed}.dat' for speed in SPEEDS]
EXPECTED_ROWS = [[4.0, 148.961900, 7.139225, 0.0], [8.0, 1615.091080, 8.922938, 0.0], [11.0, 4129.585700, 11.802750, 0.0], [15.0, 4999.824037, 12.098685, 9.619814], [20.0, 5000.103390, 12.100203, 16.936624]]
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


def keyed_value(text: str, key: str) -> str:
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == key:
            return parts[0].strip('"')
    raise KeyError(key)


def tail_means(path: Path) -> tuple[float, float, float]:
    lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    header = next(i for i, line in enumerate(lines) if line.split() and line.split()[0] == 'Time')
    names = lines[header].split()
    indices = [names.index(name) for name in ('Time', 'GenPwr', 'RotSpeed', 'BldPitch1')]
    rows = [[float(value) for value in line.split()] for line in lines[header + 2:] if line.split()]
    if not rows or rows[-1][indices[0]] < 59.9:
        raise ValueError('incomplete output')
    tail = [row for row in rows if row[indices[0]] >= 50.0]
    return tuple(sum(row[index] for row in tail) / len(tail) for index in indices[1:])


def check_task(root: Path) -> bool:
    for rel in REQUIRED_FILES:
        if not file_ok(root / rel):
            return False

    actual = parse_numeric_rows(root / SUMMARY_FILE)
    if len(actual) != len(EXPECTED_ROWS):
        return False

    by_speed = {int(row[0]): row for row in actual if len(row) == 4}
    for row_e in EXPECTED_ROWS:
        speed = int(row_e[0])
        row_a = by_speed.get(speed, [])
        if len(row_a) != len(row_e):
            return False
        for a, e in zip(row_a, row_e):
            if not close_enough(a, e):
                return False
        inflow_name = f'NRELOffshrBsline5MW_InflowWind_{speed}.dat'
        inflow = (root / inflow_name).read_text(encoding='utf-8', errors='ignore')
        if float(keyed_value(inflow, 'WindType')) != 1 or float(keyed_value(inflow, 'HWindSpeed')) != speed:
            return False
        if f'"{inflow_name}"' not in (root / f'case_ws{speed}.fst').read_text(errors='ignore'):
            return False
        if 'OpenFAST terminated normally' not in (root / f'case_ws{speed}.log').read_text(errors='ignore'):
            return False
        means = tail_means(root / f'case_ws{speed}.out')
        if any(not close_enough(value, expected) for value, expected in zip(means, row_a[1:])):
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
