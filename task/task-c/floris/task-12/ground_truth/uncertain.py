from pathlib import Path

import floris
from floris import FlorisModel, UncertainFlorisModel
from floris.optimization.yaw_optimization.yaw_optimizer_sr import YawOptimizationSR
import numpy as np
import yaml


ROOT = Path(__file__).resolve().parent


def configuration():
    default_path = Path(floris.__file__).resolve().with_name("default_inputs.yaml")
    config = yaml.safe_load(default_path.read_text(encoding="utf-8"))
    config["logging"]["console"]["level"] = "ERROR"
    config["farm"]["layout_x"] = [0.0, 630.0]
    config["farm"]["layout_y"] = [0.0, 0.0]
    config["farm"]["turbine_type"] = ["nrel_5MW", "nrel_5MW"]
    return config


def set_condition(model):
    model.set(
        wind_directions=[270.0],
        wind_speeds=[8.0],
        turbulence_intensities=[0.06],
    )


def optimize(model):
    set_condition(model)
    optimizer = YawOptimizationSR(
        model,
        minimum_yaw_angle=-30.0,
        maximum_yaw_angle=30.0,
        Ny_passes=[3, 4],
    )
    result = optimizer.optimize(print_progress=False)
    return np.asarray(result.loc[0, "yaw_angles_opt"], dtype=float).reshape(1, -1)


def expected_power_kw(model, yaw_angles):
    set_condition(model)
    model.set(yaw_angles=yaw_angles)
    model.run()
    return float(model.get_turbine_powers().sum() / 1000.0)


def main():
    deterministic_yaw = optimize(FlorisModel(configuration()))
    uncertain_yaw = optimize(UncertainFlorisModel(configuration(), wd_std=5.0))

    evaluator = UncertainFlorisModel(configuration(), wd_std=5.0)
    deterministic_expected_kw = expected_power_kw(evaluator, deterministic_yaw)
    uncertain_expected_kw = expected_power_kw(evaluator, uncertain_yaw)

    values = [
        float(deterministic_yaw[0, 0]),
        float(uncertain_yaw[0, 0]),
        deterministic_expected_kw,
        uncertain_expected_kw,
    ]
    (ROOT / "summary.txt").write_text(
        ", ".join(f"{value:.6f}" for value in values) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
