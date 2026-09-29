#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parent
result = []
for speed in (4, 8, 11, 15, 20):
    lines = (root / f"case_ws{speed}.out").read_text(errors="replace").splitlines()
    header = next(i for i, line in enumerate(lines) if line.split() and line.split()[0] == "Time")
    names = lines[header].split()
    indices = [names.index(name) for name in ("Time", "GenPwr", "RotSpeed", "BldPitch1")]
    rows = [[float(value) for value in line.split()] for line in lines[header + 2:] if line.split()]
    tail = [row for row in rows if row[indices[0]] >= 50.0]
    means = [sum(row[index] for row in tail) / len(tail) for index in indices[1:]]
    result.append((speed, *means))
(root / "summary.txt").write_text("\n".join(f"{ws}, {power:.6f}, {rpm:.6f}, {pitch:.6f}" for ws, power, rpm, pitch in result) + "\n")
