#!/usr/bin/env python3
from pathlib import Path
import math

root = Path(__file__).resolve().parent
lines = (root / "case_turb.out").read_text(errors="replace").splitlines()
header = next(i for i, line in enumerate(lines) if line.split() and line.split()[0] == "Time")
names = lines[header].split()
time_i = names.index("Time")
power_i = names.index("GenPwr")
rows = [[float(value) for value in line.split()] for line in lines[header + 2:] if line.split()]
if not rows or rows[-1][time_i] < 59.9:
    raise RuntimeError("incomplete OpenFAST output")
power = [row[power_i] for row in rows]
mean = sum(power) / len(power)
std = math.sqrt(sum((value - mean) ** 2 for value in power) / len(power))
(root / "summary.txt").write_text(f"{mean:.6f}, {std:.6f}\n")
