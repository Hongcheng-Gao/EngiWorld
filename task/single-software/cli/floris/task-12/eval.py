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


EXPECTED = [26.25, 15.0, 2527.279712, 2562.098072]


def check() -> bool:
    root = desktop_root()
    tree = run_submission(root, "uncertain.py", ["summary.txt"], timeout=300)
    require_calls(tree, {"FlorisModel": 1, "UncertainFlorisModel": 2, "YawOptimizationSR": 1, "optimize": 1})
    require_source_tokens(
        root / "uncertain.py",
        ["wd_std", "5.0", "minimum_yaw_angle", "maximum_yaw_angle", "Ny_passes"],
    )
    values = parse_floats(root / "summary.txt", 4)
    return floats_close(values, EXPECTED) and values[3] > values[2]


if __name__ == "__main__":
    try:
        result = check()
    except Exception:
        result = False
    raise SystemExit(print_result(result))
