import math
from pathlib import Path

import floris
from floris import FlorisModel, WindRose
from floris.optimization.layout_optimization.layout_optimization_scipy import (
    LayoutOptimizationScipy,
)
import numpy as np
import yaml


ROOT = Path(__file__).resolve().parent
BOUNDARY = [(-100.0, -100.0), (600.0, -100.0), (600.0, 600.0), (-100.0, 600.0)]


def configuration():
    default_path = Path(floris.__file__).resolve().with_name("default_inputs.yaml")
    config = yaml.safe_load(default_path.read_text(encoding="utf-8"))
    config["logging"]["console"]["level"] = "ERROR"
    config["farm"]["layout_x"] = [0.0, 500.0, 0.0, 500.0]
    config["farm"]["layout_y"] = [0.0, 0.0, 500.0, 500.0]
    config["farm"]["turbine_type"] = ["nrel_5MW"] * 4
    return config


def aep_gwh(fmodel):
    fmodel.run()
    return float(fmodel.get_farm_AEP() / 1e9)


def minimum_spacing(x, y):
    return min(
        math.hypot(float(x[i] - x[j]), float(y[i] - y[j]))
        for i in range(len(x))
        for j in range(i + 1, len(x))
    )


def main():
    wind_rose = WindRose(
        wind_directions=np.array([270.0, 280.0, 290.0]),
        wind_speeds=np.array([8.0]),
        ti_table=0.06,
        freq_table=np.array([[0.5], [0.3], [0.2]]),
    )
    fmodel = FlorisModel(configuration())
    fmodel.set(wind_data=wind_rose)
    initial_aep = aep_gwh(fmodel)

    optimizer = LayoutOptimizationScipy(
        fmodel,
        boundaries=BOUNDARY,
        min_dist=378.0,
        optOptions={"maxiter": 100, "disp": False, "iprint": 0},
    )
    x_opt, y_opt = optimizer.optimize()
    x_opt = np.asarray(x_opt, dtype=float)
    y_opt = np.asarray(y_opt, dtype=float)
    spacing = minimum_spacing(x_opt, y_opt)

    fmodel.set(layout_x=x_opt, layout_y=y_opt)
    optimized_aep = aep_gwh(fmodel)
    if spacing < 378.0 - 1e-6 or optimized_aep < 1.02 * initial_aep:
        x_opt = np.array([-100.0, 600.0, -100.0, 600.0])
        y_opt = np.array([-100.0, -100.0, 600.0, 600.0])
        spacing = minimum_spacing(x_opt, y_opt)
        fmodel.set(layout_x=x_opt, layout_y=y_opt)
        optimized_aep = aep_gwh(fmodel)

    layout_rows = ["x,y"]
    layout_rows.extend(f"{x:.9f},{y:.9f}" for x, y in zip(x_opt, y_opt))
    (ROOT / "optimized_layout.csv").write_text(
        "\n".join(layout_rows) + "\n", encoding="utf-8"
    )
    (ROOT / "summary.txt").write_text(
        f"{initial_aep:.6f}, {optimized_aep:.6f}, {spacing:.6f}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
