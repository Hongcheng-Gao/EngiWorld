#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parent
rows = []
for speed in (4, 8, 11, 15, 20):
    lines = (root / f"case_ws{speed}.out").read_text(errors="replace").splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.split() and line.split()[0] == "Time")
    names = lines[header_index].split()
    time_i, power_i, rpm_i = (names.index(name) for name in ("Time", "GenPwr", "RotSpeed"))
    data = [[float(value) for value in line.split()] for line in lines[header_index + 2:] if line.split()]
    tail = [row for row in data if row[time_i] >= 50.0]
    rows.append((speed, sum(row[power_i] for row in tail) / len(tail), sum(row[rpm_i] for row in tail) / len(tail)))

(root / "summary.txt").write_text("# ws, genpwr_kw, rotspeed_rpm\n" + "\n".join(f"{ws}, {pwr:.6f}, {rpm:.6f}" for ws, pwr, rpm in rows) + "\n")
