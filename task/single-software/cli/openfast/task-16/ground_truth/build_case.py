#!/usr/bin/env python3
from __future__ import annotations

import re
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
    for degree_of_freedom in (
        "FlapDOF1",
        "FlapDOF2",
        "EdgeDOF",
        "DrTrDOF",
        "GenDOF",
        "YawDOF",
        "TwFADOF1",
        "TwFADOF2",
        "TwSSDOF1",
        "TwSSDOF2",
    ):
        elasto = replace_parameter(elasto, degree_of_freedom, "False")
    elasto = replace_parameter(elasto, "RotSpeed", "9.0")
    elasto = replace_parameter(elasto, "OverHang", "20.0")
    (ROOT / "elasto_shadow.dat").write_text(elasto, encoding="utf-8")

    aero_base = (ROOT / "aero_twrshadow_base.dat").read_text(encoding="utf-8")
    for label, shadow in (("notower", 0), ("tower", 1)):
        aero = aero_base.replace("{TWRSHADOW}", str(shadow))
        if '"RtAeroPwr"' not in aero:
            aero = re.sub(r"(?m)^END of OutList.*$", '"RtAeroPwr"\nEND of OutList', aero, count=1)
        (ROOT / f"aero_{label}.dat").write_text(aero, encoding="utf-8")

        fst = (ROOT / "tsr_scan.fst").read_text(encoding="utf-8")
        for name, value in {
            "TMax": "30.0",
            "DT_Out": "0.1",
            "OutFileFmt": "1",
            "CompInflow": "1",
            "CompAero": "2",
            "CompServo": "0",
            "EDFile": '"elasto_shadow.dat"',
            "InflowFile": '"5MW_Baseline/NRELOffshrBsline5MW_InflowWind_Steady8mps.dat"',
            "AeroFile": f'"aero_{label}.dat"',
        }.items():
            fst = replace_parameter(fst, name, value)
        (ROOT / f"case_{label}.fst").write_text(fst, encoding="utf-8")


if __name__ == "__main__":
    main()
