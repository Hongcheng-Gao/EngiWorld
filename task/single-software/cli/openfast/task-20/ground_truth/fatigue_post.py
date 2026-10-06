#!/usr/bin/env python3
from collections import deque
from pathlib import Path
import csv

N_EQ = 1_000_000
root = Path(__file__).resolve().parent


def reversals(series):
    iterator = iter(enumerate(series))
    first_index, first = next(iterator)
    second_index, second = next(iterator)
    while second == first:
        second_index, second = next(iterator)
    yield first_index, first
    previous_slope = second - first
    current_index, current = second_index, second
    for next_index, next_value in iterator:
        slope = next_value - current
        if slope == 0:
            continue
        if previous_slope * slope < 0:
            yield current_index, current
        previous_slope = slope
        current_index, current = next_index, next_value
    yield current_index, current


def extract_cycles(series):
    points = deque()
    for point in reversals(series):
        points.append(point)
        while len(points) >= 3:
            newer = abs(points[-2][1] - points[-1][1])
            older = abs(points[-3][1] - points[-2][1])
            if newer < older:
                break
            if len(points) == 3:
                first, second = points[0], points[1]
                yield older, (first[1] + second[1]) / 2, 0.5, first[0], second[0]
                points.popleft()
            else:
                first, second = points[-3], points[-2]
                yield older, (first[1] + second[1]) / 2, 1.0, first[0], second[0]
                last = points.pop()
                points.pop()
                points.pop()
                points.append(last)
    while len(points) > 1:
        first, second = points[0], points[1]
        yield abs(first[1] - second[1]), (first[1] + second[1]) / 2, 0.5, first[0], second[0]
        points.popleft()


lines = (root / "fatigue.out").read_text(errors="replace").splitlines()
header = next(i for i, line in enumerate(lines) if line.split() and line.split()[0] == "Time")
names = lines[header].split()
indices = [names.index(name) for name in ("Time", "RootMyb1", "TwrBsMyt")]
rows = [[float(value) for value in line.split()] for line in lines[header + 2:] if line.split()]
if not rows or rows[-1][indices[0]] < 599.9:
    raise RuntimeError("incomplete 600-second OpenFAST output")
tail = [row for row in rows if row[indices[0]] >= 60.0]

all_cycles = []
dels = []
for channel, column, exponent in (("RootMyb1", indices[1], 10), ("TwrBsMyt", indices[2], 4)):
    cycles = [cycle for cycle in extract_cycles([row[column] for row in tail]) if cycle[0] > 0]
    all_cycles.extend((channel, *cycle) for cycle in cycles)
    dels.append((sum(count * load_range ** exponent for load_range, _, count, _, _ in cycles) / N_EQ) ** (1 / exponent))

with (root / "cycles.csv").open("w", newline="") as handle:
    writer = csv.writer(handle)
    writer.writerow(("channel", "range_knm", "mean_knm", "count", "start_index", "end_index"))
    writer.writerows(all_cycles)
(root / "summary.txt").write_text(f"{dels[0]:.6f}, {dels[1] / 1000:.6f}\n")
