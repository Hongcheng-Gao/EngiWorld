#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from pathlib import Path


FLOAT_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?(?![A-Za-z0-9_])")
REL_TOL = 1e-2
ABS_TOL = 1e-4
ANGLES = (0, 5, 10, 15, 20)
REQUIRED_FILES = ['summary.txt', 'run_cases.py', 'postprocess.py', 'inflow_yaw_steady.dat'] + [
    f'{stem}_yaw_{angle}{suffix}' for angle in ANGLES
    for stem, suffix in (('case', '.fst'), ('case', '.out'), ('case', '.log'), ('elasto', '.dat'))
]
EXPECTED_ROWS = [[0.0, 4585.835790], [5.0, 4541.449278], [10.0, 4407.646856], [15.0, 4191.045931], [20.0, 3899.729668]]
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


def tail_power(path: Path) -> float:
    lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    header = next(i for i, line in enumerate(lines) if line.split() and line.split()[0] == 'Time')
    names = lines[header].split()
    ti, pi = names.index('Time'), names.index('GenPwr')
    rows = [[float(value) for value in line.split()] for line in lines[header + 2:] if line.split()]
    if not rows or rows[-1][ti] < 59.9:
        raise ValueError('incomplete output')
    tail = [row for row in rows if row[ti] >= 50.0]
    return sum(row[pi] for row in tail) / len(tail)


def check_task(root: Path) -> bool:
    for rel in REQUIRED_FILES:
        if not file_ok(root / rel):
            return False

    actual = parse_numeric_rows(root / SUMMARY_FILE)
    if len(actual) != len(EXPECTED_ROWS):
        return False

    by_angle = {int(row[0]): row for row in actual if len(row) == 2}
    for row_e in EXPECTED_ROWS:
        angle = int(row_e[0])
        row_a = by_angle.get(angle, [])
        if len(row_a) != len(row_e):
            return False
        for a, e in zip(row_a, row_e):
            if not close_enough(a, e):
                return False
        ed = (root / f'elasto_yaw_{angle}.dat').read_text(encoding='utf-8', errors='ignore')
        if keyed_value(ed, 'YawDOF').lower() != 'false' or float(keyed_value(ed, 'NacYaw')) != angle:
            return False
        fst = (root / f'case_yaw_{angle}.fst').read_text(encoding='utf-8', errors='ignore')
        if f'"elasto_yaw_{angle}.dat"' not in fst or '"inflow_yaw_steady.dat"' not in fst:
            return False
        if 'OpenFAST terminated normally' not in (root / f'case_yaw_{angle}.log').read_text(errors='ignore'):
            return False
        if not close_enough(tail_power(root / f'case_yaw_{angle}.out'), row_a[1]):
            return False
    inflow = (root / 'inflow_yaw_steady.dat').read_text(encoding='utf-8', errors='ignore')
    if float(keyed_value(inflow, 'WindType')) != 1 or float(keyed_value(inflow, 'HWindSpeed')) != 11.4:
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
