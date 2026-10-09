from pathlib import Path

from floris import FlorisModel
import numpy as np


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "derating_base.yaml"
if not CONFIG.exists():
    CONFIG = ROOT.parent / "init_file" / "derating_base.yaml"


def main():
    fmodel = FlorisModel(CONFIG)
    fmodel.set(
        wind_directions=[270.0],
        wind_speeds=[8.0],
        turbulence_intensities=[0.06],
    )
    fmodel.run()
    baseline_powers_w = np.asarray(fmodel.get_turbine_powers(), dtype=float)
    baseline_total_kw = float(baseline_powers_w.sum() / 1000.0)
    upstream_setpoint_w = 0.8 * float(baseline_powers_w[0, 0])

    fmodel.set_operation_model("simple-derating")
    fmodel.set(power_setpoints=np.array([[upstream_setpoint_w, None, None]], dtype=object))
    fmodel.run()
    derated_total_kw = float(fmodel.get_turbine_powers().sum() / 1000.0)
    net_change_kw = derated_total_kw - baseline_total_kw

    (ROOT / "summary.txt").write_text(
        f"{baseline_total_kw:.6f}, {derated_total_kw:.6f}, {net_change_kw:.6f}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
