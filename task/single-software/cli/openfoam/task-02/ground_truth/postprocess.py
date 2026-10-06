#!/usr/bin/env python3
from __future__ import annotations

import math
import re
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "cavity"


def vectors(path: Path) -> list[tuple[float, float, float]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(
        r"internalField\s+nonuniform\s+List<vector>\s+\d+\s*\((.*?)\)\s*;",
        text,
        re.S,
    )
    if not match:
        raise ValueError(f"nonuniform vector field not found in {path}")
    return [
        tuple(float(value) for value in item.split())
        for item in re.findall(r"\(([^()]+)\)", match.group(1))
    ]


times = sorted(
    (float(path.name), path)
    for path in CASE.iterdir()
    if path.is_dir() and re.fullmatch(r"\d+(?:\.\d+)?", path.name)
)
if not times or times[-1][0] < 30.0:
    raise RuntimeError("the 30 s solution is missing")

latest = times[-1][1]
centres = vectors(latest / "C")
velocity = vectors(latest / "U")
if len(centres) != len(velocity):
    raise RuntimeError("cell-centre and velocity lengths differ")


def nearest(point: tuple[float, float, float], count: int = 4) -> tuple[float, float, float]:
    indices = sorted(
        range(len(centres)),
        key=lambda i: sum((centres[i][j] - point[j]) ** 2 for j in range(3)),
    )[:count]
    return tuple(sum(velocity[i][j] for i in indices) / len(indices) for j in range(3))


center = nearest((0.5, 0.5, 0.005))
left = nearest((0.25, 0.5, 0.005))
right = nearest((0.75, 0.5, 0.005))
if not all(math.isfinite(value) for value in (*center, *left, *right)):
    raise RuntimeError("non-finite velocity")

(ROOT / "center_velocity.csv").write_text(
    "location,ux_mps,uy_mps,uz_mps\n"
    f"center,{center[0]:.9f},{center[1]:.9f},{center[2]:.9f}\n"
    f"left_mid,{left[0]:.9f},{left[1]:.9f},{left[2]:.9f}\n"
    f"right_mid,{right[0]:.9f},{right[1]:.9f},{right[2]:.9f}\n",
    encoding="utf-8",
)
(ROOT / "summary.txt").write_text(f"{center[0]:.9f}\n", encoding="utf-8")
