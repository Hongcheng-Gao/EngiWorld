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


EXPECTED = [2697.065314, 2489.992999, -207.072315]


def check() -> bool:
    root = desktop_root()
    tree = run_submission(root, "derating.py", ["summary.txt"])
    require_calls(
        tree,
        {"FlorisModel": 1, "set_operation_model": 1, "set": 2, "run": 2, "get_turbine_powers": 2},
    )
    require_source_tokens(root / "derating.py", ["simple-derating", "power_setpoints", "0.8", "derating_base.yaml"])
    if "yaw_angles" in (root / "derating.py").read_text(encoding="utf-8"):
        return False
    values = parse_floats(root / "summary.txt", 3)
    return floats_close(values, EXPECTED) and abs(values[2] - (values[1] - values[0])) <= 1e-3


if __name__ == "__main__":
    try:
        result = check()
    except Exception:
        result = False
    raise SystemExit(print_result(result))
