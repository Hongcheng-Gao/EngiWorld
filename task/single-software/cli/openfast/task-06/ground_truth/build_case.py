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
    shutil.copyfile(ROOT / "moordyn_oc4_base.dat", ROOT / "moordyn.dat")
    sea_state = (ROOT / "SeaState.dat").read_text(encoding="utf-8")
    sea_state = replace_parameter(sea_state, "WaveMod", "0")
    (ROOT / "seastate_moordyn.dat").write_text(sea_state, encoding="utf-8")
    normalized_copy("NRELOffshrBsline5MW_OC4DeepCwindSemi_ElastoDyn.dat", "elasto_moordyn.dat")
    normalized_copy("NRELOffshrBsline5MW_OC3Hywind_AeroDyn.dat", "aero_moordyn.dat")
    normalized_copy("NRELOffshrBsline5MW_OC4DeepCwindSemi_ServoDyn.dat", "servo_moordyn.dat")
    normalized_copy("NRELOffshrBsline5MW_OC4DeepCwindSemi_HydroDyn.dat", "hydrodyn_moordyn.dat")
    elasto_path = ROOT / "elasto_moordyn.dat"
    elasto = elasto_path.read_text(encoding="utf-8")
    elasto = replace_parameter(elasto, "GenDOF", "False")
    elasto = replace_parameter(elasto, "RotSpeed", "9.0")
    elasto_path.write_text(elasto, encoding="utf-8")

    fst = (ROOT / "moordyn_base.fst").read_text(encoding="utf-8")
    for name, value in {
        "TMax": "120.0",
        "CompSeaSt": "1",
        "CompHydro": "1",
        "CompServo": "0",
        "CompMooring": "3",
        "DT_Out": "0.1",
        "OutFileFmt": "1",
        "EDFile": '"elasto_moordyn.dat"',
        "AeroFile": '"aero_moordyn.dat"',
        "ServoFile": '"servo_moordyn.dat"',
        "SeaStFile": '"seastate_moordyn.dat"',
        "HydroFile": '"hydrodyn_moordyn.dat"',
        "MooringFile": '"moordyn.dat"',
    }.items():
        fst = replace_parameter(fst, name, value)
    (ROOT / "moordyn_case.fst").write_text(fst, encoding="utf-8")


if __name__ == "__main__":
    main()
