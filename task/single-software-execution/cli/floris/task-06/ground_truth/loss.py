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
    wake_kw = float(fmodel.get_turbine_powers().sum() / 1000.0)
    fmodel.run_no_wake()
    no_wake_kw = float(fmodel.get_turbine_powers().sum() / 1000.0)
    wake_loss_percent = (no_wake_kw - wake_kw) / no_wake_kw * 100.0
    values = [no_wake_kw, wake_kw, wake_loss_percent]
    (ROOT / "summary.txt").write_text(
        ", ".join(f"{value:.6f}" for value in values) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
