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


def normalized_copy(source: str, destination: str) -> str:
    shutil.copyfile(ROOT / source, ROOT / destination)
    path = ROOT / destination
    text = path.read_text(encoding="utf-8")
    return text.replace('"../5MW_Baseline/', '"5MW_Baseline/')


def ensure_output_channel(text: str, channel: str) -> str:
    if f'"{channel}"' in text:
        return text
    updated, count = re.subn(
        r"(?m)^END of OutList.*$",
        f'"{channel}"\nEND of OutList section',
        text,
        count=1,
    )
    if count != 1:
        raise ValueError(f"could not add output channel {channel}")
    return updated


def main() -> None:
    inflow = (ROOT / "5MW_Baseline/NRELOffshrBsline5MW_InflowWind_Steady13mps.dat").read_text(encoding="utf-8")
    inflow = replace_parameter(inflow, "WindType", "1")
    inflow = replace_parameter(inflow, "HWindSpeed", "15.0")
    (ROOT / "inflow_shutdown.dat").write_text(inflow, encoding="utf-8")

    elasto = normalized_copy("NRELOffshrBsline5MW_Onshore_ElastoDyn.dat", "elasto_shutdown.dat")
    elasto = replace_parameter(elasto, "RotSpeed", "12.1")
    for channel in ("BldPitch1", "BldPitch2", "BldPitch3", "RotSpeed"):
        elasto = ensure_output_channel(elasto, channel)
    (ROOT / "elasto_shutdown.dat").write_text(elasto, encoding="utf-8")

    aero = normalized_copy("NRELOffshrBsline5MW_Onshore_AeroDyn.dat", "aero_shutdown.dat")
    (ROOT / "aero_shutdown.dat").write_text(aero, encoding="utf-8")

    servo = normalized_copy("servo_shutdown_base.dat", "servo_shutdown.dat")
    servo = replace_parameter(servo, "GenTiStp", "True")
    servo = replace_parameter(servo, "TimGenOf", "20.0")
    servo = replace_parameter(servo, "HSSBrMode", "0")
    for blade in (1, 2, 3):
        servo = replace_parameter(servo, f"TPitManS({blade})", "20.0")
        servo = replace_parameter(servo, f"PitManRat({blade})", "2.0")
        servo = replace_parameter(servo, f"BlPitchF({blade})", "90.0")
    (ROOT / "servo_shutdown.dat").write_text(servo, encoding="utf-8")

    fst = (ROOT / "shutdown.fst").read_text(encoding="utf-8")
    for name, value in {
        "TMax": "90.0",
        "DT_Out": "0.1",
        "OutFileFmt": "1",
        "EDFile": '"elasto_shutdown.dat"',
        "InflowFile": '"inflow_shutdown.dat"',
        "AeroFile": '"aero_shutdown.dat"',
        "ServoFile": '"servo_shutdown.dat"',
    }.items():
        fst = replace_parameter(fst, name, value)
    (ROOT / "shutdown_case.fst").write_text(fst, encoding="utf-8")


if __name__ == "__main__":
    main()
