from pathlib import Path

import floris
from floris import FlorisModel
import numpy as np
import yaml


ROOT = Path(__file__).resolve().parent
TURBINE_FILE = ROOT / "custom_turbine.yaml"
if not TURBINE_FILE.exists():
    TURBINE_FILE = ROOT.parent / "init_file" / "custom_turbine.yaml"


def configuration(turbine_definition):
    default_path = Path(floris.__file__).resolve().with_name("default_inputs.yaml")
    config = yaml.safe_load(default_path.read_text(encoding="utf-8"))
    config["logging"]["console"]["level"] = "ERROR"
    config["farm"]["layout_x"] = [0.0]
    config["farm"]["layout_y"] = [0.0]
    config["farm"]["turbine_type"] = [turbine_definition]
    return config


def main():
    turbine = yaml.safe_load(TURBINE_FILE.read_text(encoding="utf-8"))
    wind_speeds = np.array([3.0, 5.0, 7.0, 9.0, 11.0, 13.0, 15.0])
    fmodel = FlorisModel(configuration(turbine))
    fmodel.set(
        wind_directions=np.full(7, 270.0),
        wind_speeds=wind_speeds,
        turbulence_intensities=np.full(7, 0.06),
    )
    fmodel.run_no_wake()
    powers_kw = np.asarray(fmodel.get_turbine_powers(), dtype=float).reshape(-1) / 1000.0
    table = fmodel.core.farm.turbine_definitions[0]["power_thrust_table"]
    ct = np.interp(
        wind_speeds,
        np.asarray(table["wind_speed"], dtype=float),
        np.asarray(table["thrust_coefficient"], dtype=float),
    )
    values = [powers_kw[0], ct[0], powers_kw[3], ct[3], powers_kw[6], ct[6]]
    (ROOT / "summary.txt").write_text(
        ", ".join(f"{float(value):.6f}" for value in values) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
