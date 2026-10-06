#!/usr/bin/env python3
from __future__ import annotations

import math
from collections import deque
from pathlib import Path


ROOT = Path("/home/user/Desktop")
M = 4.0
N_EQ = 50.0


def reversals(series: list[float]) -> list[float]:
    cleaned = [series[0]]
    for value in series[1:]:
        if value != cleaned[-1]:
            cleaned.append(value)
    points = [cleaned[0]]
    for index in range(1, len(cleaned) - 1):
        left = cleaned[index] - cleaned[index - 1]
        right = cleaned[index + 1] - cleaned[index]
        if left * right <= 0.0:
            points.append(cleaned[index])
    points.append(cleaned[-1])
    return points


def rainflow_ranges(series: list[float]) -> list[tuple[float, float]]:
    stack: deque[float] = deque()
    cycles: list[tuple[float, float]] = []
    for point in reversals(series):
        stack.append(point)
        while len(stack) >= 3:
            newer = abs(stack[-1] - stack[-2])
            older = abs(stack[-2] - stack[-3])
            if newer < older:
                break
            if len(stack) == 3:
                cycles.append((older, 0.5))
                stack.popleft()
            else:
                cycles.append((older, 1.0))
                last = stack.pop()
                stack.pop()
                stack.pop()
                stack.append(last)
    while len(stack) > 1:
        first = stack.popleft()
        cycles.append((abs(stack[0] - first), 0.5))
    return cycles


def main() -> None:
    lines = (ROOT / "drivetrain_case.out").read_text(encoding="utf-8", errors="ignore").splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.split()[:1] == ["Time"])
    headers = lines[header_index].split()
    units = lines[header_index + 1].split()
    time_i = headers.index("Time")
    torque_i = headers.index("RotTorq")
    if units[torque_i] != "(kN-m)":
        raise ValueError("unexpected rotor-torque units")
    torque_mnm: list[float] = []
    for line in lines[header_index + 2 :]:
        fields = line.split()
        if len(fields) != len(headers):
            continue
        try:
            row = [float(value) for value in fields]
        except ValueError:
            continue
        if row[time_i] >= 10.0:
            torque_mnm.append(row[torque_i] / 1000.0)
    if len(torque_mnm) < 490:
        raise ValueError("insufficient samples after transient")
    mean = sum(torque_mnm) / len(torque_mnm)
    std = math.sqrt(sum((value - mean) ** 2 for value in torque_mnm) / len(torque_mnm))
    cycles = rainflow_ranges(torque_mnm)
    damage_sum = sum(count * load_range**M for load_range, count in cycles)
    damage_equivalent = (damage_sum / N_EQ) ** (1.0 / M)
    (ROOT / "summary.txt").write_text(
        f"{mean:.6f},{std:.6f},{damage_equivalent:.6f}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
