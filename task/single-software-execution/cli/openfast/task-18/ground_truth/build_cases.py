#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path("/home/user/Desktop")
GAIN_LABELS = ("PC_GS_KP", "PC_GS_KI")
GAIN_COUNT = 30


def replace_parameter(text: str, name: str, value: str) -> str:
    pattern = rf"(?m)^(\s*)\S+(\s+{re.escape(name)}\s+-.*)$"
    updated, count = re.subn(pattern, rf"\g<1>{value}\g<2>", text)
    if count != 1:
        raise ValueError(f"expected one {name} parameter, found {count}")
    return updated


def values_for_label(text: str, label: str) -> list[float]:
    matches: list[list[float]] = []
    for line in text.splitlines():
        values, marker, comment = line.partition("!")
        if marker and re.search(rf"\b{re.escape(label)}\b", comment):
            matches.append([float(token) for token in values.split()])
    if len(matches) != 1:
        raise ValueError(f"expected one {label} array, found {len(matches)}")
    if len(matches[0]) != GAIN_COUNT:
        raise ValueError(f"{label} must contain {GAIN_COUNT} values")
    return matches[0]


def scale_pitch_gains(text: str, factor: float) -> str:
    output: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        values, marker, comment = line.partition("!")
        label = next(
            (
                candidate
                for candidate in GAIN_LABELS
                if marker and re.search(rf"\b{candidate}\b", comment)
            ),
            None,
        )
        if label is None:
            output.append(line)
            continue
        baseline = [float(token) for token in values.split()]
        if len(baseline) != GAIN_COUNT:
            raise ValueError(f"{label} must contain {GAIN_COUNT} values")
        scaled = "   ".join(f"{factor * value:.9e}" for value in baseline)
        output.append(f"{scaled}   !{comment}")
        seen.add(label)
    if seen != set(GAIN_LABELS):
        raise ValueError("missing ROSCO pitch gain-schedule array")
    result = "\n".join(output) + "\n"
    for label in GAIN_LABELS:
        values_for_label(result, label)
    return result


def normalized_module_copy(source: str, destination: str) -> None:
    text = (ROOT / source).read_text(encoding="utf-8")
    text = text.replace('"../5MW_Baseline/', '"5MW_Baseline/')
    (ROOT / destination).write_text(text, encoding="utf-8")


def build_case(name: str, factor: float) -> None:
    controller = (ROOT / "DISCON.IN").read_text(encoding="utf-8")
    (ROOT / f"rosco_{name}.IN").write_text(
        scale_pitch_gains(controller, factor),
        encoding="utf-8",
    )

    servo = (ROOT / "NRELOffshrBsline5MW_Onshore_ServoDyn.dat").read_text(
        encoding="utf-8"
    )
    servo = replace_parameter(servo, "DLL_FileName", '"libdiscon.so"')
    servo = replace_parameter(servo, "DLL_InFile", f'"rosco_{name}.IN"')
    (ROOT / f"servo_{name}.dat").write_text(servo, encoding="utf-8")

    main = (ROOT / "rosco_base.fst").read_text(encoding="utf-8")
    for parameter, value in {
        "TMax": "60.0",
        "DT_Out": "0.1",
        "OutFileFmt": "1",
        "EDFile": '"elasto_rosco.dat"',
        "InflowFile": (
            '"5MW_Baseline/'
            'NRELOffshrBsline5MW_InflowWind_12mps.dat"'
        ),
        "AeroFile": '"aero_rosco.dat"',
        "ServoFile": f'"servo_{name}.dat"',
    }.items():
        main = replace_parameter(main, parameter, value)
    (ROOT / f"rosco_{name}.fst").write_text(main, encoding="utf-8")


def main() -> None:
    for required in (
        "DISCON.IN",
        "Cp_Ct_Cq.NREL5MW.txt",
        "libdiscon.so",
        "rosco_base.fst",
        "NRELOffshrBsline5MW_Onshore_ServoDyn.dat",
    ):
        if not (ROOT / required).is_file():
            raise FileNotFoundError(required)
    normalized_module_copy(
        "NRELOffshrBsline5MW_Onshore_ElastoDyn.dat",
        "elasto_rosco.dat",
    )
    normalized_module_copy(
        "NRELOffshrBsline5MW_Onshore_AeroDyn.dat",
        "aero_rosco.dat",
    )
    build_case("soft", 0.5)
    build_case("stiff", 1.5)


if __name__ == "__main__":
    main()
