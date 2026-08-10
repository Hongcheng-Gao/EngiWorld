from pathlib import Path

from floris import FlorisModel
import numpy as np


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "heterogeneous.yaml"
if not CONFIG.exists():
    CONFIG = ROOT.parent / "init_file" / "heterogeneous.yaml"


def main():
    fmodel = FlorisModel(CONFIG)
    fmodel.set(
        wind_directions=[270.0],
        wind_speeds=[8.0],
        turbulence_intensities=[0.06],
    )
    fmodel.run()
    powers_kw = np.asarray(fmodel.get_turbine_powers(), dtype=float).reshape(-1) / 1000.0
    if not (powers_kw[1] > powers_kw[0] and powers_kw[3] > powers_kw[2]):
        raise RuntimeError("heterogeneous turbine powers do not match the configured turbine types")
    values = [*powers_kw.tolist(), float(powers_kw.sum())]
    (ROOT / "summary.txt").write_text(
        ", ".join(f"{float(value):.6f}" for value in values) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
