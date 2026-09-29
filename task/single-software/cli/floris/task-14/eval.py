#!/usr/bin/env python3
import yaml

from eval_utils import (
    desktop_root,
    floats_close,
    parse_floats,
    print_result,
    require_calls,
    require_source_tokens,
    run_submission,
)


EXPECTED = [49.898152, 0.9, 1493.583556, 0.7, 2996.944551, 0.2]


def check() -> bool:
    root = desktop_root()
    turbine = yaml.safe_load((root / "custom_turbine.yaml").read_text(encoding="utf-8"))
    table = turbine["power_thrust_table"]
    required = ["ref_air_density", "ref_tilt", "cosine_loss_exponent_yaw", "cosine_loss_exponent_tilt"]
    if turbine.get("turbine_type") != "custom_3mw" or any(key not in table for key in required):
        return False
    tree = run_submission(root, "external.py", ["summary.txt"])
    require_calls(tree, {"FlorisModel": 1, "set": 1, "run_no_wake": 1, "get_turbine_powers": 1})
    require_source_tokens(root / "external.py", ["custom_turbine.yaml", "3.0", "5.0", "7.0", "9.0", "11.0", "13.0", "15.0"])
    source = (root / "external.py").read_text(encoding="utf-8")
    if ".pop(" in source or ".setdefault(" in source:
        return False
    return floats_close(parse_floats(root / "summary.txt", 6), EXPECTED)


if __name__ == "__main__":
    try:
        result = check()
    except Exception:
        result = False
    raise SystemExit(print_result(result))
