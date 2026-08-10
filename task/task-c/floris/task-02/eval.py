#!/usr/bin/env python3
from eval_utils import (
    desktop_root,
    floats_close,
    parse_floats,
    print_result,
    require_calls,
    require_source_tokens,
    run_submission,
)


EXPECTED = [436.442701, 778.043382, 78.269308]


def check() -> bool:
    root = desktop_root()
    tree = run_submission(root, "yaw.py", ["summary.txt"])
    require_calls(tree, {"FlorisModel": 1, "set": 2, "run": 2, "get_turbine_powers": 2})
    require_source_tokens(root / "yaw.py", ["two_turbine.yaml", "yaw_angles", "20"])
    values = parse_floats(root / "summary.txt", 3)
    if not floats_close(values, EXPECTED):
        return False
    return abs(values[2] - (values[1] - values[0]) / values[0] * 100.0) <= 1e-3


if __name__ == "__main__":
    try:
        result = check()
    except Exception:
        result = False
    raise SystemExit(print_result(result))
