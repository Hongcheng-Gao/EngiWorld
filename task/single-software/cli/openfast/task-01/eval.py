#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from pathlib import Path


FLOAT_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?(?![A-Za-z0-9_])")
REL_TOL = 1e-2
ABS_TOL = 1e-4
SPEEDS = (4, 8, 11, 15, 20)
REQUIRED_FILES = ['summary.txt', 'run_cases.py', 'postprocess.py'] + [
    f'{stem}_ws{speed}{suffix}'
    for speed in SPEEDS
    for stem, suffix in (('inflow', '.dat'), ('case', '.fst'), ('case', '.out'), ('case', '.log'))
]
EXPECTED_ROWS = [[4.0, 148.962779, 7.139224], [8.0, 1615.090892, 8.922937], [11.0, 4129.585441, 11.802749], [15.0, 4999.823664, 12.098685], [20.0, 5000.103239, 12.100202]]
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


def keyed_value(text: str, key: str) -> float:
    line = next(line for line in text.splitlines() if re.search(rf'\b{re.escape(key)}\b', line))
    return float(line.split()[0])


def output_means(path: Path) -> tuple[float, float]:
    lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    header = next(i for i, line in enumerate(lines) if line.split() and line.split()[0] == 'Time')
    names = lines[header].split()
    indices = [names.index(name) for name in ('Time', 'GenPwr', 'RotSpeed')]
    rows = [[float(value) for value in line.split()] for line in lines[header + 2:] if line.split()]
    if not rows or rows[-1][indices[0]] < 59.9:
        raise ValueError('incomplete OpenFAST output')
    tail = [row for row in rows if row[indices[0]] >= 50.0]
    return tuple(sum(row[index] for row in tail) / len(tail) for index in indices[1:])


def check_task(root: Path) -> bool:
    for rel in REQUIRED_FILES:
        if not file_ok(root / rel):
            return False

    actual = parse_numeric_rows(root / SUMMARY_FILE)
    if len(actual) != len(EXPECTED_ROWS):
        return False

    by_speed = {int(row[0]): row for row in actual if len(row) == 3}
    for row_e in EXPECTED_ROWS:
        speed = int(row_e[0])
        row_a = by_speed.get(speed, [])
        if len(row_a) != len(row_e):
            return False
        for a, e in zip(row_a, row_e):
            if not close_enough(a, e):
                return False
        inflow = (root / f'inflow_ws{speed}.dat').read_text(encoding='utf-8', errors='ignore')
        if keyed_value(inflow, 'WindType') != 1 or keyed_value(inflow, 'HWindSpeed') != speed:
            return False
        fst = (root / f'case_ws{speed}.fst').read_text(encoding='utf-8', errors='ignore')
        if f'"inflow_ws{speed}.dat"' not in fst:
            return False
        if 'OpenFAST terminated normally' not in (root / f'case_ws{speed}.log').read_text(errors='ignore'):
            return False
        power, rpm = output_means(root / f'case_ws{speed}.out')
        if not close_enough(power, row_a[1]) or not close_enough(rpm, row_a[2]):
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
