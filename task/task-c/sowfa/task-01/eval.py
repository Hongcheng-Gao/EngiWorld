#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import re
from pathlib import Path

ABS_TOL = 1e-4
NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?$")
EXPECTED_ROWS = [[1.6]]


def is_nonempty_file(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def parse_number(token: str) -> float:
    s = token.strip()
    if not NUMBER_RE.fullmatch(s):
        raise ValueError(f"not a plain float token: {token!r}")
    return float(s)


def parse_csv_matrix(path: Path) -> list[list[float]]:
    lines = [
        ln.strip()
        for ln in read_text(path).splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    ]
    rows: list[list[float]] = []
    for ln in lines:
        parts = [p.strip() for p in ln.split(",")]
        rows.append([parse_number(p) for p in parts])
    return rows


def matrices_close(actual: list[list[float]], expected: list[list[float]]) -> bool:
    if len(actual) != len(expected):
        return False
    for a_row, e_row in zip(actual, expected):
        if len(a_row) != len(e_row):
            return False
        for a, e in zip(a_row, e_row):
            if not math.isclose(a, e, rel_tol=0.0, abs_tol=ABS_TOL):
                return False
    return True


def write_result(path: Path, value: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"result": int(1 if value else 0)}, ensure_ascii=False) + "\n", encoding="utf-8")


def check_task(root: Path) -> bool:
    summary_path = root / "summary.txt"
    if not is_nonempty_file(summary_path):
        return False
    actual_rows = parse_csv_matrix(summary_path)
    return matrices_close(actual_rows, EXPECTED_ROWS)


def evaluate() -> int:
    root = Path("/home/user/Desktop")
    try:
        ok = check_task(root)
    except Exception:
        ok = False
    write_result(root / "eval.json", 1 if ok else 0)
    return 1 if ok else 0


def main() -> int:
    result = evaluate()
    print("True" if result == 1 else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
