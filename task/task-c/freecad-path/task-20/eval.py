from __future__ import annotations

import csv
import json
import re
from pathlib import Path

REQUIRED = ['task-20.nc', 'post_log.txt']
CFG = {'tools': [1, 2, 3, 4, 5], 'ops': ['Job', 'Face', 'Pocket', 'Drilling', 'Counterbore', 'Surface', 'Profile'], 'hole_count': 18, 'pocket_count': 3, 'fixture_clearance': 3.0, 'all_checks_pass': True}
ROOT = Path(__file__).resolve().parent
TARGET = Path("/home/user/Desktop")

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

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
    if CFG.get("sequence"):
        nums = [int(m.group(1)) for m in re.finditer(r"\bN(\d+)\b", text)]
        if len(nums) < 20 or nums[0] != 10 or any((b - a) != 5 for a, b in zip(nums, nums[1:])):
            return False
    if path.suffix.lower() == ".gcode" and path.stat().st_size < 3000:
        return False
    return True





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
        if ext in {".txt", ".log"} and not check_text(path):
            return False
    return True

if __name__ == "__main__":
    try:
        ok = main()
    except Exception:
        ok = False
    print(True if ok else False)
