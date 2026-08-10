import floris
from floris import FlorisModel
import yaml, numpy as np
from pathlib import Path


def cfg():
    p = Path(floris.__file__).resolve().with_name("default_inputs.yaml")
    c = yaml.safe_load(p.read_text(encoding="utf-8"))
    c["logging"]["console"]["level"] = "ERROR"
    c["farm"]["layout_x"] = [0.0]
    c["farm"]["layout_y"] = [0.0]
    c["farm"]["turbine_type"] = ["nrel_5MW"]
    return c

if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    ws = np.arange(4.0, 22.0, 2.0)
    f = FlorisModel(cfg())
    f.set(wind_directions=np.full(ws.shape, 270.0), wind_speeds=ws, turbulence_intensities=np.full(ws.shape, 0.06))
    f.run_no_wake()
    p = (f.get_turbine_powers() / 1000.0).reshape(-1)
    td = f.core.farm.turbine_definitions[0]["power_thrust_table"]
    ct = np.interp(ws, np.array(td["wind_speed"], dtype=float), np.array(td["thrust_coefficient"], dtype=float))
    idx = {4:0, 8:2, 12:4, 20:8}
    vals = [float(p[idx[4]]), float(ct[idx[4]]), float(p[idx[8]]), float(ct[idx[8]]), float(p[idx[12]]), float(ct[idx[12]]), float(p[idx[20]]), float(ct[idx[20]])]
    (root / "summary.txt").write_text(
        ", ".join(f"{v:.6f}" for v in vals) + "\n", encoding="utf-8"
    )
