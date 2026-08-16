#!/usr/bin/env python3
from __future__ import annotations

import os
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


FLOAT_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?(?![A-Za-z0-9_])")
REL_TOL = 1e-4
ABS_TOL = 1e-3
REQUIRED_FILES = ['fixed_summary.txt', 'diagnosis.txt', 'postprocess.py',
                  'fixed.fst', 'fixed_elasto.dat', 'fixed_inflow.dat', 'fixed.out',
                  'diagnostic_1.log', 'diagnostic_2.log']
EXPECTED_ROWS = [[4866.598858, 5139.093750]]
SUMMARY_FILE = 'fixed_summary.txt'


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


def output_stats(path: Path) -> tuple[float, float]:
    lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    header = next(i for i, line in enumerate(lines) if line.split() and line.split()[0] == 'Time')
    names = lines[header].split()
    time_i, power_i = names.index('Time'), names.index('GenPwr')
    rows = []
    for line in lines[header + 2:]:
        if not line.split():
            continue
        values = [float(value) for value in line.split()]
        if len(values) != len(names) or not all(math.isfinite(value) for value in values):
            raise ValueError('malformed OpenFAST output row')
        rows.append(values)
    times = [row[time_i] for row in rows]
    if (len(rows) < 1000 or times[0] > 0.01 or times[-1] < 59.9 or
            any(second <= first for first, second in zip(times, times[1:]))):
        raise ValueError('incomplete OpenFAST output')
    power = [row[power_i] for row in rows]
    return sum(power) / len(power), max(power)


def openfast_fields(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    pattern = re.compile(r'^\s*(.*?)\s+([A-Za-z][A-Za-z0-9_]*(?:\(\d+\))?)\s+-')
    for raw_line in path.read_text(encoding='utf-8', errors='ignore').splitlines():
        match = pattern.match(raw_line)
        if not match:
            continue
        value = re.sub(r'\s+', ' ', match.group(1)).strip()
        name = match.group(2)
        if value and name not in fields:
            fields[name] = value
    return fields


def unquoted(value: str) -> str:
    value = str(value or '').strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1]
    return value


def only_fields_changed(broken: Path, fixed: Path, changes: dict[str, tuple[str, str]]) -> bool:
    before = openfast_fields(broken)
    after = openfast_fields(fixed)
    if not before or before.keys() != after.keys():
        return False
    for field, (old, new) in changes.items():
        if unquoted(before.get(field, '')) != old or unquoted(after.get(field, '')) != new:
            return False
    return all(before[field] == after[field] for field in before if field not in changes)


def diagnostics_valid(root: Path) -> bool:
    first = (root / 'diagnostic_1.log').read_bytes().decode('utf-8', errors='ignore').replace('\x00', '')
    second = (root / 'diagnostic_2.log').read_bytes().decode('utf-8', errors='ignore').replace('\x00', '')
    common = ('OpenFAST-v', 'FAST_InitializeAll:', 'FATAL ERROR', 'Aborting OpenFAST')
    if not all(token in first and token in second for token in common):
        return False
    if not ('ReadBladeFile' in first and 'input file' in first and 'not found' in first):
        return False
    if 'Running InflowWind' in first or 'Invalid WindType' in first:
        return False
    if not ('Running InflowWind' in second and 'Invalid WindType' in second and 'supported' in second):
        return False
    return True


