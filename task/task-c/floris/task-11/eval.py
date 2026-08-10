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


EXPECTED = [3507.908918, 2190.397160, 0.0]


def check() -> bool:
    root = desktop_root()
    tree = run_submission(root, "parallel.py", ["summary.txt"], timeout=300)
    require_calls(tree, {"FlorisModel": 1, "ParFlorisModel": 1, "set": 1, "run": 1})
    require_source_tokens(root / "parallel.py", ["max_workers", "36", "360", "10.0"])
    values = parse_floats(root / "summary.txt", 3)
    return floats_close(values, EXPECTED, abs_tol=1e-2) and values[2] < 0.1


if __name__ == "__main__":
    try:
        result = check()
    except Exception:
        result = False
    raise SystemExit(print_result(result))
