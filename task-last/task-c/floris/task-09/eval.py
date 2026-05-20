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


EXPECTED_SUMMARY = [46.913442000000, 61.047511000000, 378.653453000000]


def check_task(root: Path) -> bool:
    required = ['layout_opt.py', 'summary.txt']
    if not require_files(root, required):
        return False

    actual = parse_floats(read_text(root / "summary.txt"))
    return floats_close(actual, EXPECTED_SUMMARY)

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
