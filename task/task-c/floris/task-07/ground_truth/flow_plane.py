from floris import FlorisModel
import numpy as np, yaml
from pathlib import Path


def cfg():
    import sys
    p = Path(sys.prefix) / "lib" / "python3.10" / "site-packages" / "floris" / "default_inputs.yaml"
    c = yaml.safe_load(p.read_text(encoding="utf-8"))
    c["logging"]["console"]["level"] = "ERROR"
    c["farm"]["layout_x"] = [0.0, 630.0]
    c["farm"]["layout_y"] = [0.0, 0.0]
    c["farm"]["turbine_type"] = ["nrel_5MW", "nrel_5MW"]
    return c

if __name__ == "__main__":
    f = FlorisModel(cfg())
    f.set(wind_directions=[270], wind_speeds=[8], turbulence_intensities=[0.06])
    f.run()
    xs = np.linspace(0.0, 1000.0, 201)
    ys = np.zeros_like(xs)
    zs = np.full_like(xs, 90.0)
    u = np.array(f.sample_flow_at_points(xs, ys, zs), dtype=float).reshape(-1)
    u_min = float(u.min())
    idx = np.where(u >= 0.95 * 8.0)[0]
    recov = float(xs[idx[0]]) if len(idx) > 0 else 3000.0
    csv_lines = ["x,y,u_eff"]
    csv_lines.extend(f"{x:.3f},0.000,{ui:.6f}" for x, ui in zip(xs, u))
    Path("flow_plane.csv").write_text("\n".join(csv_lines)+"\n", encoding="utf-8")
    Path("summary.txt").write_text(f"{u_min:.6f}, {recov:.6f}\n", encoding="utf-8")
