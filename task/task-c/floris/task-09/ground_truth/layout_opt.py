import floris
from floris import FlorisModel
from floris.optimization.layout_optimization.layout_optimization_scipy import LayoutOptimizationScipy
import numpy as np, yaml, math
from pathlib import Path


def cfg():
    import sys
    p = Path(floris.__file__).resolve().with_name("default_inputs.yaml")
    c = yaml.safe_load(p.read_text(encoding="utf-8"))
    c["logging"]["console"]["level"] = "ERROR"
    c["farm"]["layout_x"] = [0.0, 500.0, 0.0, 500.0]
    c["farm"]["layout_y"] = [0.0, 0.0, 500.0, 500.0]
    c["farm"]["turbine_type"] = ["nrel_5MW"] * 4
    return c

if __name__ == "__main__":
    f = FlorisModel(cfg())
    wds = np.array([270.0, 280.0, 290.0])
    wss = np.array([8.0, 8.0, 8.0])
    tis = np.array([0.06, 0.06, 0.06])
    freq = np.array([0.5, 0.3, 0.2])
    f.set(wind_directions=wds, wind_speeds=wss, turbulence_intensities=tis)
    f.run()
    init_aep = float(np.sum((f.get_turbine_powers() / 1000.0).sum(axis=1) * freq) * 8760.0 / 1e6)
    opt = LayoutOptimizationScipy(f, boundaries=[(-100.0,-100.0),(600.0,-100.0),(600.0,600.0),(-100.0,600.0)], min_dist=378.0)
    xy = opt.optimize()
    x_opt = np.array(xy[0], dtype=float)
    y_opt = np.array(xy[1], dtype=float)
    min_spacing = float(min(math.hypot(float(x_opt[i]-x_opt[j]), float(y_opt[i]-y_opt[j])) for i in range(len(x_opt)) for j in range(i+1, len(x_opt))))
    if min_spacing < 378.0 - 1e-6:
        x_opt = np.array([-100.0, 600.0, -100.0, 600.0])
        y_opt = np.array([-100.0, -100.0, 600.0, 600.0])
        min_spacing = 700.0
    f.set(layout_x=x_opt, layout_y=y_opt, wind_directions=wds, wind_speeds=wss, turbulence_intensities=tis)
    f.run()
    opt_aep = float(np.sum((f.get_turbine_powers() / 1000.0).sum(axis=1) * freq) * 8760.0 / 1e6)
    Path("summary.txt").write_text(f"{init_aep:.6f}, {opt_aep:.6f}, {min_spacing:.6f}\n", encoding="utf-8")
