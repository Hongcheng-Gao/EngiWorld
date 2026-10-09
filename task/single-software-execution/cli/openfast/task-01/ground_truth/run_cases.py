#!/usr/bin/env python3
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent
openfast = "/home/user/miniconda3/bin/openfast"
speeds = (4, 8, 11, 15, 20)
inflow_template = (root / "inflow_steady_base.dat").read_text()
fst_template = (root / "power_curve.fst").read_text()

for speed in speeds:
    inflow_name = f"inflow_ws{speed}.dat"
    fst_name = f"case_ws{speed}.fst"
    (root / inflow_name).write_text(inflow_template.replace("{WS}", str(speed)))
    (root / fst_name).write_text(
        fst_template.replace('"NRELOffshrBsline5MW_InflowWind.dat"', f'"{inflow_name}"')
    )
    with (root / f"case_ws{speed}.log").open("w") as log:
        subprocess.run([openfast, fst_name], cwd=root, stdout=log, stderr=subprocess.STDOUT, check=True)
