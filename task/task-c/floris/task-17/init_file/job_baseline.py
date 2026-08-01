from pathlib import Path
import sys

import floris
from floris import FlorisModel
import numpy as np
import yaml


def configuration():
    source = Path(floris.__file__).resolve().with_name("default_inputs.yaml")
    config = yaml.safe_load(source.read_text(encoding="utf-8"))
    config["logging"]["console"]["level"] = "ERROR"
    config["farm"]["layout_x"] = [0.0, 630.0]
    config["farm"]["layout_y"] = [0.0, 0.0]
    config["farm"]["turbine_type"] = ["nrel_5MW", "nrel_5MW"]
    return config


if __name__ == "__main__":
    model = FlorisModel(configuration())
    model.set(wind_directions=[270.0], wind_speeds=[8.0], turbulence_intensities=[0.06])
    model.run()
    powers_kw = np.asarray(model.get_turbine_powers(), dtype=float).reshape(-1) / 1000.0
    Path(__file__).with_name("baseline.csv").write_text(
        "{:.9f},{:.9f}\n".format(float(powers_kw.sum()), float(powers_kw[1])),
        encoding="utf-8",
    )
