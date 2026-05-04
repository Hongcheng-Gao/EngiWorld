from floris import FlorisModel
import yaml, numpy as np
from pathlib import Path


def build_custom():
    src = Path(__file__).resolve().parent.parent / "init_file" / "custom_turbine.yaml"
    custom = yaml.safe_load(src.read_text(encoding="utf-8"))
    custom.pop("generator_efficiency", None)
    custom.setdefault("TSR", 8.0)
    custom.setdefault("power_thrust_table", {}).setdefault("ref_tilt", 0.0)
    custom["power_thrust_table"].setdefault("cosine_loss_exponent_yaw", 1.88)
    custom["power_thrust_table"].setdefault("cosine_loss_exponent_tilt", 1.88)
    return custom


def cfg(custom):
    import sys
    p = Path(sys.prefix) / "lib" / "python3.10" / "site-packages" / "floris" / "default_inputs.yaml"
    c = yaml.safe_load(p.read_text(encoding="utf-8"))
    c["logging"]["console"]["level"] = "ERROR"
    c["farm"]["layout_x"] = [0.0]
    c["farm"]["layout_y"] = [0.0]
    c["farm"]["turbine_type"] = [custom]
    return c

if __name__ == "__main__":
    custom = build_custom()
    ws = np.array([3.0, 5.0, 7.0, 9.0, 11.0, 13.0, 15.0])
    f = FlorisModel(cfg(custom))
    f.set(wind_directions=np.full(ws.shape, 270.0), wind_speeds=ws, turbulence_intensities=np.full(ws.shape, 0.06))
    f.run_no_wake()
    p = (f.get_turbine_powers() / 1000.0).reshape(-1)
    td = f.core.farm.turbine_definitions[0]["power_thrust_table"]
    ct = np.interp(ws, np.array(td["wind_speed"], dtype=float), np.array(td["thrust_coefficient"], dtype=float))
    vals = [float(p[0]), float(ct[0]), float(p[3]), float(ct[3]), float(p[6]), float(ct[6])]
    Path("summary.txt").write_text(", ".join(f"{v:.6f}" for v in vals)+"\n", encoding="utf-8")
