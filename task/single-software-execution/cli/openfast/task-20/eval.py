#!/usr/bin/env python3
from __future__ import annotations

from collections import deque
import os
import re
import struct
from pathlib import Path


FLOAT_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?(?![A-Za-z0-9_])")
REL_TOL = 1e-2
ABS_TOL = 1e-4
REQUIRED_FILES = ['summary.txt', 'fatigue_post.py', 'cycles.csv', 'fatigue_wind.inp', 'fatigue_wind.bts',
                  'turbsim.log', 'fatigue.fst', 'inflow_fatigue.dat', 'fatigue.out', 'openfast.log']
EXPECTED_ROWS = [[2698.728680, 2.374722]]
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


def bts_ok(path: Path) -> bool:
    header = path.read_bytes()[:42]
    if len(header) != 42:
        return False
    _, nz, ny, _, nt, _, _, dt, uhub, zhub, _ = struct.unpack('<h4i6f', header)
    return nz == 31 and ny == 31 and nt >= 12000 and abs(dt - 0.05) < 1e-4 and abs(uhub - 11.4) < 0.05 and abs(zhub - 90.0) < 0.05


def reversals(series):
    iterator = iter(enumerate(series))
    first_index, first = next(iterator)
    second_index, second = next(iterator)
    while second == first:
        second_index, second = next(iterator)
    yield first_index, first
    previous_slope = second - first
    current_index, current = second_index, second
    for next_index, next_value in iterator:
        slope = next_value - current
        if slope == 0:
            continue
        if previous_slope * slope < 0:
            yield current_index, current
        previous_slope = slope
        current_index, current = next_index, next_value
    yield current_index, current


def extract_cycles(series):
    points = deque()
    for point in reversals(series):
        points.append(point)
        while len(points) >= 3:
            newer = abs(points[-2][1] - points[-1][1])
            older = abs(points[-3][1] - points[-2][1])
            if newer < older:
                break
            if len(points) == 3:
                yield older, 0.5
                points.popleft()
            else:
                yield older, 1.0
                last = points.pop()
                points.pop()
                points.pop()
                points.append(last)
    while len(points) > 1:
        yield abs(points[0][1] - points[1][1]), 0.5
        points.popleft()


def output_dels(path: Path) -> tuple[float, float]:
    lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    header = next(i for i, line in enumerate(lines) if line.split() and line.split()[0] == 'Time')
    names = lines[header].split()
    indices = [names.index(name) for name in ('Time', 'RootMyb1', 'TwrBsMyt')]
    rows = [[float(value) for value in line.split()] for line in lines[header + 2:] if line.split()]
    if not rows or rows[-1][indices[0]] < 599.9:
        raise ValueError('incomplete OpenFAST output')
    tail = [row for row in rows if row[indices[0]] >= 60.0]
    result = []
    for column, exponent in ((indices[1], 10), (indices[2], 4)):
        cycles = [(load_range, count) for load_range, count in extract_cycles([row[column] for row in tail]) if load_range > 0]
        result.append((sum(count * load_range ** exponent for load_range, count in cycles) / 1_000_000) ** (1 / exponent))
    return result[0], result[1] / 1000


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

    ts = (root / 'fatigue_wind.inp').read_text(encoding='utf-8', errors='ignore')
    if keyed_value(ts, 'IECturbc') != 'B' or keyed_value(ts, 'RandSeed1') != '13428' or keyed_value(ts, 'RandSeed2') != 'RanLux':
        return False
    if float(keyed_value(ts, 'URef')) != 11.4 or float(keyed_value(ts, 'RefHt')) != 90 or keyed_value(ts, 'UsableTime').upper() != 'ALL':
        return False
    inflow = (root / 'inflow_fatigue.dat').read_text(encoding='utf-8', errors='ignore')
    if float(keyed_value(inflow, 'WindType')) != 3 or keyed_value(inflow, 'FileName_BTS') != 'fatigue_wind.bts':
        return False
    if not bts_ok(root / 'fatigue_wind.bts'):
        return False
    if 'TurbSim terminated normally' not in (root / 'turbsim.log').read_text(errors='ignore'):
        return False
    if 'OpenFAST terminated normally' not in (root / 'openfast.log').read_text(errors='ignore'):
        return False
    if sum(1 for _ in (root / 'cycles.csv').open(errors='ignore')) < 100:
        return False
    blade, tower = output_dels(root / 'fatigue.out')
    if not close_enough(blade, actual[0][0]) or not close_enough(tower, actual[0][1]):
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
