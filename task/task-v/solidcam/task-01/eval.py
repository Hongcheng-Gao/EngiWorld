from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from pathlib import Path


DEFAULT_TARGET = r"C:\Users\User\Desktop"
TARGET = Path(os.environ.get("EVAL_TARGET_DIR", os.environ.get("OUTPUT_ROOT", DEFAULT_TARGET)))
OUTPUT_NAME = "task-1.nc"

STOCK_X = 104.0
STOCK_Y = 64.0
FINISH_Z = -1.0
Z_TOL = 0.15
MAX_INSTALLED_TOOL_DIAMETER_MM = 50.0

WORD_RE = re.compile(r"([A-Z])([+-]?(?:\d+(?:\.\d*)?|\.\d+))", re.I)
PAREN_COMMENT_RE = re.compile(r"\(([^)]*)\)")
FORBIDDEN_CODES = {"G10", "G51", "G52", "G68", "G69", "G92", "M98", "M99"}


@dataclass
class Record:
    line: int
    motion: int
    start: tuple[float | None, float | None, float | None]
    end: tuple[float | None, float | None, float | None]
    explicit: dict[str, float]
    ij: tuple[float | None, float | None]
    radius: float | None
    tool: int | None
    wcs: str | None
    feed: float | None
    spindle_on: bool
    speed: float | None
    length_comp: bool
    h: int | None
    plane: int
    safe_home_before: bool


def split_block(raw: str) -> tuple[str, list[str]]:
    comments = PAREN_COMMENT_RE.findall(raw)
    code = PAREN_COMMENT_RE.sub(" ", raw)
    if ";" in code:
        code, tail = code.split(";", 1)
        comments.append(tail)
    return code.upper(), comments


def close(a: float, b: float, tol: float) -> bool:
    return abs(float(a) - float(b)) <= tol


def parse_nc(source: str):
    records: list[Record] = []
    comments: list[str] = []
    errors: list[str] = []
    state = {
        "unit": 1.0,
        "absolute": True,
        "motion": None,
        "plane": 17,
        "x": None,
        "y": None,
        "z": None,
        "pending_tool": None,
        "tool": None,
        "wcs": None,
        "feed": None,
        "speed": None,
        "spindle_on": False,
        "length_comp": False,
        "h": None,
        "safe_home": False,
    }
    tool_changes: list[int] = []
    m30_lines: list[int] = []
    after_m30 = False

    for line_number, raw in enumerate(source.splitlines(), 1):
        code, block_comments = split_block(raw)
        comments.extend(block_comments)
        stripped = code.strip()
        if not stripped or stripped == "%":
            continue
        if after_m30:
            residue = re.sub(r"\bN\d+(?:\.\d+)?\b", " ", stripped).strip()
            if residue and residue != "%":
                errors.append(f"executable content after M30 at line {line_number}")
            continue
        if any(mark in code for mark in ("#", "[", "]")):
            errors.append(f"macro syntax at line {line_number}")

        words = [(letter.upper(), float(number)) for letter, number in WORD_RE.findall(code)]
        g_values = [number for letter, number in words if letter == "G"]
        m_values = [int(round(number)) for letter, number in words if letter == "M" and close(number, round(number), 1e-9)]
        normalized_codes = {f"G{int(round(value))}" for value in g_values if close(value, round(value), 1e-9)}
        normalized_codes.update(f"M{value}" for value in m_values)
        if normalized_codes & FORBIDDEN_CODES:
            errors.append(f"unsupported transform/subprogram at line {line_number}")
        if any(81 <= int(round(value)) <= 89 for value in g_values if close(value, round(value), 1e-9)):
            errors.append(f"drilling cycle at line {line_number}")
        if any(letter in {"A", "B", "C"} for letter, _ in words):
            errors.append(f"rotary-axis motion at line {line_number}")

        if any(close(value, 20.0, 1e-9) for value in g_values):
            state["unit"] = 25.4
        if any(close(value, 21.0, 1e-9) for value in g_values):
            state["unit"] = 1.0
        if any(close(value, 90.0, 1e-9) for value in g_values):
            state["absolute"] = True
        if any(close(value, 91.0, 1e-9) for value in g_values):
            state["absolute"] = False
        for plane in (17, 18, 19):
            if any(close(value, float(plane), 1e-9) for value in g_values):
                state["plane"] = plane
        for value in g_values:
            if close(value, round(value), 1e-9) and int(round(value)) in {0, 1, 2, 3}:
                state["motion"] = int(round(value))
        for value in g_values:
            if close(value, round(value), 1e-9) and 54 <= int(round(value)) <= 59:
                state["wcs"] = f"G{int(round(value))}"

        t_words = [int(round(value)) for letter, value in words if letter == "T" and value > 0 and close(value, round(value), 1e-9)]
        if t_words:
            state["pending_tool"] = t_words[-1]
        s_words = [value for letter, value in words if letter == "S"]
        if s_words:
            state["speed"] = s_words[-1]
        f_words = [value * state["unit"] for letter, value in words if letter == "F"]
        if f_words:
            state["feed"] = f_words[-1]
        h_words = [int(round(value)) for letter, value in words if letter == "H" and value > 0 and close(value, round(value), 1e-9)]
        if h_words:
            state["h"] = h_words[-1]
        if 6 in m_values:
            if state["pending_tool"] is None:
                errors.append(f"M6 without a positive T word at line {line_number}")
            else:
                state["tool"] = state["pending_tool"]
                tool_changes.append(state["tool"])
            state["length_comp"] = False
            state["h"] = None
        if 3 in m_values or 4 in m_values:
            state["spindle_on"] = True
        if 5 in m_values:
            state["spindle_on"] = False
        if any(close(value, 43.0, 1e-9) or close(value, 43.4, 1e-9) for value in g_values):
            state["length_comp"] = True
        if any(close(value, 49.0, 1e-9) for value in g_values):
            state["length_comp"] = False

        is_g28 = any(close(value, 28.0, 1e-9) for value in g_values)
        is_g53 = any(close(value, 53.0, 1e-9) for value in g_values)
        axis_words: dict[str, float] = {}
        for letter, value in words:
            if letter in {"X", "Y", "Z", "I", "J", "R"}:
                axis_words[letter.lower()] = value * state["unit"]
        has_xyz = any(axis in axis_words for axis in ("x", "y", "z"))
        if is_g28:
            state["safe_home"] = True
        elif has_xyz and state["motion"] is not None and not is_g53:
            start = (state["x"], state["y"], state["z"])
            end_values = [state["x"], state["y"], state["z"]]
            for index, axis in enumerate(("x", "y", "z")):
                if axis not in axis_words:
                    continue
                value = axis_words[axis]
                if state["absolute"]:
                    end_values[index] = value
                elif end_values[index] is None:
                    if not close(value, 0.0, 1e-12):
                        errors.append(f"incremental move from unknown {axis.upper()} at line {line_number}")
                else:
                    end_values[index] += value
            record = Record(
                line=line_number,
                motion=int(state["motion"]),
                start=start,
                end=tuple(end_values),
                explicit=axis_words,
                ij=(axis_words.get("i"), axis_words.get("j")),
                radius=axis_words.get("r"),
                tool=state["tool"],
                wcs=state["wcs"],
                feed=state["feed"],
                spindle_on=bool(state["spindle_on"]),
                speed=state["speed"],
                length_comp=bool(state["length_comp"]),
                h=state["h"],
                plane=int(state["plane"]),
                safe_home_before=bool(state["safe_home"]),
            )
            records.append(record)
            state["x"], state["y"], state["z"] = end_values
            state["safe_home"] = False
        if 30 in m_values:
            m30_lines.append(line_number)
            after_m30 = True

    return records, comments, tool_changes, m30_lines, errors


