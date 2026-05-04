from floris import FlorisModel
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
    f = FlorisModel(cfg())
    f.set(wind_directions=[270], wind_speeds=[8], turbulence_intensities=[0.06])
    f.run()
    base = float((f.get_turbine_powers() / 1000.0).sum())
    yo = YawOptimizationSR(f, minimum_yaw_angle=-30, maximum_yaw_angle=30, Ny_passes=[3,4])
    res = yo.optimize(print_progress=False)
    yaw_arr = np.array(res.loc[0, "yaw_angles_opt"], dtype=float).reshape(1, -1)
    f.set(yaw_angles=yaw_arr)
    f.run()
    opt = float((f.get_turbine_powers() / 1000.0).sum())
    vals = [base, opt, float(yaw_arr[0,0]), float(yaw_arr[0,1])]
    Path("summary.txt").write_text(", ".join(f"{v:.6f}" for v in vals)+"\n", encoding="utf-8")
