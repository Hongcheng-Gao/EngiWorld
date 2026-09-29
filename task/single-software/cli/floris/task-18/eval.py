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


EXPECTED = [308.767537, 436.442701, 680.849154, 946.323098]


def check() -> bool:
    root = desktop_root()
    tree = run_submission(root, "spacing_scan.py", ["summary.txt"])
    require_calls(tree, {"FlorisModel": 1, "set": 1, "run": 1, "get_turbine_powers": 1})
    require_source_tokens(root / "spacing_scan.py", ["3.0", "5.0", "7.0", "10.0", "126.0"])
    values = parse_floats(root / "summary.txt", 4)
    return floats_close(values, EXPECTED) and values == sorted(values)


if __name__ == "__main__":
    try:
        result = check()
    except Exception:
        result = False
    raise SystemExit(print_result(result))
