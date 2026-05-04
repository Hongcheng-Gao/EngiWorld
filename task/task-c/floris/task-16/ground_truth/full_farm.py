from floris import FlorisModel
import yaml
from pathlib import Path

if __name__ == "__main__":
    cfg = yaml.safe_load(Path("farm.yaml").read_text(encoding="utf-8"))
    f = FlorisModel(cfg)
    f.set(wind_directions=[270], wind_speeds=[8], turbulence_intensities=[0.06])
    f.run()
    p = (f.get_turbine_powers() / 1000.0).reshape(-1)
    total = float(p.sum())
    front = float((p[0] + p[1] + p[2]) / 3.0)
    back = float((p[6] + p[7] + p[8]) / 3.0)
    Path("summary.txt").write_text(f"{total:.6f}, {front:.6f}, {back:.6f}\n", encoding="utf-8")
