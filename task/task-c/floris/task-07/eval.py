#!/usr/bin/env python3
from eval_utils import (
    desktop_root,
    floats_close,
    parse_floats,
    print_result,
    read_numeric_csv,
    require_calls,
    require_source_tokens,
    run_submission,
)


EXPECTED = [0.763779, 3506.0]


def check() -> bool:
    root = desktop_root()
    tree = run_submission(root, "flow_plane.py", ["flow_plane.csv", "summary.txt"])
    require_calls(tree, {"FlorisModel": 1, "sample_flow_at_points": 1})
    require_source_tokens(root / "flow_plane.py", ["756", "5000", "90", "0.95", "two_turbine.yaml"])
    values = parse_floats(root / "summary.txt", 2)
    rows = read_numeric_csv(root / "flow_plane.csv", 425, 3, header=["x", "y", "u_eff"])
    for index, row in enumerate(rows):
        if abs(row[0] - (756.0 + 10.0 * index)) > 1e-9 or abs(row[1]) > 1e-9:
            return False
        if not 0.0 < row[2] < 9.0:
            return False
    recovered = next((row[0] for row in rows if row[2] >= 7.6), None)
    if recovered is None:
        return False
    return (
        floats_close(values, EXPECTED)
        and abs(values[0] - min(row[2] for row in rows)) <= 1e-6
        and abs(values[1] - (recovered - 630.0)) <= 1e-6
    )


if __name__ == "__main__":
    try:
        result = check()
    except Exception:
        result = False
    raise SystemExit(print_result(result))
