#!/usr/bin/env python3
import math
from pathlib import Path

import floris
from floris import FlorisModel, WindRose
import numpy as np
import yaml

from eval_utils import (
    desktop_root,
    parse_floats,
    print_result,
    read_numeric_csv,
    require_calls,
    require_source_tokens,
    run_submission,
)


def configuration():
    path = Path(floris.__file__).resolve().with_name("default_inputs.yaml")
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    config["logging"]["console"]["level"] = "ERROR"
    config["farm"]["layout_x"] = [0.0, 500.0, 0.0, 500.0]
    config["farm"]["layout_y"] = [0.0, 0.0, 500.0, 500.0]
    config["farm"]["turbine_type"] = ["nrel_5MW"] * 4
    return config


def compute_aep_gwh(x, y):
    rose = WindRose(
        np.array([270.0, 280.0, 290.0]),
        np.array([8.0]),
        0.06,
        np.array([[0.5], [0.3], [0.2]]),
    )
    model = FlorisModel(configuration())
    model.set(layout_x=x, layout_y=y, wind_data=rose)
    model.run()
    return float(model.get_farm_AEP() / 1e9)


def check() -> bool:
    root = desktop_root()
    tree = run_submission(
        root,
        "layout_opt.py",
        ["optimized_layout.csv", "summary.txt"],
        timeout=420,
    )
    require_calls(tree, {"FlorisModel": 1, "WindRose": 1, "optimize": 1})
    require_source_tokens(root / "layout_opt.py", ["LayoutOptimization", "378", "0.5", "0.3", "0.2"])
    summary = parse_floats(root / "summary.txt", 3)
    layout = read_numeric_csv(root / "optimized_layout.csv", 4, 2, header=["x", "y"])
    x = np.array([row[0] for row in layout])
    y = np.array([row[1] for row in layout])
    if np.any(x < -100.000001) or np.any(x > 600.000001):
        return False
    if np.any(y < -100.000001) or np.any(y > 600.000001):
        return False
    spacing = min(
        math.hypot(float(x[i] - x[j]), float(y[i] - y[j]))
        for i in range(4)
        for j in range(i + 1, 4)
    )
    if spacing < 377.999:
        return False
    initial = compute_aep_gwh([0.0, 500.0, 0.0, 500.0], [0.0, 0.0, 500.0, 500.0])
    optimized = compute_aep_gwh(x, y)
    return (
        optimized >= initial * 1.02
        and math.isclose(summary[0], initial, rel_tol=5e-4, abs_tol=1e-3)
        and math.isclose(summary[1], optimized, rel_tol=5e-4, abs_tol=1e-3)
        and math.isclose(summary[2], spacing, rel_tol=1e-5, abs_tol=1e-3)
    )


if __name__ == "__main__":
    try:
        result = check()
    except Exception:
        result = False
    raise SystemExit(print_result(result))
