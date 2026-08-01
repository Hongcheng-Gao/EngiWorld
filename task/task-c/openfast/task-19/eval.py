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
EXPECTED = (0.049626, 262.790752)
REL_TOL = 2.0e-3
ABS_TOL = 2.0e-5


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def close(actual: float, expected: float, rel_tol: float = REL_TOL, abs_tol: float = ABS_TOL) -> bool:
    return math.isfinite(actual) and abs(actual - expected) <= max(
        abs_tol, rel_tol * max(1.0, abs(expected))
    )


def parameter(text: str, name: str) -> str:
    match = re.search(rf"^\s*(\S+).*?\s{re.escape(name)}(?:\s+-.*)?$", text, re.MULTILINE)
    if not match:
        raise ValueError(f"missing parameter {name}")
    return match.group(1).strip('"').rstrip(",")


def pulse_kinematics(time: float, scale: float) -> tuple[float, float, float]:
    if time < 30.0 or time > 60.0:
        return 0.0, 0.0, 0.0
    tau = time - 30.0
    envelope_frequency = math.pi / 30.0
    carrier_frequency = 2.0 * math.pi
    sine = math.sin(envelope_frequency * tau)
    cosine = math.cos(envelope_frequency * tau)
    envelope = sine**4
    envelope_d1 = 4.0 * envelope_frequency * sine**3 * cosine
    envelope_d2 = 4.0 * envelope_frequency**2 * (3.0 * sine**2 * cosine**2 - sine**4)
    carrier = math.sin(carrier_frequency * tau)
    carrier_d1 = carrier_frequency * math.cos(carrier_frequency * tau)
    carrier_d2 = -(carrier_frequency**2) * carrier
    displacement = scale * envelope * carrier
    velocity = scale * (envelope_d1 * carrier + envelope * carrier_d1)
    acceleration = scale * (
        envelope_d2 * carrier + 2.0 * envelope_d1 * carrier_d1 + envelope * carrier_d2
    )
    return displacement, velocity, acceleration


def check_motion(path: Path) -> bool:
    rows: list[list[float]] = []
    for line in read(path).splitlines():
        fields = line.split()
        if len(fields) != 19:
            return False
        rows.append([float(value) for value in fields])
    if len(rows) != 6001:
        return False

    unscaled_peak = max(
        abs(pulse_kinematics(step * DT, 1.0)[2])
        for step in range(round(T_MAX / DT) + 1)
    )
    scale = TARGET_PEAK_ACCELERATION / unscaled_peak
    peak_acceleration = 0.0
    for index, row in enumerate(rows):
        time = index * DT
        if not close(row[0], time, rel_tol=0.0, abs_tol=2.0e-9):
            return False
        expected = pulse_kinematics(time, scale)
        actual = (row[1], row[7], row[13])
        if any(not close(value, target, rel_tol=2.0e-8, abs_tol=2.0e-9) for value, target in zip(actual, expected)):
            return False
        if any(abs(row[column]) > 1.0e-12 for column in (*range(2, 7), *range(8, 13), *range(14, 19))):
            return False
        peak_acceleration = max(peak_acceleration, abs(row[13]))
    return close(peak_acceleration, TARGET_PEAK_ACCELERATION, rel_tol=0.0, abs_tol=2.0e-8)


def output_metrics(path: Path) -> tuple[float, float]:
    lines = read(path).splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.split()[:1] == ["Time"])
    headers = lines[header_index].split()
    units = lines[header_index + 1].split()
    time_i = headers.index("Time")
    displacement_i = headers.index("Intf1TDXss")
    moment_i = headers.index("ReactMYss")
    if units[displacement_i] != "(m)" or units[moment_i] != "(N*m)":
        raise ValueError("unexpected native SubDyn units")

    all_rows: list[list[float]] = []
    for line in lines[header_index + 2 :]:
        fields = line.split()
        if len(fields) != len(headers):
            continue
        try:
            all_rows.append([float(value) for value in fields])
        except ValueError:
            continue
    if len(all_rows) != 6000 or not close(all_rows[-1][time_i], 59.99, rel_tol=0.0, abs_tol=1.0e-8):
        raise ValueError("incomplete SubDyn output")
    rows = [row for row in all_rows if row[time_i] >= 30.0]
    if len(rows) != 3000:
        raise ValueError("incorrect excitation-window sample count")
    return (
        max(abs(row[displacement_i]) for row in rows),
        max(abs(row[moment_i]) for row in rows) / 1.0e6,
    )


def parse_summary(path: Path) -> tuple[float, float]:
    rows = [line.strip() for line in read(path).splitlines() if line.strip()]
    if len(rows) != 1:
        raise ValueError("summary must contain one row")
    values = tuple(float(value.strip()) for value in rows[0].split(","))
    if len(values) != 2 or not all(math.isfinite(value) for value in values):
        raise ValueError("summary must contain two finite values")
    return values


def check() -> bool:
    required = (
        "build_case.py",
        "postprocess.py",
        "earthquake_motion.txt",
        "subdyn_eq.dat",
        "earthquake.dvr",
        "earthquake_sd.SD.out",
        "earthquake_sd.SD.sum.yaml",
        "earthquake_sd.log",
        "summary.txt",
    )
    if any(not (ROOT / name).is_file() or (ROOT / name).stat().st_size == 0 for name in required):
        return False

    driver = read(ROOT / "earthquake.dvr")
    expected_driver = {
        "NSteps": "6000",
        "TimeInterval": "0.01",
        "nTP": "1",
        "TP_RefPoint_X": "0.0",
        "TP_RefPoint_Y": "0.0",
        "TP_RefPoint_Z": "10.0",
        "InputsMod": "2",
        "InputsFile": "earthquake_motion.txt",
        "nAppliedLoads": "0",
    }
    if any(parameter(driver, name) != value for name, value in expected_driver.items()):
        return False
    if "ALJointID Fx Fy Fz Mx My Mz UnsteadyFile" not in driver:
        return False

    subdyn = read(ROOT / "subdyn_eq.dat")
    if "ExtLdMod" in subdyn:
        return False
    if re.search(r"(?<![-A-Za-z0-9_])ReactMYss(?![A-Za-z0-9_])", subdyn) is None:
        return False
    if re.search(r"(?<![-A-Za-z0-9_])Intf1TDXss(?![A-Za-z0-9_])", subdyn) is None:
        return False
    if re.search(r"(?<![A-Za-z0-9_])-ReactMYss(?![A-Za-z0-9_])", subdyn):
        return False
    if not check_motion(ROOT / "earthquake_motion.txt"):
        return False

    log = read(ROOT / "earthquake_sd.log")
    if "Running SubDyn Driver a part of OpenFAST - v5.0.0" not in log:
        return False
    if "Simulated Time:        59.99 seconds" not in log or "Total Real Time:" not in log:
        return False
    if any(marker in log for marker in ("Premature EOF", "Invalid numerical input", "FATAL ERROR")):
        return False

    calculated = output_metrics(ROOT / "earthquake_sd.SD.out")
    reported = parse_summary(ROOT / "summary.txt")
    return all(close(actual, expected) for actual, expected in zip(calculated, EXPECTED)) and all(
        close(actual, expected) for actual, expected in zip(reported, EXPECTED)
    ) and all(close(actual, calculated_value, rel_tol=0.0, abs_tol=2.0e-5) for actual, calculated_value in zip(reported, calculated))


def main() -> int:
    try:
        result = check()
    except Exception:
        result = False
    print("True" if result else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