def xy_changed(record: Record) -> bool:
    sx, sy, _ = record.start
    ex, ey, _ = record.end
    return None not in (sx, sy, ex, ey) and (not close(sx, ex, 1e-9) or not close(sy, ey, 1e-9))


def tool_diameters_mm(comments: list[str], program_is_inch: bool) -> list[float]:
    values: list[float] = []
    for comment in comments:
        upper = comment.upper()
        if not re.search(r"FACE\s*MILL|FLAT\s*END|END\s*MILL|\bEM\b|\d+(?:\.\d+)?\s*MM.*\b(?:FL|CRB|CARBIDE|LOC)\b", upper):
            continue
        for numerator, denominator in re.findall(r"(?<!\d)(\d+)\s*/\s*(\d+)(?!\d)", upper):
            if int(denominator):
                values.append(25.4 * int(numerator) / int(denominator))
        metric = re.findall(r"(?<![\d.])(\d+(?:\.\d+)?)\s*MM\b", upper)
        values.extend(float(value) for value in metric)
        inch = re.findall(r"(?<![\d.])(\d+(?:\.\d+)?)\s*(?:IN|INCH)\b", upper)
        values.extend(25.4 * float(value) for value in inch)
        if not metric and not inch and not re.search(r"\d+\s*/\s*\d+", upper):
            match = re.search(r"(?<![\d.])(\d+(?:\.\d+)?)\s+(?:\d+FL\s+)?(?:FACE\s*MILL|FLAT\s*END|END\s*MILL)", upper)
            if match:
                raw = float(match.group(1))
                values.append(raw * (25.4 if program_is_inch and raw <= 4.0 else 1.0))
    return sorted({round(value, 6) for value in values if 0.5 <= value <= MAX_INSTALLED_TOOL_DIAMETER_MM})


