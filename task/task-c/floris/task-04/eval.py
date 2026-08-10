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


EXPECTED = [2190.397160, 3303.876875, 3507.735753, 24.422081]


def check() -> bool:
    root = desktop_root()
    tree = run_submission(root, "aep.py", ["summary.txt"])
    require_calls(tree, {"FlorisModel": 1, "set": 1, "run": 1, "get_turbine_powers": 1})
    require_source_tokens(root / "aep.py", ["270", "280", "290", "0.5", "0.3", "0.2", "8760"])
    values = parse_floats(root / "summary.txt", 4)
    if not floats_close(values, EXPECTED):
        return False
    expected_aep = (0.5 * values[0] + 0.3 * values[1] + 0.2 * values[2]) * 8760.0 / 1e6
    return abs(values[3] - expected_aep) <= 1e-3


if __name__ == "__main__":
    try:
        result = check()
    except Exception:
        result = False
    raise SystemExit(print_result(result))
