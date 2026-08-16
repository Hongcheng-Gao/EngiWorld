#!/usr/bin/env python3
from __future__ import annotations

import math
import os
import re
import struct
from pathlib import Path


FLOAT_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?(?![A-Za-z0-9_])")
REL_TOL = 1e-2
ABS_TOL = 1e-4
REQUIRED_FILES = ['summary.txt', 'postprocess.py', 'wind_8ms.inp', 'wind_8ms.bts', 'turbsim.log',
                  'case_turb.fst', 'inflow_turb_base.dat', 'case_turb.out', 'openfast.log']
EXPECTED_ROWS = [[1970.977618, 475.357979]]
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
    return nz == 31 and ny == 31 and nt >= 1200 and abs(dt - 0.05) < 1e-4 and abs(uhub - 8.0) < 0.05 and abs(zhub - 90.0) < 0.05


def output_stats(path: Path) -> tuple[float, float]:
    lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    header = next(i for i, line in enumerate(lines) if line.split() and line.split()[0] == 'Time')
    names = lines[header].split()
    time_i, power_i = names.index('Time'), names.index('GenPwr')
    rows = [[float(value) for value in line.split()] for line in lines[header + 2:] if line.split()]
    if not rows or rows[-1][time_i] < 59.9:
        raise ValueError('incomplete OpenFAST output')
    power = [row[power_i] for row in rows]
    mean = sum(power) / len(power)
    return mean, math.sqrt(sum((value - mean) ** 2 for value in power) / len(power))


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

    ts = (root / 'wind_8ms.inp').read_text(encoding='utf-8', errors='ignore')
    if keyed_value(ts, 'IECturbc') != 'B' or float(keyed_value(ts, 'RefHt')) != 90 or float(keyed_value(ts, 'URef')) != 8:
        return False
    inflow = (root / 'inflow_turb_base.dat').read_text(encoding='utf-8', errors='ignore')
    if float(keyed_value(inflow, 'WindType')) != 3 or keyed_value(inflow, 'FileName_BTS') != 'wind_8ms.bts':
        return False
    if not bts_ok(root / 'wind_8ms.bts'):
        return False
    if 'OpenFAST terminated normally' not in (root / 'openfast.log').read_text(errors='ignore'):
        return False
    if 'TurbSim terminated normally' not in (root / 'turbsim.log').read_text(errors='ignore'):
        return False
    mean, std = output_stats(root / 'case_turb.out')
    if not close_enough(mean, actual[0][0]) or not close_enough(std, actual[0][1]):
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
