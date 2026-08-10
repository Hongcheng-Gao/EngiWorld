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


EXPECTED = [9593.332396, 1065.874397, 1065.922349]
LAYOUT_X = [0.0, 882.0, 1764.0, 0.0, 882.0, 1764.0, 0.0, 882.0, 1764.0]
LAYOUT_Y = [0.0, 0.0, 0.0, 882.0, 882.0, 882.0, 1764.0, 1764.0, 1764.0]


def check() -> bool:
    root = desktop_root()
    config = yaml.safe_load((root / "farm.yaml").read_text(encoding="utf-8"))
    farm = config["farm"]
    if farm["layout_x"] != LAYOUT_X or farm["layout_y"] != LAYOUT_Y:
        return False
    if farm["turbine_type"] != ["nrel_5MW"] * 9:
        return False
    if config["wake"]["model_strings"]["velocity_model"] != "gauss":
        return False
    tree = run_submission(root, "full_farm.py", ["summary.txt"])
    require_calls(tree, {"FlorisModel": 1, "set": 1, "run": 1, "get_turbine_powers": 1})
    require_source_tokens(root / "full_farm.py", ["farm.yaml", "270", "8", "0.06"])
    values = parse_floats(root / "summary.txt", 3)
    return floats_close(values, EXPECTED) and abs(values[0] - 9.0 * (values[1] + values[2]) / 2.0) < 1e4


if __name__ == "__main__":
    try:
        result = check()
    except Exception:
        result = False
    raise SystemExit(print_result(result))
