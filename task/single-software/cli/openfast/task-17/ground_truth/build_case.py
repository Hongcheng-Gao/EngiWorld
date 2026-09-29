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


def normalized_copy(source: str, destination: str) -> None:
    shutil.copyfile(ROOT / source, ROOT / destination)
    path = ROOT / destination
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace('"../5MW_Baseline/', '"5MW_Baseline/'), encoding="utf-8")


def main() -> None:
    normalized_copy("elasto_drivetrain_base.dat", "elasto_drivetrain.dat")
    normalized_copy("NRELOffshrBsline5MW_Onshore_AeroDyn.dat", "aero_drivetrain.dat")
    normalized_copy("NRELOffshrBsline5MW_Onshore_ServoDyn.dat", "servo_drivetrain.dat")

    fst = (ROOT / "drivetrain.fst").read_text(encoding="utf-8")
    for name, value in {
        "TMax": "60.0",
        "DT_Out": "0.1",
        "OutFileFmt": "1",
        "EDFile": '"elasto_drivetrain.dat"',
        "InflowFile": '"5MW_Baseline/NRELOffshrBsline5MW_InflowWind_12mps.dat"',
        "AeroFile": '"aero_drivetrain.dat"',
        "ServoFile": '"servo_drivetrain.dat"',
    }.items():
        fst = replace_parameter(fst, name, value)
    (ROOT / "drivetrain_case.fst").write_text(fst, encoding="utf-8")


if __name__ == "__main__":
    main()
