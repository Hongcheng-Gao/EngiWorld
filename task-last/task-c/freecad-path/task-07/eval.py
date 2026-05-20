from __future__ import annotations

import csv
import json
import re
from pathlib import Path

VARIANTS = [
    {"name": "variant_01", "pocket_size": [34, 16], "bottom_z": 7.5, "tool_diameter": 7, "program": 2701},
    {"name": "variant_02", "pocket_size": [38, 18], "bottom_z": 7.0, "tool_diameter": 8, "program": 2702},
    {"name": "variant_03", "pocket_size": [42, 20], "bottom_z": 6.5, "tool_diameter": 9, "program": 2703},
    {"name": "variant_04", "pocket_size": [46, 22], "bottom_z": 6.0, "tool_diameter": 10, "program": 2704},
    {"name": "variant_05", "pocket_size": [50, 24], "bottom_z": 5.5, "tool_diameter": 11, "program": 2705},
]
REQUIRED = [f"{variant['name']}.nc" for variant in VARIANTS]
VARIANT_BY_FILE = {f"{variant['name']}.nc": variant for variant in VARIANTS}
CFG = {"tools": [1], "ops": ["Job", "Pocket Shape"]}
ROOT = Path(__file__).resolve().parent
TARGET = Path("/home/user/Desktop")

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def axis_words(line: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for axis, value in re.findall(r"\b([XYZ])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))", line.upper()):
        out[axis] = float(value)
    return out


def motions(text: str) -> list[dict[str, float]]:
    return [vals for vals in (axis_words(line) for line in text.splitlines()) if vals]


def has_axis(moves: list[dict[str, float]], axis: str, value: float, tol: float = 0.35) -> bool:
    return any(axis in move and abs(move[axis] - value) <= tol for move in moves)


def bbox_present(moves: list[dict[str, float]], pocket_size: list[float]) -> bool:
    xs = [move["X"] for move in moves if "X" in move]
    ys = [move["Y"] for move in moves if "Y" in move]
    if not xs or not ys:
        return False
    half_x = float(pocket_size[0]) / 2.0
    half_y = float(pocket_size[1]) / 2.0
    return min(xs) <= -half_x + 0.35 and max(xs) >= half_x - 0.35 and min(ys) <= -half_y + 0.35 and max(ys) >= half_y - 0.35


def check_nc(path: Path) -> bool:
    text = read_text(path).upper()
    if "G21" not in text or "G90" not in text or "M30" not in text:
        return False
    for tool in CFG.get("tools", []):
        if f"T{tool}" not in text:
            return False
    for spindle in CFG.get("spindles", []):
        if f"S{int(spindle)}" not in text:
            return False
    for feed in CFG.get("feeds", []):
        if f"F{int(feed)}" not in text:
            return False
    for wcs in CFG.get("wcs", []):
        if str(wcs).upper() not in text:
            return False
    for op in CFG.get("ops", []):
        if str(op).upper() not in text:
            return False
    variant = VARIANT_BY_FILE.get(path.name)
    if variant is None:
        return False
    if re.search(rf"\bO\s*{int(variant['program'])}\b", text) is None:
        return False
    if re.search(rf"TOOL\s*DIAMETER\s*{float(variant['tool_diameter']):g}\b", text) is None:
        return False
    moves = motions(text)
    if not has_axis(moves, "Z", float(variant["bottom_z"])):
        return False
    if not bbox_present(moves, variant["pocket_size"]):
        return False
    if CFG.get("sequence"):
        nums = [int(m.group(1)) for m in re.finditer(r"\bN(\d+)\b", text)]
        if len(nums) < 20 or nums[0] != 10 or any((b - a) != 5 for a, b in zip(nums, nums[1:])):
            return False
    if path.suffix.lower() == ".gcode" and path.stat().st_size < 3000:
        return False
    return True






def main() -> bool:
    for rel in REQUIRED:
        path = TARGET / rel
        if not path.exists() or path.stat().st_size == 0:
            return False
        ext = path.suffix.lower()
        if ext in {".nc", ".gcode"} and not check_nc(path):
            return False
    return True

if __name__ == "__main__":
    try:
        ok = main()
    except Exception:
        ok = False
    print(True if ok else False)
