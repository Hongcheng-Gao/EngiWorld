from floris import FlorisModel
import yaml, json
from pathlib import Path


def base_cfg():
    import sys
    p = Path(sys.prefix) / "lib" / "python3.10" / "site-packages" / "floris" / "default_inputs.yaml"
    cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
    cfg["logging"]["console"]["level"] = "ERROR"
    cfg["farm"]["layout_x"] = [0.0, 630.0]
    cfg["farm"]["layout_y"] = [0.0, 0.0]
    cfg["farm"]["turbine_type"] = ["nrel_5MW", "nrel_5MW"]
    cfg["wake"]["model_strings"]["deflection_model"] = "gauss"
    return cfg

if __name__ == "__main__":
    vals = []
    for m in ["jensen", "gauss", "cc"]:
        cfg = json.loads(json.dumps(base_cfg()))
        cfg["wake"]["model_strings"]["velocity_model"] = m
        f = FlorisModel(cfg)
        f.set(wind_directions=[270], wind_speeds=[8], turbulence_intensities=[0.06])
        f.run()
        vals.append(float((f.get_turbine_powers() / 1000.0)[0, 1]))
    Path("summary.txt").write_text(", ".join(f"{v:.6f}" for v in vals) + "\n", encoding="utf-8")
