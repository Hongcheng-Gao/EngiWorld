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
    turbulence_intensities = np.array([0.03, 0.06, 0.12])
    fmodel = FlorisModel(configuration())
    fmodel.set(
        wind_directions=np.full(3, 270.0),
        wind_speeds=np.full(3, 8.0),
        turbulence_intensities=turbulence_intensities,
    )
    fmodel.run()
    downstream_kw = fmodel.get_turbine_powers()[:, 1] / 1000.0
    (ROOT / "summary.txt").write_text(
        ", ".join(f"{float(value):.6f}" for value in downstream_kw) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