def line_distance(point, start, end) -> float:
    px, py = point
    ax, ay = start
    bx, by = end
    dx, dy = bx - ax, by - ay
    if close(dx, 0.0, 1e-12) and close(dy, 0.0, 1e-12):
        return math.hypot(px - ax, py - ay)
    ratio = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + ratio * dx), py - (ay + ratio * dy))


def arc_polyline(record: Record) -> list[tuple[float, float]]:
    sx, sy, _ = record.start
    ex, ey, _ = record.end
    if None in (sx, sy, ex, ey) or record.plane != 17:
        return []
    i, j = record.ij
    if i is None or j is None:
        return [(sx, sy), (ex, ey)]
    cx, cy = sx + i, sy + j
    radius = math.hypot(sx - cx, sy - cy)
    if radius <= 1e-9:
        return []
    start_angle = math.atan2(sy - cy, sx - cx)
    end_angle = math.atan2(ey - cy, ex - cx)
    if record.motion == 2:
        sweep = -((start_angle - end_angle) % (2 * math.pi))
    else:
        sweep = (end_angle - start_angle) % (2 * math.pi)
    if close(sweep, 0.0, 1e-12):
        sweep = -2 * math.pi if record.motion == 2 else 2 * math.pi
    steps = max(8, int(abs(sweep) * radius / 2.0))
    return [
        (cx + radius * math.cos(start_angle + sweep * step / steps), cy + radius * math.sin(start_angle + sweep * step / steps))
        for step in range(steps + 1)
    ]


def cut_segments(records: list[Record]) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    segments = []
    for record in records:
        if record.motion not in {1, 2, 3} or not xy_changed(record):
            continue
        if record.end[2] is None or not close(record.end[2], FINISH_Z, Z_TOL):
            continue
        points = arc_polyline(record) if record.motion in {2, 3} else [record.start[:2], record.end[:2]]
        if any(None in point for point in points):
            continue
        segments.extend(zip(points, points[1:]))
    return segments


def stock_grid(angle_degrees: float):
    angle = math.radians(angle_degrees)
    cosine, sine = math.cos(angle), math.sin(angle)
    xs = [(-STOCK_X / 2) + STOCK_X * index / 12 for index in range(13)]
    ys = [(-STOCK_Y / 2) + STOCK_Y * index / 8 for index in range(9)]
    return [
        (x * cosine - y * sine, x * sine + y * cosine)
        for x in xs
        for y in ys
    ]


def covers_stock(records: list[Record], diameters: list[float]) -> bool:
    segments = cut_segments(records)
    if not segments:
        return False
    for diameter in diameters:
        radius = diameter / 2.0 + 0.25
        for angle in range(0, 180, 5):
            if all(min(line_distance(point, *segment) for segment in segments) <= radius for point in stock_grid(angle)):
                return True
    return False


def validate_file(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 80 or path.stat().st_size > 2_000_000:
        return False
    source = path.read_text(encoding="utf-8", errors="ignore")
    upper = source.upper()
    records, comments, tool_changes, m30_lines, errors = parse_nc(source)
    if errors or len(m30_lines) != 1:
        return False
    if not re.search(r"\bG(?:20|21)\b", upper) or not re.search(r"\bG90\b", upper):
        return False
    if not any("FACE" in comment.upper() and "MILL" in comment.upper() for comment in comments):
        return False
    if not tool_changes or not records:
        return False

    material = [record for record in records if record.motion in {1, 2, 3} and xy_changed(record)]
    if not material:
        return False
    if len({record.tool for record in material}) != 1 or None in {record.tool for record in material}:
        return False
    if len({record.wcs for record in material}) != 1 or None in {record.wcs for record in material}:
        return False
    if any(record.feed is None or record.feed <= 0 for record in material):
        return False
    if any(not record.spindle_on or record.speed is None or record.speed <= 0 for record in material):
        return False
    if any(not record.length_comp or record.h is None or record.h <= 0 for record in material):
        return False
    if any(record.plane != 17 for record in material):
        return False
    if any(record.end[2] is None or record.end[2] < FINISH_Z - Z_TOL for record in material):
        return False
    if not any(record.end[2] is not None and close(record.end[2], FINISH_Z, Z_TOL) for record in material):
        return False
    for record in records:
        if record.motion == 0 and xy_changed(record):
            z = record.start[2]
            if z is None:
                if not record.safe_home_before:
                    return False
            elif z < 1.0:
                return False
        if record.motion in {1, 2, 3} and record.end[2] is not None and record.end[2] < FINISH_Z - Z_TOL:
            return False

    program_is_inch = bool(re.search(r"\bG20\b", upper)) and not bool(re.search(r"\bG21\b", upper))
    diameters = tool_diameters_mm(comments, program_is_inch)
    return covers_stock(records, diameters)


def evaluate() -> bool:
    return validate_file(TARGET / OUTPUT_NAME)


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print("True" if ok else "False")
