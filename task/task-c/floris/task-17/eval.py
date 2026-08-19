#!/usr/bin/env python3
import csv
import hashlib
import math

from eval_utils import (
    desktop_root,
    print_result,
    read_numeric_csv,
    run_submission,
)


JOB_HASHES = {
    "job_baseline.py": "49a962bcda502b901c1a8d9fc5e018bd05e9a3218438e20f0cec9f3655c8a736",
    "job_yaw.py": "b0f1c852d0ce7b514a649582c23b6a9c2bddd3af8e13970f768aa1c57c1842b5",
}
EXPECTED = [2190.397160, 436.442701, 2304.300414, 660.711994, 5.200119, 51.385736]


def check() -> bool:
    root = desktop_root()
    for name, expected_hash in JOB_HASHES.items():
        actual_hash = hashlib.sha256((root / name).read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            return False

    run_submission(
        root,
        "run_pipeline.py",
        ["baseline.csv", "yaw.csv"],
        timeout=300,
    )
    run_submission(root, "compare.py", ["comparison_report.txt"])

    with (root / "comparison_report.txt").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    if len(rows) != 4 or [row[0] for row in rows] != [
        "baseline",
        "yaw",
        "Gain_Total_Percent",
        "Gain_Downstream_Percent",
    ]:
        return False
    values = [
        float(rows[0][1]),
        float(rows[0][2]),
        float(rows[1][1]),
        float(rows[1][2]),
        float(rows[2][1]),
        float(rows[3][1]),
    ]
    baseline_values = read_numeric_csv(root / "baseline.csv", 1, 2)[0]
    yaw_values = read_numeric_csv(root / "yaw.csv", 1, 2)[0]
    if not all(
        math.isclose(actual, source, rel_tol=1e-6, abs_tol=1e-6)
        for actual, source in zip(values[:4], baseline_values + yaw_values)
    ):
        return False
    if not all(math.isclose(a, e, rel_tol=1e-4, abs_tol=1e-3) for a, e in zip(values, EXPECTED)):
        return False
    total_gain = (values[2] - values[0]) / values[0] * 100.0
    downstream_gain = (values[3] - values[1]) / values[1] * 100.0
    return abs(values[4] - total_gain) <= 1e-3 and abs(values[5] - downstream_gain) <= 1e-3


if __name__ == "__main__":
    try:
        result = check()
    except Exception:
        result = False
    raise SystemExit(print_result(result))
