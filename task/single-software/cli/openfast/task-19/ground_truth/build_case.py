#!/usr/bin/env python3
from __future__ import annotations

import math
import re
from pathlib import Path


ROOT = Path("/home/user/Desktop")
DT = 0.01
T_MAX = 60.0
G = 9.80665
TARGET_PEAK_ACCELERATION = 0.2 * G


def pulse_kinematics(time: float, scale: float) -> tuple[float, float, float]:
    if time < 30.0 or time > 60.0:
        return 0.0, 0.0, 0.0
    tau = time - 30.0
    envelope_frequency = math.pi / 30.0
    carrier_frequency = 2.0 * math.pi
    envelope = math.sin(envelope_frequency * tau) ** 4
    envelope_d1 = (
        4.0
        * envelope_frequency
        * math.sin(envelope_frequency * tau) ** 3
        * math.cos(envelope_frequency * tau)
    )
    envelope_d2 = 4.0 * envelope_frequency**2 * (
        3.0 * math.sin(envelope_frequency * tau) ** 2 * math.cos(envelope_frequency * tau) ** 2
        - math.sin(envelope_frequency * tau) ** 4
    )
    carrier = math.sin(carrier_frequency * tau)
    carrier_d1 = carrier_frequency * math.cos(carrier_frequency * tau)
    carrier_d2 = -(carrier_frequency**2) * carrier
    displacement = scale * envelope * carrier
    velocity = scale * (envelope_d1 * carrier + envelope * carrier_d1)
    acceleration = scale * (
        envelope_d2 * carrier + 2.0 * envelope_d1 * carrier_d1 + envelope * carrier_d2
    )
    return displacement, velocity, acceleration


def make_motion() -> None:
    unscaled_peak = max(
        abs(pulse_kinematics(step * DT, 1.0)[2])
        for step in range(round(T_MAX / DT) + 1)
    )
    scale = TARGET_PEAK_ACCELERATION / unscaled_peak
    rows: list[str] = []
    for step in range(round(T_MAX / DT) + 1):
        time = step * DT
        displacement, velocity, acceleration = pulse_kinematics(time, scale)
        values = (
            time,
            displacement, 0.0, 0.0, 0.0, 0.0, 0.0,
            velocity, 0.0, 0.0, 0.0, 0.0, 0.0,
            acceleration, 0.0, 0.0, 0.0, 0.0, 0.0,
        )
        rows.append(" ".join(f"{value:.10e}" for value in values))
    (ROOT / "earthquake_motion.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def make_subdyn_input() -> None:
    text = (ROOT / "subdyn_eq_base.dat").read_text(encoding="utf-8")
    text = re.sub(r"(?m)^\s*\S+\s+ExtLdMod\s+-.*\n?", "", text)
    text = text.replace(
        '"-ReactMXss, -ReactMYss, -ReactMZss"',
        '"ReactMXss, ReactMYss, ReactMZss"',
    )
    if '"Intf1TDXss"' not in text:
        text = re.sub(
            r"(?m)^END of output channels.*$",
            '"Intf1TDXss" - Prescribed transition-piece X displacement.\n'
            "END of output channels and end of file.",
            text,
            count=1,
        )
    (ROOT / "subdyn_eq.dat").write_text(text, encoding="utf-8")


def make_driver() -> None:
    driver = """--- SubDyn Driver input file ----------------------------------------------------
Deterministic prescribed transition-piece earthquake-motion case
False                          Echo
---------------------- ENVIRONMENTAL CONDITIONS -------------------------------------
9.80665                        Gravity
20.0                           WtrDpth
---------------------- SUBDYN --------------------------------------------------------
"subdyn_eq.dat"                SDInputFile
"earthquake_sd"                OutRootName
6000                           NSteps
0.01                           TimeInterval
1                              nTP
0.0                            TP_RefPoint_X
0.0                            TP_RefPoint_Y
10.0                           TP_RefPoint_Z
0.0                            SubRotateZ
---------------------- INPUTS --------------------------------------------------------
2                              InputsMod
"earthquake_motion.txt"        InputsFile
---------------------- STEADY INPUTS -------------------------------------------------
0 0 0 0 0 0                    uTPInSteady
0 0 0 0 0 0                    uDotTPInSteady
0 0 0 0 0 0                    uDotDotTPInSteady
---------------------- LOADS ---------------------------------------------------------
0                              nAppliedLoads
ALJointID Fx Fy Fz Mx My Mz UnsteadyFile
(-) (N) (N) (N) (Nm) (Nm) (Nm) (-)
END of driver input file
"""
    (ROOT / "earthquake.dvr").write_text(driver, encoding="utf-8")


def main() -> None:
    make_motion()
    make_subdyn_input()
    make_driver()


if __name__ == "__main__":
    main()
