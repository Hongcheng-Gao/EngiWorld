from __future__ import annotations

import os
import re
from pathlib import Path

SPEC = {'required': ['task-36_B.nc'], 'tools': [1, 2]}
TARGET = Path(os.environ.get("NX_CAM_TARGET", r"C:\Users\User\Desktop"))
TOL = 0.35


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def axis_words(line: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for axis, value in re.findall(r"\b([XYZABCFIJK])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))", line.upper()):
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


def check_nc(path: Path, rel: str) -> bool:
    text = read_text(path).upper()
    if "G20" in text:
        return False
    if re.search(r"\bM\s*(?:2|30)\b", text) is None:
        return False

    tools_seen = {int(m.group(1)) for m in re.finditer(r"\bT\s*0*(\d+)\b", text)}
    for tool in SPEC.get("tools", []):
        if int(tool) not in tools_seen:
            return False
    if SPEC.get("forbid_extra_tools") and not tools_seen.issubset({int(t) for t in SPEC.get("tools", [])}):
        return False

    for spindle in SPEC.get("spindles", []):
        if re.search(rf"\bS\s*{int(spindle)}\b", text) is None:
            return False
    for feed in SPEC.get("feeds", []):
        if re.search(rf"\bF\s*{int(feed)}\b", text) is None:
            return False
    for wcs in SPEC.get("wcs", []):
        if str(wcs).upper() not in text:
            return False

    moves = motions(text)
    for z in SPEC.get("z", []):
        if not has_axis(moves, "Z", float(z)):
            return False

    bbox = SPEC.get("file_bboxes", {}).get(rel, SPEC.get("bbox"))
    if bbox is not None and not bbox_present(moves, bbox):
        return False

    for x, y in SPEC.get("holes", []):
        if not has_xy(moves, float(x), float(y)):
            return False
    lower_name = path.name.lower()
    for x, y in SPEC.get("side_a_holes", []):
        if lower_name.endswith("sidea.nc") and not has_xy(moves, float(x), float(y)):
            return False
    for x, y in SPEC.get("side_b_holes", []):
        if lower_name.endswith("sideb.nc") and not has_xy(moves, float(x), float(y)):
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

    if SPEC.get("turning") and not any("X" in move and "Z" in move for move in moves):
        return False
    if SPEC.get("millturn") and not any("C" in move or "Y" in move for move in moves):
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

    for variant in SPEC.get("variants", []):
        if path.stem.lower() == variant["name"].lower():
            if not has_axis(moves, "Z", float(variant["z"])):
                return False
            if re.search(rf"\bO\s*{int(variant['program'])}\b", text) is None:
                return False
            pocket = variant.get("pocket")
            if pocket and not bbox_present(moves, [-float(pocket[0]) / 2, float(pocket[0]) / 2, -float(pocket[1]) / 2, float(pocket[1]) / 2]):
                return False
    return True


def main() -> bool:
    for rel in SPEC["required"]:
        path = TARGET / rel
        if not path.exists() or path.stat().st_size == 0:
            return False
        if path.suffix.lower() not in {".nc", ".gcode"}:
            return False
        if not check_nc(path, rel):
            return False
    return True


if __name__ == "__main__":
    print(main())
