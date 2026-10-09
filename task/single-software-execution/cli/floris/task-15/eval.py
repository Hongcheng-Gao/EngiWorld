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


EXPECTED = [1753.954459, 436.442701]


def check() -> bool:
    root = desktop_root()
    tree = run_submission(root, "fixed.py", ["fixed_summary.txt"])
    require_calls(tree, {"FlorisModel": 1, "set": 1, "run": 1, "get_turbine_powers": 1})
    require_source_tokens(root / "fixed.py", ["two_turbine.yaml", "fixed_summary.txt"])
    diagnosis = (root / "diagnosis.txt").read_text(encoding="utf-8").strip().lower()
    if len(diagnosis) < 100:
        return False
    groups = [
        ("scalar", "list", "wind_directions"),
        ("get_turbine_powers", "run", "before"),
        ("output", "fixed_summary.txt"),
    ]
    if any(not all(token in diagnosis for token in group) for group in groups):
        return False
    return floats_close(parse_floats(root / "fixed_summary.txt", 2), EXPECTED)


if __name__ == "__main__":
    try:
        result = check()
    except Exception:
        result = False
    raise SystemExit(print_result(result))
