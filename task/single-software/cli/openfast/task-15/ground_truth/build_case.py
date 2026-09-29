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
    elasto = (ROOT / "elasto_tsr_base.dat").read_text(encoding="utf-8")
    elasto = elasto.replace('"../5MW_Baseline/', '"5MW_Baseline/')
    elasto = replace_parameter(elasto, "GenDOF", "False")
    elasto = replace_parameter(elasto, "RotSpeed", "9.0")
    (ROOT / "minimal_elasto.dat").write_text(elasto, encoding="utf-8")

    shutil.copyfile(ROOT / "NRELOffshrBsline5MW_Onshore_AeroDyn.dat", ROOT / "minimal_aero.dat")
    aero_path = ROOT / "minimal_aero.dat"
    aero = aero_path.read_text(encoding="utf-8")
    aero = aero.replace('"../5MW_Baseline/', '"5MW_Baseline/')
    for channel in ("RtAeroPwr", "RtAeroFxh"):
        if f'"{channel}"' not in aero:
            aero = re.sub(r"(?m)^END.*$", f'"{channel}"\nEND', aero, count=1)
    aero_path.write_text(aero, encoding="utf-8")

    fst = (ROOT / "tsr_scan.fst").read_text(encoding="utf-8")
    for name, value in {
        "TMax": "30.0",
        "DT": "0.0125",
        "DT_Out": "0.1",
        "OutFileFmt": "1",
        "CompInflow": "1",
        "CompAero": "2",
        "CompServo": "0",
        "EDFile": '"minimal_elasto.dat"',
        "InflowFile": '"5MW_Baseline/NRELOffshrBsline5MW_InflowWind_Steady8mps.dat"',
        "AeroFile": '"minimal_aero.dat"',
    }.items():
        fst = replace_parameter(fst, name, value)
    (ROOT / "minimal.fst").write_text(fst, encoding="utf-8")


if __name__ == "__main__":
    main()
