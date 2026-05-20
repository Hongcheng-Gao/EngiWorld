from floris import FlorisModel
import numpy as np, yaml
from pathlib import Path


def cfg():
    import sys
    p = Path(sys.prefix) / "lib" / "python3.10" / "site-packages" / "floris" / "default_inputs.yaml"
    c = yaml.safe_load(p.read_text(encoding="utf-8"))
    c["logging"]["console"]["level"] = "ERROR"
    d = 126.0
    s = 7.0 * d
    c["farm"]["layout_x"] = [0.0, s, 2*s, 0.0, s, 2*s, 0.0, s, 2*s]
    c["farm"]["layout_y"] = [0.0, 0.0, 0.0, s, s, s, 2*s, 2*s, 2*s]
    c["farm"]["turbine_type"] = ["nrel_5MW"] * 9
    return c

if __name__ == "__main__":
    f = FlorisModel(cfg())
    wds = np.arange(0.0, 360.0, 30.0)
    wss = np.full(wds.shape, 8.0)
    tis = np.full(wds.shape, 0.06)
    f.set(wind_directions=wds, wind_speeds=wss, turbulence_intensities=tis)
    f.run()
    m = (f.get_turbine_powers() / 1000.0)
    Path("power_matrix.csv").write_text("\n".join(",".join(f"{float(v):.6f}" for v in row) for row in m)+"\n", encoding="utf-8")
    totals = m.sum(axis=1)
    pmax = float(totals.max())
    pmin = float(totals.min())
    f.set(wind_directions=[270], wind_speeds=[8], turbulence_intensities=[0.06])
    f.run_no_wake()
    p_nowake = float((f.get_turbine_powers() / 1000.0).sum())
    loss = (p_nowake - pmin) / max(abs(p_nowake), 1e-9) * 100.0
    Path("summary.txt").write_text(f"{pmax:.6f}, {pmin:.6f}, {loss:.6f}\n", encoding="utf-8")
