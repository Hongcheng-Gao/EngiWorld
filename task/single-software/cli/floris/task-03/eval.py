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


EXPECTED = [767.287220, 436.442701, 381.082811]


def check() -> bool:
    root = desktop_root()
    tree = run_submission(root, "compare.py", ["summary.txt"])
    require_calls(tree, {"FlorisModel": 1, "set": 1, "run": 1, "get_turbine_powers": 1})
    require_source_tokens(root / "compare.py", ["jensen", "gauss", "cc", "velocity_model"])
    return floats_close(parse_floats(root / "summary.txt", 3), EXPECTED)


if __name__ == "__main__":
    try:
        result = check()
    except Exception:
        result = False
    raise SystemExit(print_result(result))
