from floris import FlorisModel
import yaml
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
    p_wake = float((f.get_turbine_powers() / 1000.0).sum())
    f.run_no_wake()
    p_nowake = float((f.get_turbine_powers() / 1000.0).sum())
    loss = (p_nowake - p_wake) / max(abs(p_nowake), 1e-9) * 100.0
    vals = [p_nowake, p_wake, loss]
    Path("summary.txt").write_text(", ".join(f"{v:.6f}" for v in vals)+"\n", encoding="utf-8")