def generated_summary(root: Path, expected_stats: tuple[float, float]) -> tuple[float, float] | None:
    invocations = [[], ['fixed.out'], ['fixed.out', 'fixed_summary.txt']]

    def transformed_output(path: Path) -> str:
        lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
        header = next(i for i, line in enumerate(lines) if line.split() and line.split()[0] == 'Time')
        power_index = lines[header].split().index('GenPwr')
        for index in range(header + 2, len(lines)):
            tokens = lines[index].split()
            if not tokens:
                continue
            tokens[power_index] = format(float(tokens[power_index]) * 0.37 + 123.45, '.12g')
            lines[index] = '\t'.join(tokens)
        return '\n'.join(lines) + '\n'

    with tempfile.TemporaryDirectory(prefix='engiworld_openfast_post_') as temp_root:
        base = Path(temp_root)
        transformed = base / 'transformed.out'
        transformed.write_text(transformed_output(root / 'fixed.out'), encoding='utf-8')
        probes = [
            (root / 'fixed.out', expected_stats),
            (transformed, (expected_stats[0] * 0.37 + 123.45,
                           expected_stats[1] * 0.37 + 123.45)),
        ]
        first_result = None
        for probe_index, (source, expected) in enumerate(probes):
            probe_passed = False
            for invocation_index, arguments in enumerate(invocations):
                work = base / ('probe_%d_%d' % (probe_index, invocation_index))
                work.mkdir()
                shutil.copy2(root / 'postprocess.py', work / 'postprocess.py')
                shutil.copy2(source, work / 'fixed.out')
                try:
                    completed = subprocess.run(
                        [sys.executable, 'postprocess.py', *arguments],
                        cwd=str(work),
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=30,
                        check=False,
                    )
                except (OSError, subprocess.TimeoutExpired):
                    continue
                summary = work / SUMMARY_FILE
                if completed.returncode != 0 or not file_ok(summary):
                    continue
                rows = parse_numeric_rows(summary)
                if (len(rows) == 1 and len(rows[0]) == 2 and
                        all(close_enough(actual, wanted) for actual, wanted in zip(rows[0], expected))):
                    probe_passed = True
                    if probe_index == 0:
                        first_result = (rows[0][0], rows[0][1])
                    break
            if not probe_passed:
                return None
        return first_result


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

    if not only_fields_changed(root / 'broken_elasto.dat', root / 'fixed_elasto.dat',
                               {'NumBl': ('4', '3')}):
        return False
    if not only_fields_changed(root / 'broken_inflow.dat', root / 'fixed_inflow.dat',
                               {'WindType': ('99', '3')}):
        return False
    if not only_fields_changed(root / 'broken.fst', root / 'fixed.fst',
                               {'EDFile': ('broken_elasto.dat', 'fixed_elasto.dat'),
                                'InflowFile': ('broken_inflow.dat', 'fixed_inflow.dat')}):
        return False

    diagnosis = (root / 'diagnosis.txt').read_text(encoding='utf-8', errors='ignore')
    words = re.findall(r"[A-Za-z0-9_]+", diagnosis)
    diagnosis_lower = diagnosis.lower()
    if (len(words) < 100 or not all(token in diagnosis for token in ('NumBl', 'WindType')) or
            not all(re.search(pattern, diagnosis_lower) for pattern in
                    (r'\b4\b', r'\b3\b', r'\b99\b', r'not\s+found|nonexistent|unreadable',
                     r'invalid', r'correct'))):
        return False
    fixed_fields = openfast_fields(root / 'fixed.fst')
    if (unquoted(fixed_fields.get('EDFile', '')) != 'fixed_elasto.dat' or
            unquoted(fixed_fields.get('InflowFile', '')) != 'fixed_inflow.dat' or
            unquoted(fixed_fields.get('TMax', '')) not in {'60', '60.0'}):
        return False
    if not diagnostics_valid(root):
        return False
    logs = [path for path in root.glob('*.log') if path.is_file()]
    normal_logs = [path for path in logs if
                   'OpenFAST terminated normally' in path.read_text(errors='ignore') and
                   'FATAL ERROR' not in path.read_text(errors='ignore')]
    if not normal_logs:
        return False
    mean, maximum = output_stats(root / 'fixed.out')
    if not close_enough(mean, actual[0][0]) or not close_enough(maximum, actual[0][1]):
        return False
    regenerated = generated_summary(root, (mean, maximum))
    if regenerated is None:
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
