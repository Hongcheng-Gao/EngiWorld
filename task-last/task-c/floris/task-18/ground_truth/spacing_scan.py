from floris import FlorisModel
import yaml
from pathlib import Path


def base_cfg():
    import sys
    p = Path(sys.prefix) / "lib" / "python3.10" / "site-packages" / "floris" / "default_inputs.yaml"
    c = yaml.safe_load(p.read_text(encoding="utf-8"))
    c["logging"]["console"]["level"] = "ERROR"
    c["farm"]["layout_x"] = [0.0, 630.0]
    c["farm"]["layout_y"] = [0.0, 0.0]
    c["farm"]["turbine_type"] = ["nrel_5MW", "nrel_5MW"]
    return c

if __name__ == "__main__":
    vals = []
    for d_mult in [3.0, 5.0, 7.0, 10.0]:
        cfg = base_cfg()
        cfg["farm"]["layout_x"] = [0.0, 126.0 * d_mult]
        f = FlorisModel(cfg)
        f.set(wind_directions=[270], wind_speeds=[8], turbulence_intensities=[0.06])
        f.run()
        vals.append(float((f.get_turbine_powers() / 1000.0)[0, 1]))
    Path("summary.txt").write_text(", ".join(f"{v:.6f}" for v in vals)+"\n", encoding="utf-8")
