#!/usr/bin/env python3
from __future__ import annotations

import math
import re
from pathlib import Path

REL_TOL = 1e-4
ABS_TOL = 1e-3
FLOAT_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?(?![A-Za-z0-9_])")


def is_result_artifact(path: Path) -> bool:
    name = path.name.lower()
    return (
        any(k in name for k in ("summary", "result", "report", "diagnosis"))
        or path.suffix.lower() in {".txt", ".csv", ".xy", ".result"}
    )


def is_nonempty_file(path: Path) -> bool:
    if not is_result_artifact(path):
        return path.exists() and path.is_file()
    return path.exists() and path.is_file() and path.stat().st_size > 0


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def parse_floats(text: str) -> list[float]:
    values: list[float] = []
    for token in FLOAT_RE.findall(text):
        try:
            values.append(float(token))
        except (TypeError, ValueError):
            continue
    return values


def floats_close(actual: list[float], expected: list[float]) -> bool:
    if len(actual) != len(expected):
        return False
    for a, e in zip(actual, expected):
        if not math.isclose(a, e, rel_tol=REL_TOL, abs_tol=ABS_TOL):
            return False
    return True


def require_files(root: Path, required: list[str]) -> bool:
    for rel in required:
        if not is_nonempty_file(root / rel):
            return False
    return True


EXPECTED_SUMMARY = [15350.619804000000, 9593.316025000000, 39.227384000000]
EXPECTED_MATRIX = [[762.819577, 762.975895, 762.959368, 680.849154, 680.915259, 680.933394, 1753.954459, 1753.954459, 1753.954459], [1536.69931, 1536.170075, 1753.954459, 1753.949695, 1753.949608, 1753.954459, 1753.954459, 1753.954459, 1753.954459], [1535.482209, 1753.949803, 1753.954459, 1536.167952, 1753.949608, 1753.954459, 1753.954459, 1753.954459, 1753.954459], [762.959368, 680.933394, 1753.954459, 762.975895, 680.915259, 1753.954459, 762.819577, 680.849154, 1753.954459], [1753.954459, 1753.954459, 1753.954459, 1536.170075, 1753.949608, 1753.954459, 1536.778279, 1753.949546, 1753.954459], [1753.954459, 1753.954459, 1753.954459, 1753.949659, 1753.949608, 1753.954459, 1535.565108, 1536.167952, 1753.954459], [1753.954459, 1753.954459, 1753.954459, 680.933394, 680.915259, 680.849154, 762.959368, 762.975895, 762.819577], [1753.954459, 1753.954459, 1753.954459, 1753.954459, 1753.949608, 1753.949546, 1753.954459, 1536.170075, 1536.778279], [1753.954459, 1753.954459, 1753.954459, 1753.954459, 1753.949608, 1536.167952, 1753.954459, 1753.949659, 1535.565108], [1753.954459, 680.849154, 762.819577, 1753.954459, 680.915259, 763.072441, 1753.954459, 680.933394, 762.879193], [1753.954459, 1753.949695, 1536.69931, 1753.954459, 1753.949608, 1536.170075, 1753.954459, 1753.954459, 1753.954459], [1753.954459, 1536.167952, 1535.565108, 1753.954459, 1753.949608, 1753.949659, 1753.954459, 1753.954459, 1753.954459]]
EXPECTED_SHAPE = (12, 9)


def check_task(root: Path) -> bool:
    required = ["wind_sector.py", "power_matrix.csv", "summary.txt"]
    if not require_files(root, required):
        return False

    summary = parse_floats(read_text(root / "summary.txt"))
    if not floats_close(summary, EXPECTED_SUMMARY):
        return False

    lines = [ln.strip() for ln in read_text(root / "power_matrix.csv").splitlines() if ln.strip()]
    if len(lines) != EXPECTED_SHAPE[0]:
        return False

    actual_rows = []
    for line in lines:
        parts = [p.strip() for p in line.split(',')]
        if len(parts) != EXPECTED_SHAPE[1]:
            return False
        try:
            actual_rows.append([float(x) for x in parts])
        except ValueError:
            return False

    for arow, erow in zip(actual_rows, EXPECTED_MATRIX):
        for a, e in zip(arow, erow):
            if not math.isclose(a, e, rel_tol=REL_TOL, abs_tol=ABS_TOL):
                return False
    return True

def evaluate() -> int:
    root = Path("/home/user/Desktop")
    try:
        ok = check_task(root)
    except Exception:
        ok = False
    return 1 if ok else 0


def main() -> int:
    result = evaluate()
    print("True" if result == 1 else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
