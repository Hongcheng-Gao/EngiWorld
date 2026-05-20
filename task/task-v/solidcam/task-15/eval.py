
from __future__ import annotations

import csv
import json
import math
import os
import re
from pathlib import Path
from typing import Any
import sys

_TASK_V_ROOT = Path(__file__).resolve().parents[2]
if str(_TASK_V_ROOT) not in sys.path:
    sys.path.insert(0, str(_TASK_V_ROOT))
from _gui_bypass import check_no_gui_bypass


SPEC = {'files': {'task-15.nc': {'min_tool_calls': 1, 'min_motion': 6, 'kind': 'nc'}}}
TARGET = Path(os.environ.get("EVAL_TARGET_DIR", r"C:\Users\User\Desktop"))
TOL = 0.5


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore").upper()


def nums(src: str, axis: str) -> list[float]:
    return [float(m.group(1)) for m in re.finditer(rf"\b{axis}([+-]?\d+(?:\.\d+)?)", src)]


def pairs(src: str) -> list[tuple[float, float]]:
    out = []
    for line in src.splitlines():
        mx = re.search(r"\bX([+-]?\d+(?:\.\d+)?)", line)
        my = re.search(r"\bY([+-]?\d+(?:\.\d+)?)", line)
        if mx and my:
            out.append((float(mx.group(1)), float(my.group(1))))
    return out


def has_num(values: list[float], expected: float) -> bool:
    return any(abs(v - float(expected)) <= TOL for v in values)


def has_pair(values: list[tuple[float, float]], expected: list[float] | tuple[float, float]) -> bool:
    ex, ey = float(expected[0]), float(expected[1])
    return any(abs(x - ex) <= 0.75 and abs(y - ey) <= 0.75 for x, y in values)


def modal_points(src: str) -> list[tuple[float, float, float]]:
    x = y = z = None
    out = []
    for line in src.splitlines():
        if not re.search(r"\bG0?0|\bG0?1|\bG0?2|\bG0?3", line):
            continue
        mx = re.search(r"\bX([+-]?\d+(?:\.\d+)?)", line)
        my = re.search(r"\bY([+-]?\d+(?:\.\d+)?)", line)
        mz = re.search(r"\bZ([+-]?\d+(?:\.\d+)?)", line)
        if mx:
            x = float(mx.group(1))
        if my:
            y = float(my.group(1))
        if mz:
            z = float(mz.group(1))
        if x is not None and y is not None and z is not None:
            out.append((x, y, z))
    return out


def rect_distance(x: float, y: float, rect: list[float]) -> float:
    x1, y1, x2, y2 = rect
    xmin, xmax = sorted((x1, x2))
    ymin, ymax = sorted((y1, y2))
    return math.hypot(max(xmin - x, 0, x - xmax), max(ymin - y, 0, y - ymax))


def motion_block_count(src: str) -> int:
    active_motion = False
    count = 0
    for line in src.splitlines():
        if re.search(r"\bG0?(?:0|1|2|3)\b|\bG8[123]\b", line):
            active_motion = True
        if active_motion and re.search(r"\b[XYZABC][+-]?\d", line):
            count += 1
    return count


def tool_call_count(src: str) -> int:
    return len(re.findall(r"\bT0*\d+\b", src))


