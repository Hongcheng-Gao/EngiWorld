#!/usr/bin/env python3
import math
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


EXPECTED = [1753.954459, 5313.911068, 1753.954459, 5314.055367, 14135.875354]


def check() -> bool:
    root = desktop_root()
    config = yaml.safe_load((root / "heterogeneous.yaml").read_text(encoding="utf-8"))
    farm = config["farm"]
    if farm["turbine_type"] != ["nrel_5MW", "iea_15MW", "nrel_5MW", "iea_15MW"]:
        return False
    if float(config["flow_field"]["reference_wind_height"]) != 90.0:
        return False
    tree = run_submission(root, "hetero.py", ["summary.txt"])
    require_calls(tree, {"FlorisModel": 1, "set": 1, "run": 1, "get_turbine_powers": 1})
    require_source_tokens(root / "hetero.py", ["heterogeneous.yaml"])
    values = parse_floats(root / "summary.txt", 5)
    return (
        floats_close(values, EXPECTED)
        and values[1] > values[0]
        and values[3] > values[2]
        and math.isclose(values[4], sum(values[:4]), abs_tol=2e-3)
    )


if __name__ == "__main__":
    try:
        result = check()
    except Exception:
        result = False
    raise SystemExit(print_result(result))
