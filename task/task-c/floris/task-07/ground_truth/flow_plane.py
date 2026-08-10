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
    )

    x = np.arange(756.0, 5000.0, 10.0)
    y = np.zeros_like(x)
    z = np.full_like(x, 90.0)
    velocity = np.asarray(fmodel.sample_flow_at_points(x, y, z), dtype=float).reshape(-1)

    recovered = np.flatnonzero(velocity >= 0.95 * 8.0)
    if recovered.size == 0:
        raise RuntimeError("wake did not recover within the required sampling interval")
    min_velocity = float(velocity.min())
    recovery_distance = float(x[recovered[0]] - 630.0)

    rows = ["x,y,u_eff"]
    rows.extend(
        f"{float(xi):.3f},{float(yi):.3f},{float(ui):.6f}"
        for xi, yi, ui in zip(x, y, velocity)
    )
    (ROOT / "flow_plane.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    (ROOT / "summary.txt").write_text(
        f"{min_velocity:.6f}, {recovery_distance:.6f}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
