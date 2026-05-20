from floris import FlorisModel
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
    wds = np.array([270.0, 280.0, 290.0])
    wss = np.array([8.0, 8.0, 8.0])
    tis = np.array([0.06, 0.06, 0.06])
    freq = np.array([0.5, 0.3, 0.2])
    f.set(wind_directions=wds, wind_speeds=wss, turbulence_intensities=tis)
    f.run()
    farm_kw = (f.get_turbine_powers() / 1000.0).sum(axis=1)
    aep_gwh = float(np.sum(farm_kw * freq) * 8760.0 / 1e6)
    vals = [float(farm_kw[0]), float(farm_kw[1]), float(farm_kw[2]), aep_gwh]
    Path("summary.txt").write_text(", ".join(f"{v:.6f}" for v in vals)+"\n", encoding="utf-8")
