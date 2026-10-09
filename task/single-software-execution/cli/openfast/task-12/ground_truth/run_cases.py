#!/usr/bin/env python3
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parent
fst_base = (root / "yaw_error.fst").read_text()
ed_base = (root / "NRELOffshrBsline5MW_ElastoDyn_Yaw.dat").read_text()
for angle in (0, 5, 10, 15, 20):
    ed_name = f"elasto_yaw_{angle}.dat"
    fst_name = f"case_yaw_{angle}.fst"
    ed = re.sub(r"^\s*[-+0-9.]+\s+NacYaw\b.*$", f"      {angle:.1f}   NacYaw          - Initial or fixed nacelle-yaw angle (degrees)", ed_base, flags=re.MULTILINE)
    (root / ed_name).write_text(ed)
    (root / fst_name).write_text(fst_base.replace('"NRELOffshrBsline5MW_ElastoDyn_Yaw.dat"', f'"{ed_name}"'))
    with (root / f"case_yaw_{angle}.log").open("w") as log:
        subprocess.run(["/home/user/miniconda3/bin/openfast", fst_name], cwd=root, stdout=log, stderr=subprocess.STDOUT, check=True)
