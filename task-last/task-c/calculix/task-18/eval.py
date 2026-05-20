#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ABS_TOL = 1e-6
REL_TOL = 1e-4


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


def parse_csv_values(path: Path) -> list[str]:
    content = read_text(path).strip()
    if not content:
        return []
    return [p.strip() for p in content.split(",")]


def close_enough(actual: float, target: float) -> bool:
    limit = max(ABS_TOL, REL_TOL * max(1.0, abs(target)))
    return abs(actual - target) <= limit


def check_task(root: Path) -> bool:
    required = ['pretension.inp', 'summary.txt']
    for rel in required:
        if not is_nonempty_file(root / rel):
            return False
    actual_parts = parse_csv_values(root / "summary.txt")
    expected_vals = [-21291.7, 208.055]

    if len(actual_parts) != len(expected_vals):
        return False

    try:
        actual_vals = [float(v) for v in actual_parts]
    except (TypeError, ValueError):
        return False

    for a, g in zip(actual_vals, expected_vals):
        if not close_enough(a, g):
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
