from floris import FlorisModel
import numpy as np
import yaml
from pathlib import Path


def build_cfg():
    from pathlib import Path
    import sys
    p = Path(sys.prefix) / "lib" / "python3.10" / "site-packages" / "floris" / "default_inputs.yaml"
    cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
    cfg["logging"]["console"]["level"] = "ERROR"
    cfg["farm"]["layout_x"] = [0.0, 630.0]
    cfg["farm"]["layout_y"] = [0.0, 0.0]
    cfg["farm"]["turbine_type"] = ["nrel_5MW", "nrel_5MW"]
    cfg["wake"]["model_strings"]["velocity_model"] = "gauss"
    cfg["wake"]["model_strings"]["deflection_model"] = "gauss"
    return cfg


if __name__ == "__main__":
    fmodel = FlorisModel(build_cfg())
    fmodel.set(wind_directions=[270], wind_speeds=[8], turbulence_intensities=[0.06])
    fmodel.run()
    base = float((fmodel.get_turbine_powers() / 1000.0)[0, 1])
    fmodel.set(yaw_angles=np.array([[20.0, 0.0]], dtype=float))
    fmodel.run()
    yawed = float((fmodel.get_turbine_powers() / 1000.0)[0, 1])
    gain = (yawed - base) / max(abs(base), 1e-9) * 100.0
    out = f"{base:.6f}, {yawed:.6f}, {gain:.6f}\n"
    Path("summary.txt").write_text(out, encoding="utf-8")
