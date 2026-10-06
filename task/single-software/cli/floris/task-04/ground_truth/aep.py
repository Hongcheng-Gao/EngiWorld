from pathlib import Path

import floris
from floris import FlorisModel
import numpy as np
import yaml


ROOT = Path(__file__).resolve().parent


def configuration():
    default_path = Path(floris.__file__).resolve().with_name("default_inputs.yaml")
    config = yaml.safe_load(default_path.read_text(encoding="utf-8"))
    config["logging"]["console"]["level"] = "ERROR"
    config["farm"]["layout_x"] = [0.0, 630.0]
    config["farm"]["layout_y"] = [0.0, 0.0]
    config["farm"]["turbine_type"] = ["nrel_5MW", "nrel_5MW"]
    return config


def main():
    wind_directions = np.array([270.0, 280.0, 290.0])
    frequencies = np.array([0.5, 0.3, 0.2])
    fmodel = FlorisModel(configuration())
    fmodel.set(
        wind_directions=wind_directions,
        wind_speeds=np.full(3, 8.0),
        turbulence_intensities=np.full(3, 0.06),
    )
    fmodel.run()
    farm_total_kw = (fmodel.get_turbine_powers() / 1000.0).sum(axis=1)
    aep_gwh = float(np.sum(farm_total_kw * frequencies) * 8760.0 / 1e6)
    values = [*farm_total_kw.tolist(), aep_gwh]
    (ROOT / "summary.txt").write_text(
        ", ".join(f"{float(value):.6f}" for value in values) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
