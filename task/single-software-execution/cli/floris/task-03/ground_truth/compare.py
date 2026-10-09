from copy import deepcopy
from pathlib import Path

import floris
from floris import FlorisModel
import yaml


ROOT = Path(__file__).resolve().parent


def base_configuration():
    default_path = Path(floris.__file__).resolve().with_name("default_inputs.yaml")
    config = yaml.safe_load(default_path.read_text(encoding="utf-8"))
    config["logging"]["console"]["level"] = "ERROR"
    config["farm"]["layout_x"] = [0.0, 630.0]
    config["farm"]["layout_y"] = [0.0, 0.0]
    config["farm"]["turbine_type"] = ["nrel_5MW", "nrel_5MW"]
    return config


def main():
    powers_kw = []
    for velocity_model in ("jensen", "gauss", "cc"):
        config = deepcopy(base_configuration())
        config["wake"]["model_strings"]["velocity_model"] = velocity_model
        fmodel = FlorisModel(config)
        fmodel.set(
            wind_directions=[270.0],
            wind_speeds=[8.0],
            turbulence_intensities=[0.06],
        )
        fmodel.run()
        powers_kw.append(float(fmodel.get_turbine_powers()[0, 1] / 1000.0))

    (ROOT / "summary.txt").write_text(
        ", ".join(f"{value:.6f}" for value in powers_kw) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
