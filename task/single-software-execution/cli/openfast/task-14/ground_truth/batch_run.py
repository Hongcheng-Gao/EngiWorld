#!/usr/bin/env python3
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent
fst_base = (root / "batch_base.fst").read_text()
inflow_base = (root / "NRELOffshrBsline5MW_InflowWind_base.dat").read_text()
for speed in (4, 8, 11, 15, 20):
    inflow_name = f"NRELOffshrBsline5MW_InflowWind_{speed}.dat"
    fst_name = f"case_ws{speed}.fst"
    (root / inflow_name).write_text(inflow_base.replace("{WS}", str(speed)))
    (root / fst_name).write_text(fst_base.replace("{WS}", str(speed)))
    with (root / f"case_ws{speed}.log").open("w") as log:
        subprocess.run(["/home/user/miniconda3/bin/openfast", fst_name], cwd=root, stdout=log, stderr=subprocess.STDOUT, check=True)
