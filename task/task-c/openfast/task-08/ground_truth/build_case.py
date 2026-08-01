#!/usr/bin/env python3
from __future__ import annotations

import math
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
    wind_rows = [
        "! Explicit deterministic extreme-operating-gust uniform wind file.",
        "! Time WindSpeed WindDir VertSpeed HorizShear VertShear LinVShear GustSpeed",
    ]
    for step in range(601):
        time = step / 10.0
        speed = 11.4
        if 10.0 <= time <= 20.5:
            phase = (time - 10.0) / 10.5
            speed += 7.5 * (1.0 - math.cos(2.0 * math.pi * phase))
        wind_rows.append(f"{time:.1f} {speed:.8f} 0.0 0.0 0.0 0.0 0.0 0.0")
    (ROOT / "eog.wnd").write_text("\n".join(wind_rows) + "\n", encoding="utf-8")

    inflow = (ROOT / "5MW_Baseline/NRELOffshrBsline5MW_InflowWind_Steady13mps.dat").read_text(encoding="utf-8")
    inflow = replace_parameter(inflow, "WindType", "2")
    inflow = replace_parameter(inflow, "FileName_Uni", '"eog.wnd"')
    inflow = replace_parameter(inflow, "RefHt_Uni", "90.0")
    (ROOT / "eog_inflow.dat").write_text(inflow, encoding="utf-8")

    shutil.copyfile(ROOT / "NRELOffshrBsline5MW_Onshore_ElastoDyn.dat", ROOT / "elasto_eog.dat")
    elasto_path = ROOT / "elasto_eog.dat"
    elasto = elasto_path.read_text(encoding="utf-8")
    elasto = elasto.replace('"../5MW_Baseline/', '"5MW_Baseline/')
    for channel in ("RootMyb1", "TTDspFA"):
        if f'"{channel}"' not in elasto:
            elasto = re.sub(r"(?m)^END of OutList.*$", f'"{channel}"\nEND of OutList', elasto, count=1)
    elasto_path.write_text(elasto, encoding="utf-8")

    for source, destination in (
        ("NRELOffshrBsline5MW_Onshore_AeroDyn.dat", "aero_eog.dat"),
        ("NRELOffshrBsline5MW_Onshore_ServoDyn.dat", "servo_eog.dat"),
    ):
        shutil.copyfile(ROOT / source, ROOT / destination)
        path = ROOT / destination
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace('"../5MW_Baseline/', '"5MW_Baseline/'), encoding="utf-8")

    fst = (ROOT / "pitch_step.fst").read_text(encoding="utf-8")
    for name, value in {
        "TMax": "60.0",
        "DT_Out": "0.1",
        "OutFileFmt": "1",
        "EDFile": '"elasto_eog.dat"',
        "InflowFile": '"eog_inflow.dat"',
        "AeroFile": '"aero_eog.dat"',
        "ServoFile": '"servo_eog.dat"',
    }.items():
        fst = replace_parameter(fst, name, value)
    (ROOT / "eog_case.fst").write_text(fst, encoding="utf-8")


if __name__ == "__main__":
    main()
