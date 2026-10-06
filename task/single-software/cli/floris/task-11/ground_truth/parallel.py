from pathlib import Path

import floris
from floris import FlorisModel, ParFlorisModel
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


def set_conditions(model, wind_directions):
    model.set(
        wind_directions=wind_directions,
        wind_speeds=np.full(36, 8.0),
        turbulence_intensities=np.full(36, 0.06),
    )


def main():
    wind_directions = np.arange(0.0, 360.0, 10.0)

    serial_model = FlorisModel(configuration())
    set_conditions(serial_model, wind_directions)
    serial_model.run()
    serial_kw = serial_model.get_turbine_powers().sum(axis=1) / 1000.0

    parallel_model = ParFlorisModel(configuration(), max_workers=4)
    set_conditions(parallel_model, wind_directions)
    parallel_model.run()
    parallel_kw = parallel_model.get_turbine_powers().sum(axis=1) / 1000.0

    relative_error_percent = float(
        np.max(np.abs(parallel_kw - serial_kw) / np.maximum(np.abs(serial_kw), 1e-12))
        * 100.0
    )
    (ROOT / "summary.txt").write_text(
        f"{float(parallel_kw.max()):.6f}, {float(parallel_kw.min()):.6f}, "
        f"{relative_error_percent:.6f}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
