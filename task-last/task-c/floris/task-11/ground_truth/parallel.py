from floris import FlorisModel, ParFlorisModel
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
    wds = np.arange(0.0, 360.0, 10.0)
    wss = np.full(wds.shape, 8.0)
    tis = np.full(wds.shape, 0.06)
    fs = FlorisModel(cfg())
    fs.set(wind_directions=wds, wind_speeds=wss, turbulence_intensities=tis)
    fs.run()
    p_serial = (fs.get_turbine_powers() / 1000.0).sum(axis=1)
    fp = ParFlorisModel(cfg(), max_workers=4)
    fp.set(wind_directions=wds, wind_speeds=wss, turbulence_intensities=tis)
    fp.run()
    p_par = (fp.get_turbine_powers() / 1000.0).sum(axis=1)
    rel = float(np.max(np.abs(p_par - p_serial) / np.maximum(np.abs(p_serial), 1e-9)) * 100.0)
    Path("summary.txt").write_text(f"{float(p_par.max()):.6f}, {float(p_par.min()):.6f}, {rel:.6f}\n", encoding="utf-8")
