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
    subdyn = (ROOT / "subdyn_oc3_base.dat").read_text(encoding="utf-8")
    subdyn, count = re.subn(
        r'(?s)(-+\s*SSOutList:.*?\n).*?(^END .*?$)',
        r'\1"ReactFXss" - Base fore-aft reaction force (kN).\n'
        r'"ReactMYss" - Base fore-aft reaction moment (kN-m).\n\2',
        subdyn,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise ValueError("could not replace SubDyn output list")
    (ROOT / "subdyn.dat").write_text(subdyn, encoding="utf-8")

    normalized_copy("NRELOffshrBsline5MW_OC3Monopile_ElastoDyn.dat", "elasto_subdyn.dat")
    normalized_copy("NRELOffshrBsline5MW_OC3Monopile_AeroDyn.dat", "aero_subdyn.dat")
    normalized_copy("NRELOffshrBsline5MW_OC3Monopile_ServoDyn.dat", "servo_subdyn.dat")

    fst = (ROOT / "subdyn_base.fst").read_text(encoding="utf-8")
    for name, value in {
        "TMax": "30.0",
        "CompSeaSt": "0",
        "CompHydro": "0",
        "CompSub": "1",
        "DT_Out": "0.1",
        "OutFileFmt": "1",
        "EDFile": '"elasto_subdyn.dat"',
        "AeroFile": '"aero_subdyn.dat"',
        "ServoFile": '"servo_subdyn.dat"',
        "SubFile": '"subdyn.dat"',
    }.items():
        fst = replace_parameter(fst, name, value)
    (ROOT / "subdyn_case.fst").write_text(fst, encoding="utf-8")


if __name__ == "__main__":
    main()
