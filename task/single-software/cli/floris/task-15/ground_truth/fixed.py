from pathlib import Path

from floris import FlorisModel


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
    fmodel.run()
    powers_kw = fmodel.get_turbine_powers().reshape(-1) / 1000.0
    (ROOT / "fixed_summary.txt").write_text(
        f"{float(powers_kw[0]):.6f}, {float(powers_kw[1]):.6f}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