def check_nc(path: Path, rule: dict[str, Any]) -> bool:
    src = text(path)
    if "G21" not in src or "G90" not in src or "M30" not in src:
        return False
    if len(src) < int(rule.get("min_size", 40)):
        return False
    if tool_call_count(src) < int(rule.get("min_tool_calls", 1)):
        return False
    if motion_block_count(src) < int(rule.get("min_motion", 2)):
        return False
    if rule.get("require_xy", True) and (not nums(src, "X") or not nums(src, "Y")):
        return False
    for tool in rule.get("tools", []):
        if re.search(rf"\bT0*{int(tool)}\b", src) is None:
            return False
    for spindle in rule.get("spindles", []):
        if re.search(rf"\bS{int(spindle)}\b", src) is None:
            return False
    for feed in rule.get("feeds", []):
        if re.search(rf"\bF{int(feed)}(?:\.0+)?\b", src) is None:
            return False
    zvalues = nums(src, "Z")
    for z in rule.get("z", []):
        if not has_num(zvalues, z):
            return False
    xy = pairs(src)
    for point in rule.get("points", []):
        if not has_pair(xy, point):
            return False
    for point in rule.get("forbidden_points", []):
        if has_pair(xy, point):
            return False
    for term in rule.get("terms", []):
        if str(term).upper() not in src:
            return False
    for group in rule.get("any_terms", []):
        if not any(str(term).upper() in src for term in group):
            return False
    for code in rule.get("wcs", []):
        if str(code).upper() not in src:
            return False
    if rule.get("arcs") and re.search(r"\bG0?[23]\b", src) is None:
        return False
    if rule.get("axis") and re.search(rf"\b{str(rule['axis']).upper()}[+-]?\d", src) is None:
        return False
    if rule.get("turning") and (not nums(src, "X") or not nums(src, "Z")):
        return False
    if rule.get("millturn") and (re.search(r"\bC[+-]?\d", src) is None or re.search(r"\bY[+-]?\d", src) is None):
        return False
    if rule.get("program") and str(int(rule["program"])) not in src:
        return False
    if rule.get("sequence"):
        ns = [int(m.group(1)) for m in re.finditer(r"\bN(\d+)\b", src)]
        if len(ns) < 8 or ns[0] != 10 or any((b - a) != 5 for a, b in zip(ns, ns[1:])):
            return False
    if rule.get("fixture_rects"):
        clearance = float(rule.get("min_clearance", 0))
        zlimit = float(rule.get("clearance_z_below", 1e9))
        for x, y, z in modal_points(src):
            if z < zlimit:
                for rect in rule["fixture_rects"]:
                    if rect_distance(x, y, rect) < clearance:
                        return False
    return True


def get_path(data: Any, dotted: str) -> Any:
    cur = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def equal(actual: Any, expected: Any) -> bool:
    if isinstance(expected, float) or isinstance(actual, float):
        try:
            return abs(float(actual) - float(expected)) <= 0.01
        except Exception:
            return False
    return actual == expected


def check_json(path: Path, rule: dict[str, Any]) -> bool:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("ok") is False:
        return False
    for key, expected in rule.get("expect", {}).items():
        if not equal(get_path(data, key), expected):
            return False
    for key, minimum in rule.get("min_values", {}).items():
        value = get_path(data, key)
        if value is None or float(value) < float(minimum):
            return False
    for key, length in rule.get("list_lengths", {}).items():
        value = get_path(data, key)
        if not isinstance(value, list) or len(value) != int(length):
            return False
    for name in rule.get("variants", []):
        items = data.get("variants", [])
        if not any(isinstance(item, dict) and item.get("name") == name for item in items):
            return False
    return True


def check_csv(path: Path, rule: dict[str, Any]) -> bool:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) < int(rule.get("min_rows", 1)):
        return False
    for tool in rule.get("tool_numbers", []):
        if not any(str(row.get("tool_number", "")).strip() == str(tool) for row in rows):
            return False
    for expected in rule.get("rows", []):
        if not any(all(str(row.get(k, "")).lower() == str(v).lower() for k, v in expected.items()) for row in rows):
            return False
    return True


def check_textlike(path: Path, rule: dict[str, Any], pdf: bool = False) -> bool:
    raw = path.read_bytes()
    if pdf and not raw.startswith(b"%PDF"):
        return False
    if len(raw) < (500 if pdf else 20):
        return False
    src = raw.decode("utf-8", errors="ignore").upper()
    for term in rule.get("terms", []):
        if str(term).upper() not in src:
            return False
    for term in rule.get("forbid_terms", []):
        if str(term).upper() in src:
            return False
    return True


def check_one(path: Path, rule: dict[str, Any]) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    kind = rule.get("kind")
    if kind == "nc":
        return check_nc(path, rule)
    if kind == "json":
        return check_json(path, rule)
    if kind == "csv":
        return check_csv(path, rule)
    if kind == "pdf":
        return check_textlike(path, rule, pdf=True)
    if kind == "text":
        return check_textlike(path, rule)
    return False


def main() -> bool:
    if not check_no_gui_bypass(TARGET):
        return False
    for rel, rule in SPEC["files"].items():
        if not check_one(TARGET / rel, rule):
            return False
    return True


if __name__ == "__main__":
    try:
        ok = main()
    except Exception:
        ok = False
    print("True" if ok else "False")
    raise SystemExit(0)
