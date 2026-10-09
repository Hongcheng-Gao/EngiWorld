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


EXPECTED = [331.121520, 436.442701, 832.715423]


def check() -> bool:
    root = desktop_root()
    tree = run_submission(root, "ti_scan.py", ["summary.txt"])
    require_calls(tree, {"FlorisModel": 1, "set": 1, "run": 1, "get_turbine_powers": 1})
    require_source_tokens(root / "ti_scan.py", ["0.03", "0.06", "0.12", "630"])
    values = parse_floats(root / "summary.txt", 3)
    return floats_close(values, EXPECTED) and values[0] < values[1] < values[2]


if __name__ == "__main__":
    try:
        result = check()
    except Exception:
        result = False
    raise SystemExit(print_result(result))
