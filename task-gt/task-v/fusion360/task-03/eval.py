from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

REQUIRED = ['task-3.nc']
CFG = {'tools': [1, 2], 'spindles': [8000, 5000], 'feeds': [250, 180], 'holes': [(25, 15), (25, -15), (-25, 15), (-25, -15)], 'z': [-1.0]}
TASK_NUM = 3
CHANNEL = 'v'
ROOT = Path(__file__).resolve().parent
TARGET = Path(r"C:\Users\Administrator\Desktop")

def fail() -> None:
    print("False")
    raise SystemExit(0)

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def check_nc(path: Path) -> bool:
    text = read_text(path).upper()
    if "G21" not in text or "G90" not in text or "M30" not in text:
        return False
    lower = text.lower()
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
    if CFG.get("rotary") and re.search(r"\b[ABC]-?\d", text) is None:
        return False
    if CFG.get("sequence"):
        nums = [int(m.group(1)) for m in re.finditer(r"\bN(\d+)\b", text)]
        if len(nums) < 20 or nums[0] != 10 or any((b - a) != 5 for a, b in zip(nums, nums[1:])):
            return False
    for op in CFG.get("ops", []):
        if str(op).lower() not in lower:
            return False
    for z in CFG.get("z", []):
        if f"Z{float(z):.3f}" not in text:
            return False
    for x, y in CFG.get("holes", []):
        if (x, y) in CFG.get("skipped", []):
            continue
        if f"X{float(x):.3f}" not in text or f"Y{float(y):.3f}" not in text:
            return False
    if CFG.get("setups") == 2:
        marker = "WCS_Z_DIRECTION 0 0 -1" if "SIDEB" in path.name.upper() else "WCS_Z_DIRECTION 0 0 1"
        if marker not in text:
            return False
    return True

def check_html(path: Path) -> bool:
    text = read_text(path).lower()
    return all(word in text for word in ["setup", "wcs", "tool", "operation"]) and path.stat().st_size > 1000

def check_csv(path: Path) -> bool:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return bool(rows)

def check_json(path: Path) -> bool:
    data = json.loads(read_text(path))
    if not isinstance(data, dict):
        return False
    if data.get("ok") is False:
        return False
    if CFG.get("all_checks_pass") and data.get("all_checks_pass") is not True:
        return False
    for key in ("hole_count", "setup_count", "selected_tool_count", "blade_count"):
        if key in CFG and data.get(key) != CFG[key]:
            return False
    if "hole_groups" in CFG:
        for key, value in CFG["hole_groups"].items():
            if data.get(key) != value:
                return False
    return True

def check_png(path: Path) -> bool:
    data = path.read_bytes()
    return data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) > 10000

def check_text(path: Path) -> bool:
    text = read_text(path).lower()
    return path.stat().st_size > 50 and "error" not in text and "failed" not in text

def main() -> bool:
    for rel in REQUIRED:
        path = TARGET / rel
        if not path.exists() or path.stat().st_size == 0:
            return False
        ext = path.suffix.lower()
        if ext in {".nc", ".gcode"} and not check_nc(path):
            return False
        if ext == ".html" and not check_html(path):
            return False
        if ext == ".csv" and not check_csv(path):
            return False
        if ext == ".json" and not check_json(path):
            return False
        if ext == ".png" and not check_png(path):
            return False
        if ext in {".txt", ".log"} and not check_text(path):
            return False
    return True

if __name__ == "__main__":
    try:
        result = main()
    except Exception:
        result = False
    print("True" if result else "False")
    raise SystemExit(0)
