from floris import FlorisModel, UncertainFlorisModel
from floris.optimization.yaw_optimization.yaw_optimizer_sr import YawOptimizationSR
import numpy as np, yaml
from pathlib import Path


def cfg():
    import sys
    p = Path(sys.prefix) / "lib" / "python3.10" / "site-packages" / "floris" / "default_inputs.yaml"
    c = yaml.safe_load(p.read_text(encoding="utf-8"))
    c["logging"]["console"]["level"] = "ERROR"
    c["farm"]["layout_x"] = [0.0, 630.0]
    c["farm"]["layout_y"] = [0.0, 0.0]
    c["farm"]["turbine_type"] = ["nrel_5MW", "nrel_5MW"]
    return c

if __name__ == "__main__":
    f_det = FlorisModel(cfg())
    f_det.set(wind_directions=[270], wind_speeds=[8], turbulence_intensities=[0.06])
    yo_det = YawOptimizationSR(f_det, minimum_yaw_angle=-30, maximum_yaw_angle=30, Ny_passes=[3,4])
    r_det = yo_det.optimize(print_progress=False)
    yaw_det = float(np.array(r_det.loc[0, "yaw_angles_opt"]).reshape(-1)[0])
    y_det_arr = np.array(r_det.loc[0, "yaw_angles_opt"], dtype=float).reshape(1, -1)
    f_det.set(yaw_angles=y_det_arr)
    f_det.run()
    p_det = float((f_det.get_turbine_powers() / 1000.0).sum())

    f_unc = UncertainFlorisModel(f_det, wd_std=5.0)
    yo_unc = YawOptimizationSR(f_unc, minimum_yaw_angle=-30, maximum_yaw_angle=30, Ny_passes=[3,4])
    r_unc = yo_unc.optimize(print_progress=False)
    yaw_unc = float(np.array(r_unc.loc[0, "yaw_angles_opt"]).reshape(-1)[0])
    y_unc_arr = np.array(r_unc.loc[0, "yaw_angles_opt"], dtype=float).reshape(1, -1)
    f_unc.set(yaw_angles=y_unc_arr)
    f_unc.run()
    p_unc = float((f_unc.get_turbine_powers() / 1000.0).sum())

    Path("summary.txt").write_text(f"{yaw_det:.6f}, {yaw_unc:.6f}, {p_det:.6f}, {p_unc:.6f}\n", encoding="utf-8")
