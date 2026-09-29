#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
from pathlib import Path


ROOT = Path("/home/user/Desktop")


def replace_parameter(text: str, name: str, value: str) -> str:
    pattern = rf"(?m)^(\s*)\S+(\s+{re.escape(name)}\s+-.*)$"
    updated, count = re.subn(pattern, rf"\g<1>{value}\g<2>", text)
    if count != 1:
        raise ValueError(f"expected one {name} parameter, found {count}")
    return updated


def main() -> None:
    inflow = (ROOT / "IW.dat").read_text(encoding="utf-8")
    inflow = replace_parameter(inflow, "WindType", "1")
    inflow = replace_parameter(inflow, "PropagationDir", "0")
    inflow = replace_parameter(inflow, "HWindSpeed", "8.0")
    inflow = replace_parameter(inflow, "PLExp", "0.0")
    (ROOT / "farm_inflow.dat").write_text(inflow, encoding="utf-8")

    shutil.copyfile(ROOT / "NRELOffshrBsline5MW_Onshore_ElastoDyn_8mps.dat", ROOT / "elasto_farm.dat")
    elasto_path = ROOT / "elasto_farm.dat"
    elasto = elasto_path.read_text(encoding="utf-8")
    elasto = elasto.replace('"../5MW_Baseline/', '"5MW_Baseline/')
    elasto = replace_parameter(elasto, "GenDOF", "False")
    elasto = replace_parameter(elasto, "RotSpeed", "9.0")
    elasto_path.write_text(elasto, encoding="utf-8")

    aero = (ROOT / "5MW_Baseline/AD.dat").read_text(encoding="utf-8")
    aero = aero.replace('"../5MW_Baseline/', '"5MW_Baseline/')
    if '"RtAeroPwr"' not in aero:
        aero = re.sub(r"(?m)^END.*$", '"RtAeroPwr"\nEND', aero, count=1)
    (ROOT / "aero_farm.dat").write_text(aero, encoding="utf-8")

    for number, source in ((1, "FFTest_WT1.fst"), (2, "FFTest_WT2.fst")):
        fst = (ROOT / source).read_text(encoding="utf-8")
        for name, value in {
            "TMax": "630.0",
            "CompInflow": "1",
            "CompServo": "0",
            "DT_Out": "0.1",
            "OutFileFmt": "1",
            "EDFile": '"elasto_farm.dat"',
            "InflowFile": '"farm_inflow.dat"',
            "AeroFile": '"aero_farm.dat"',
        }.items():
            fst = replace_parameter(fst, name, value)
        (ROOT / f"turbine{number}.fst").write_text(fst, encoding="utf-8")

    farm = (ROOT / "farm_base.fstf").read_text(encoding="utf-8")
    farm = replace_parameter(farm, "TMax", "630.0")
    farm = replace_parameter(farm, "Mod_AmbWind", "2")
    farm = replace_parameter(farm, "InflowFile", '"farm_inflow.dat"')
    farm = replace_parameter(farm, "NumTurbines", "2")
    farm = replace_parameter(farm, "Mod_Wake", "1")
    farm = replace_parameter(farm, "WAT", "0")
    farm = replace_parameter(farm, "OutFileFmt", "1")
    farm = farm.replace(
        ' {X1}   {Y1}    0.0    "NRELOffshrBsline5MW.fst"   -69.49   -50.0   5.0      10.17    10.0     10.0\n'
        ' {X2}   {Y2}    0.0    "NRELOffshrBsline5MW.fst"   296.63   -80.0   5.0      10.17    10.0     10.0',
        ' 0.0     0.0    0.0    "turbine1.fst"              -69.49   -80.0   5.0      10.17    10.0     10.0\n'
        ' 630.0   0.0    0.0    "turbine2.fst"              560.51   -80.0   5.0      10.17    10.0     10.0',
    )
    if "{X1}" in farm or "{X2}" in farm:
        raise ValueError("could not replace FAST.Farm turbine table")
    (ROOT / "farm.fstf").write_text(farm, encoding="utf-8")


if __name__ == "__main__":
    main()
