#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RPMS = (6, 9, 12, 15)
AIR_DENSITY = 1.225
ROTOR_RADIUS_M = 63.0
WIND_SPEED_MPS = 8.0


def read_channel_mean(path: Path, channel: str, window_s: float) -> float:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    header_index = next(
        index for index, line in enumerate(lines) if line.split() and line.split()[0] == "Time"
    )
    headers = lines[header_index].split()
    channel_index = headers.index(channel)
    rows: list[tuple[float, float]] = []
    for line in lines[header_index + 2 :]:
        values = line.split()
        if len(values) != len(headers):
            continue
        try:
            rows.append((float(values[0]), float(values[channel_index])))
        except ValueError:
            continue
    if not rows:
        raise ValueError(f"no numeric data in {path.name}")
    start = rows[-1][0] - window_s
    selected = [value for time, value in rows if time >= start]
    if not selected:
        raise ValueError(f"no samples in final {window_s} seconds")
    return sum(selected) / len(selected)


def main() -> int:
    available_power_w = (
        0.5 * AIR_DENSITY * math.pi * ROTOR_RADIUS_M**2 * WIND_SPEED_MPS**3
    )
    result: list[str] = []
    for rpm in RPMS:
        aero_power_w = read_channel_mean(ROOT / f"case_rpm{rpm}.out", "RtAeroPwr", 10.0)
        tsr = (rpm * 2.0 * math.pi / 60.0) * ROTOR_RADIUS_M / WIND_SPEED_MPS
        cp = aero_power_w / available_power_w
        result.append(f"{rpm},{tsr:.6f},{cp:.6f}")
    (ROOT / "summary.txt").write_text("\n".join(result) + "\n", encoding="ascii")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
