#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "cylinder_snappy"


def latest_time() -> Path:
    times = [
        path
        for path in CASE.iterdir()
        if path.is_dir() and re.fullmatch(r"\d+(?:\.\d+)?", path.name) and float(path.name) > 0
    ]
    if not times:
        raise FileNotFoundError("no computed time directory")
    return max(times, key=lambda path: float(path.name))


def patch_values(path: Path, patch: str) -> list[float]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    block = re.search(rf"\b{re.escape(patch)}\s*\{{(.*?)\n\s*\}}", text, re.S)
    if not block:
        raise ValueError(f"missing {patch} boundary field")
    values = re.search(
        r"value\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)\s*;",
        block.group(1),
        re.S,
    )
    if not values:
        raise ValueError(f"missing nonuniform values on {patch}")
    result = [float(value) for value in values.group(2).split()]
    if len(result) != int(values.group(1)):
        raise ValueError("yPlus face-count mismatch")
    return result


values = patch_values(latest_time() / "yPlus", "cylinder")
if len(values) < 100 or any(value < 0 for value in values):
    raise RuntimeError("invalid cylinder yPlus field")
average = sum(values) / len(values)

with (ROOT / "yplus_surface.csv").open("w", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(("face_index", "yplus"))
    for index, value in enumerate(values):
        writer.writerow((index, f"{value:.10g}"))

(ROOT / "summary.txt").write_text(f"{average:.9f}\n", encoding="utf-8")
print(
    f"avg_yplus={average:.9f} min_yplus={min(values):.9f} "
    f"max_yplus={max(values):.9f} faces={len(values)}"
)
