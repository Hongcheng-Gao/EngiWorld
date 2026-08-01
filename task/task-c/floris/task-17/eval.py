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


def parse_report(path: Path):
    lines = [ln.strip() for ln in read_text(path).splitlines() if ln.strip()]
    if len(lines) != 4:
        return None
    rows = []
    for line in lines:
        parts = [p.strip() for p in line.split(',')]
        rows.append(parts)
    return rows


def check_task(root: Path) -> bool:
    required = ["run_pipeline.py", "compare.py", "comparison_report.txt"]
    if not require_files(root, required):
        return False

    rows = parse_report(root / "comparison_report.txt")
    if rows is None:
        return False

    try:
        base_label = rows[0][0]
        base_vals = [float(rows[0][1]), float(rows[0][2])]
        yaw_label = rows[1][0]
        yaw_vals = [float(rows[1][1]), float(rows[1][2])]
        gt_label = rows[2][0]
        gt_val = float(rows[2][1])
        gd_label = rows[3][0]
        gd_val = float(rows[3][1])
    except (ValueError, IndexError):
        return False

    if base_label != "baseline":
        return False
    if yaw_label != "yaw":
        return False
    if gt_label != "Gain_Total_Percent":
        return False
    if gd_label != "Gain_Downstream_Percent":
        return False
    if min(base_vals + yaw_vals) <= 0.0:
        return False
    expected_total_gain = (yaw_vals[0] - base_vals[0]) / base_vals[0] * 100.0
    expected_down_gain = (yaw_vals[1] - base_vals[1]) / base_vals[1] * 100.0
    if not math.isclose(gt_val, expected_total_gain, rel_tol=1e-4, abs_tol=1e-3):
        return False
    if not math.isclose(gd_val, expected_down_gain, rel_tol=1e-4, abs_tol=1e-3):
        return False
    if gt_val <= 0.0 or gd_val <= 10.0:
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
