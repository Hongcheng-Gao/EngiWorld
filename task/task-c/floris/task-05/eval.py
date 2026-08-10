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


EXPECTED = [2190.397160, 2370.416706, 26.25, 0.0]


def check() -> bool:
    root = desktop_root()
    tree = run_submission(root, "yaw_opt.py", ["summary.txt"], timeout=300)
    require_calls(
        tree,
        {"FlorisModel": 1, "YawOptimizationSR": 1, "optimize": 1, "set": 2, "run": 2},
    )
    require_source_tokens(
        root / "yaw_opt.py",
        ["minimum_yaw_angle", "maximum_yaw_angle", "Ny_passes", "two_turbine.yaml"],
    )
    values = parse_floats(root / "summary.txt", 4)
    return floats_close(values, EXPECTED) and values[1] > values[0]


if __name__ == "__main__":
    try:
        result = check()
    except Exception:
        result = False
    raise SystemExit(print_result(result))
