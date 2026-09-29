#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parent
result = []
for angle in (0, 5, 10, 15, 20):
    lines = (root / f"case_yaw_{angle}.out").read_text(errors="replace").splitlines()
    header = next(i for i, line in enumerate(lines) if line.split() and line.split()[0] == "Time")
    names = lines[header].split()
    ti, pi = names.index("Time"), names.index("GenPwr")
    rows = [[float(value) for value in line.split()] for line in lines[header + 2:] if line.split()]
    tail = [row for row in rows if row[ti] >= 50.0]
    result.append((angle, sum(row[pi] for row in tail) / len(tail)))
(root / "summary.txt").write_text("\n".join(f"{angle}, {power:.6f}" for angle, power in result) + "\n")
