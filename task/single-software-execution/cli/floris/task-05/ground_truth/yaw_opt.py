from pathlib import Path

from floris import FlorisModel
from floris.optimization.yaw_optimization.yaw_optimizer_sr import YawOptimizationSR
import numpy as np


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "two_turbine.yaml"
if not CONFIG.exists():
    CONFIG = ROOT.parent / "init_file" / "two_turbine.yaml"


def main():
    fmodel = FlorisModel(CONFIG)
    fmodel.set(
        wind_directions=[270.0],
        wind_speeds=[8.0],
        turbulence_intensities=[0.06],
    )
    fmodel.run()
    baseline_total_kw = float(fmodel.get_turbine_powers().sum() / 1000.0)

    optimizer = YawOptimizationSR(
        fmodel,
        minimum_yaw_angle=-30.0,
        maximum_yaw_angle=30.0,
        Ny_passes=[3, 4],
    )
    result = optimizer.optimize(print_progress=False)
    yaw_angles = np.asarray(result.loc[0, "yaw_angles_opt"], dtype=float).reshape(1, -1)
    fmodel.set(yaw_angles=yaw_angles)
    fmodel.run()
    optimized_total_kw = float(fmodel.get_turbine_powers().sum() / 1000.0)

    values = [baseline_total_kw, optimized_total_kw, *yaw_angles.reshape(-1).tolist()]
    (ROOT / "summary.txt").write_text(
        ", ".join(f"{float(value):.6f}" for value in values) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
