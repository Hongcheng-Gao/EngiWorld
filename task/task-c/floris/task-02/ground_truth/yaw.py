from pathlib import Path

from floris import FlorisModel
import numpy as np


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "two_turbine.yaml"
if not CONFIG.exists():
    CONFIG = ROOT.parent / "init_file" / "two_turbine.yaml"


def main():
    fmodel = FlorisModel(CONFIG)
    fmodel.set(
        wind_directions=[270.0],
        wind_speeds=[8.0],
        turbulence_intensities=[0.06],
        yaw_angles=np.array([[0.0, 0.0]]),
    )
    fmodel.run()
    baseline_t1_kw = float(fmodel.get_turbine_powers()[0, 1] / 1000.0)

    fmodel.set(yaw_angles=np.array([[20.0, 0.0]]))
    fmodel.run()
    yawed_t1_kw = float(fmodel.get_turbine_powers()[0, 1] / 1000.0)
    gain_percent = (yawed_t1_kw - baseline_t1_kw) / baseline_t1_kw * 100.0

    (ROOT / "summary.txt").write_text(
        f"{baseline_t1_kw:.6f}, {yawed_t1_kw:.6f}, {gain_percent:.6f}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
