from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path

SPEC = {'required': ['task-10.gcode'], 'tools': [1], 'z': [0.0], 'bbox': [-90, 90, -50, 50], 'holes': [[-70, -30], [-70, 30], [70, -30], [70, 30]], 'ops': ['inner profile', 'outer profile', '0.15']}
TARGET = Path(os.environ.get("NX_CAM_TARGET", r"C:\Users\User\Desktop"))
TOL = 0.35


def fail() -> None:
    print(False)
    raise SystemExit(0)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def parse_words(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def axis_words(line: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for axis, value in re.findall(r"\b([XYZABCF])\s*(-?\d+(?:\.\d+)?)", line.upper()):
        out[axis] = float(value)
    return out


def motions(text: str) -> list[dict[str, float]]:
    return [vals for vals in (axis_words(line) for line in text.splitlines()) if vals]


def close(a: float, b: float, tol: float = TOL) -> bool:
    return abs(a - b) <= tol


def has_axis(moves: list[dict[str, float]], axis: str, value: float, tol: float = TOL) -> bool:
    return any(axis in move and close(move[axis], value, tol) for move in moves)


def has_xy(moves: list[dict[str, float]], x: float, y: float, tol: float = TOL) -> bool:
    return any("X" in move and "Y" in move and close(move["X"], x, tol) and close(move["Y"], y, tol) for move in moves)


def bbox_present(moves: list[dict[str, float]], bbox: list[float]) -> bool:
    xs = [move["X"] for move in moves if "X" in move]
    ys = [move["Y"] for move in moves if "Y" in move]
    if not xs or not ys:
        return False
    xmin, xmax, ymin, ymax = bbox
    return min(xs) <= xmin + TOL and max(xs) >= xmax - TOL and min(ys) <= ymin + TOL and max(ys) >= ymax - TOL


def check_nc(path: Path) -> bool:
    text = read_text(path).upper()
    compact = parse_words(text)
    if "G21" not in text or "G90" not in text or "M30" not in text:
        return False
    for tool in SPEC.get("tools", []):
        if re.search(rf"\bT\s*{int(tool)}\b", text) is None:
            return False
    for spindle in SPEC.get("spindles", []):
        if re.search(rf"\bS\s*{int(spindle)}\b", text) is None:
            return False
    for feed in SPEC.get("feeds", []):
        if re.search(rf"\bF\s*{int(feed)}\b", text) is None:
            return False
    for phrase in SPEC.get("ops", []):
        if phrase.lower() not in compact:
            return False
    for wcs in SPEC.get("wcs", []):
        if str(wcs).upper() not in text:
            return False
    moves = motions(text)
    for z in SPEC.get("z", []):
        if not has_axis(moves, "Z", float(z)):
            return False
    if "bbox" in SPEC and not bbox_present(moves, SPEC["bbox"]):
        return False
    for x, y in SPEC.get("holes", []):
        if not has_xy(moves, float(x), float(y)):
            return False
    for x, y in SPEC.get("side_a_holes", []):
        if path.name.lower().endswith("sidea.nc") and not has_xy(moves, float(x), float(y)):
            return False
    for x, y in SPEC.get("side_b_holes", []):
        if path.name.lower().endswith("sideb.nc") and not has_xy(moves, float(x), float(y)):
            return False
    for x, y in SPEC.get("skipped", []):
        if has_xy(moves, float(x), float(y)):
            return False
    if SPEC.get("arcs") and re.search(r"\bG0?[23]\b", text) is None:
        return False
    rotary = SPEC.get("rotary")
    if rotary:
        axis = str(rotary).upper()
        values = [move[axis] for move in moves if axis in move]
        if len(values) < 8 or max(values) - min(values) < 180:
            return False
    if SPEC.get("turning"):
        if not any("X" in move and "Z" in move for move in moves):
            return False
    if SPEC.get("millturn"):
        if " C" not in text and " Y" not in text:
            return False
    sequence = SPEC.get("sequence")
    if sequence:
        nums = [int(m.group(1)) for m in re.finditer(r"\bN(\d+)\b", text)]
        if len(nums) < int(sequence.get("minimum", 10)) or nums[0] != int(sequence["start"]):
            return False
        inc = int(sequence["increment"])
        if any((b - a) != inc for a, b in zip(nums, nums[1:])):
            return False
    program = SPEC.get("program")
    if program and re.search(rf"\bO\s*{int(program)}\b", text) is None:
        return False
    variants = SPEC.get("variants", [])
    if variants and path.suffix.lower() in {".nc", ".gcode"}:
        match = next((v for v in variants if path.stem.lower() == v["name"].lower()), None)
        if match:
            if not has_axis(moves, "Z", float(match["z"])):
                return False
            if re.search(rf"\bO\s*{int(match['program'])}\b", text) is None:
                return False
    return True


def get_path_value(data: object, key: str) -> object:
    if isinstance(data, dict) and key in data:
        return data[key]
    if isinstance(data, dict):
        for value in data.values():
            found = get_path_value(value, key)
            if found is not None:
                return found
    if isinstance(data, list):
        for value in data:
            found = get_path_value(value, key)
            if found is not None:
                return found
    return None


def check_json_file(path: Path, expected: dict) -> bool:
    data = json.loads(read_text(path))
    if not isinstance(data, dict) or data.get("ok") is False:
        return False
    for key, value in expected.items():
        actual = get_path_value(data, key)
        if actual != value:
            return False
    if expected.get("holes_from_csv"):
        holes = data.get("holes")
        return isinstance(holes, list) and len(holes) == 10
    return True


def check_csv_file(path: Path) -> bool:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return False
    tools = {str(t) for t in SPEC.get("tools", [])}
    tool_cols = ["tool_number", "tool", "tool_id"]
    present = set()
    for row in rows:
        for col in tool_cols:
            if row.get(col):
                present.add(str(row[col]).strip())
    if present and not tools.issubset(present):
        return False
    batch = SPEC.get("batch")
    if batch:
        files = {row.get("file", "").strip() for row in rows}
        return set(batch).issubset(files)
    return True


def check_text_file(path: Path) -> bool:
    text = read_text(path).lower()
    return path.stat().st_size > 50 and "error" not in text and "failed" not in text


def check_pdf(path: Path) -> bool:
    return path.stat().st_size > 100 and path.read_bytes()[:4] == b"%PDF"


def main() -> bool:
    required = SPEC["required"]
    for rel in required:
        path = TARGET / rel
        if not path.exists() or path.stat().st_size == 0:
            return False
        ext = path.suffix.lower()
        if ext in {".nc", ".gcode"} and not check_nc(path):
            return False
        if ext == ".json":
            expected = SPEC.get("json", {}).get(rel, {})
            if not check_json_file(path, expected):
                return False
        if ext == ".csv" and not check_csv_file(path):
            return False
        if ext in {".txt", ".log"} and not check_text_file(path):
            return False
        if ext == ".pdf" and not check_pdf(path):
            return False
    return True


if __name__ == "__main__":
    try:
        print(True if main() else False)
    except Exception:
        print(False)
