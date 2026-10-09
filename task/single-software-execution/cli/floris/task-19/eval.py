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


EXPECTED = [175.867082, 0.999471, 1753.954459, 0.787128, 5000.0, 0.542912, 5000.0, 0.106515]


def check() -> bool:
    root = desktop_root()
    tree = run_submission(root, "curve.py", ["summary.txt"])
    require_calls(tree, {"FlorisModel": 1, "set": 1, "run_no_wake": 1, "get_turbine_powers": 1})
    require_source_tokens(root / "curve.py", ["4.0", "22.0", "2.0", "nrel_5MW"])
    values = parse_floats(root / "summary.txt", 8)
    return floats_close(values, EXPECTED)


if __name__ == "__main__":
    try:
        result = check()
    except Exception:
        result = False
    raise SystemExit(print_result(result))
