#!/usr/bin/env python3
import math
from pathlib import Path

import floris
from floris import FlorisModel
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


def reference_results():
    path = Path(floris.__file__).resolve().with_name("default_inputs.yaml")
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    config["logging"]["console"]["level"] = "ERROR"
    coordinates = [0.0, 882.0, 1764.0]
    config["farm"]["layout_x"] = [x for y in coordinates for x in coordinates]
    config["farm"]["layout_y"] = [y for y in coordinates for x in coordinates]
    config["farm"]["turbine_type"] = ["nrel_5MW"] * 9
    model = FlorisModel(config)
    directions = np.arange(0.0, 360.0, 30.0)
    model.set(
        wind_directions=directions,
        wind_speeds=np.full(12, 8.0),
        turbulence_intensities=np.full(12, 0.06),
    )
    model.run()
    matrix_kw = model.get_turbine_powers() / 1000.0
    totals = matrix_kw.sum(axis=1)
    model.set(wind_directions=[270.0], wind_speeds=[8.0], turbulence_intensities=[0.06])
    model.run_no_wake()
    no_wake_kw = float(model.get_turbine_powers().sum() / 1000.0)
    summary = [
        float(totals.max()),
        float(totals.min()),
        float((no_wake_kw - totals.min()) / no_wake_kw * 100.0),
    ]
    return matrix_kw, summary


def check() -> bool:
    root = desktop_root()
    tree = run_submission(root, "wind_sector.py", ["power_matrix.csv", "summary.txt"])
    require_calls(tree, {"FlorisModel": 1, "set": 2, "run": 1, "run_no_wake": 1, "get_turbine_powers": 2})
    require_source_tokens(root / "wind_sector.py", ["30.0", "360.0", "126.0", "7.0", "nrel_5MW"])
    actual_matrix = np.asarray(read_numeric_csv(root / "power_matrix.csv", 12, 9), dtype=float)
    actual_summary = parse_floats(root / "summary.txt", 3)
    expected_matrix, expected_summary = reference_results()
    if not np.allclose(actual_matrix, expected_matrix, rtol=5e-3, atol=1e-2):
        return False
    if not all(
        math.isclose(a, e, rel_tol=5e-3, abs_tol=1e-2)
        for a, e in zip(actual_summary, expected_summary)
    ):
        return False
    totals = actual_matrix.sum(axis=1)
    return (
        math.isclose(actual_summary[0], float(totals.max()), rel_tol=1e-6, abs_tol=1e-3)
        and math.isclose(actual_summary[1], float(totals.min()), rel_tol=1e-6, abs_tol=1e-3)
        and 0.0 < actual_summary[2] < 100.0
    )


if __name__ == "__main__":
    try:
        result = check()
    except Exception:
        result = False
    raise SystemExit(print_result(result))
