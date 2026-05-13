from __future__ import annotations

import os
import re
from pathlib import Path

TARGET = Path(os.environ.get("EVAL_TARGET_DIR", r"C:\Users\User\Desktop"))
REQUIRED = "task-1.nc"
TOL = 0.35


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore").upper()


def axis_values(text: str, axis: str) -> list[float]:
    return [
        float(match.group(1))
        for match in re.finditer(rf"\b{axis}([+-]?\d+(?:\.\d+)?)", text)
    ]


def xy_points(text: str) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for line in text.splitlines():
        mx = re.search(r"\bX([+-]?\d+(?:\.\d+)?)", line)
        my = re.search(r"\bY([+-]?\d+(?:\.\d+)?)", line)
        if mx and my:
            points.append((float(mx.group(1)), float(my.group(1))))
    return points


def has_value(values: list[float], expected: float) -> bool:
    return any(abs(value - expected) <= TOL for value in values)


def has_point(points: list[tuple[float, float]], expected: tuple[float, float]) -> bool:
    ex, ey = expected
    return any(abs(x - ex) <= TOL and abs(y - ey) <= TOL for x, y in points)


def check_nc(path: Path) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    text = read_text(path)
    if "G21" not in text or "G90" not in text or "M30" not in text:
        return False
    if re.search(r"\bT0*1\b", text) is None:
        return False
    if re.search(r"\bS6000\b", text) is None:
        return False
    if re.search(r"\bF800(?:\.0+)?\b", text) is None:
        return False
    if not has_value(axis_values(text, "Z"), 12.0):
        return False
    points = xy_points(text)
    for point in [(-50.0, -30.0), (50.0, -30.0), (50.0, 30.0), (-50.0, 30.0)]:
        if not has_point(points, point):
            return False
    return True


if __name__ == "__main__":
    try:
        ok = check_nc(TARGET / REQUIRED)
    except Exception:
        ok = False
    print("true" if ok else "false")
    raise SystemExit(0)
