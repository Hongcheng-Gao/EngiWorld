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


EXPECTED = [3507.908918, 2190.397160, 37.558323]


def check() -> bool:
    root = desktop_root()
    tree = run_submission(root, "loss.py", ["summary.txt"])
    require_calls(tree, {"FlorisModel": 1, "run": 1, "run_no_wake": 1, "get_turbine_powers": 2})
    require_source_tokens(root / "loss.py", ["two_turbine.yaml"])
    values = parse_floats(root / "summary.txt", 3)
    expected_loss = (values[0] - values[1]) / values[0] * 100.0
    return floats_close(values, EXPECTED) and abs(values[2] - expected_loss) <= 1e-3


if __name__ == "__main__":
    try:
        result = check()
    except Exception:
        result = False
    raise SystemExit(print_result(result))
