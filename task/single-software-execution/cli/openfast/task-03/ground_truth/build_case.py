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
    servo = (ROOT / "servo_step_base.dat").read_text(encoding="utf-8")
    for blade in (1, 2, 3):
        servo = replace_parameter(servo, f"TPitManS({blade})", "30.0")
        servo = replace_parameter(servo, f"PitManRat({blade})", "10.0")
        servo = replace_parameter(servo, f"BlPitchF({blade})", "10.0")
    (ROOT / "servo_step.dat").write_text(servo, encoding="utf-8")

    shutil.copyfile(
        ROOT / "NRELOffshrBsline5MW_Onshore_ElastoDyn.dat",
        ROOT / "elasto_step.dat",
    )
    elasto_path = ROOT / "elasto_step.dat"
    elasto = elasto_path.read_text(encoding="utf-8")
    elasto = elasto.replace('"../5MW_Baseline/', '"5MW_Baseline/')
    if '"BldPitch2"' not in elasto:
        elasto = elasto.replace(
            '"BldPitch1"               - Blade 1 pitch angle\n',
            '"BldPitch1"               - Blade 1 pitch angle\n'
            '"BldPitch2"               - Blade 2 pitch angle\n'
            '"BldPitch3"               - Blade 3 pitch angle\n',
        )
    elasto_path.write_text(elasto, encoding="utf-8")

    shutil.copyfile(
        ROOT / "NRELOffshrBsline5MW_Onshore_AeroDyn.dat",
        ROOT / "aero_step.dat",
    )
    aero_path = ROOT / "aero_step.dat"
    aero = aero_path.read_text(encoding="utf-8")
    aero = aero.replace('"../5MW_Baseline/', '"5MW_Baseline/')
    aero_path.write_text(aero, encoding="utf-8")

    fst = (ROOT / "pitch_step.fst").read_text(encoding="utf-8")
    for name, value in {
        "TMax": "60.0",
        "DT_Out": "0.1",
        "OutFileFmt": "1",
        "EDFile": '"elasto_step.dat"',
        "AeroFile": '"aero_step.dat"',
        "ServoFile": '"servo_step.dat"',
    }.items():
        fst = replace_parameter(fst, name, value)
    (ROOT / "case.fst").write_text(fst, encoding="utf-8")


if __name__ == "__main__":
    main()
