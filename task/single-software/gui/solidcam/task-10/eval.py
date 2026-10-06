from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path


DEFAULT_TARGET = r"C:\Users\User\Desktop"
TARGET = Path(os.environ.get("EVAL_TARGET_DIR", os.environ.get("OUTPUT_ROOT", DEFAULT_TARGET)))
OUTPUT_NAME = "task-10.gcode"

DEPTH_TOL_MM = 0.45
GEOMETRY_TOL_MM = 0.65
OFFSET_TARGET_MM = 0.15
OFFSET_TOL_MM = 0.10
SAFE_CLEARANCE_MM = 0.5
WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))", re.IGNORECASE)
COMMENT_RE = re.compile(r"\(([^()]*)\)")
OPERATION_RE = re.compile(r"\b(?:CONTOUR|PROFILE)(?:\s+MILL)?\s*\d*\b", re.IGNORECASE)


@dataclass
class Record:
    line: int
    motion: int
    start: dict[str, float | None]
    end: dict[str, float | None]
    explicit: dict[str, float]
    tool: int | None
    wcs: str | None
    spindle_on: bool
    feed: float | None


@dataclass
class Program:
    code_lines: list[str] = field(default_factory=list)
    records: list[Record] = field(default_factory=list)
    tools: list[int] = field(default_factory=list)
    units_seen: set[int] = field(default_factory=set)
    distance_modes_seen: set[int] = field(default_factory=set)
    axes_seen: set[str] = field(default_factory=set)
    m_codes_seen: set[int] = field(default_factory=set)
    m30_lines: list[int] = field(default_factory=list)
    g_codes_seen: set[int] = field(default_factory=set)
    has_tool_length_comp: bool = False


@dataclass(frozen=True)
class Operation:
    header_line: int
    end_line: int
    comment: str
    diameter_mm: float | None
    records: tuple[Record, ...]


@dataclass(frozen=True)
class Rectangle:
    bounds: tuple[float, float, float, float]
    center: tuple[float, float]
    long_span: float
    short_span: float


def close(left: float, right: float, tolerance: float = GEOMETRY_TOL_MM) -> bool:
    return abs(float(left) - float(right)) <= tolerance


def split_line(raw: str) -> str:
    return COMMENT_RE.sub(" ", raw.upper()).split(";", 1)[0]


def parse_program(source: str) -> Program:
    program = Program()
    position: dict[str, float | None] = {"x": None, "y": None, "z": None}
    unit_scale: float | None = None
    absolute = True
    wcs: str | None = None
    pending_tool: int | None = None
    current_tool: int | None = None
    modal_motion: int | None = None
    spindle_on = False
    modal_feed: float | None = None

    for line_number, raw in enumerate(source.splitlines()):
        code = split_line(raw)
        program.code_lines.append(code)
        words = [(letter.upper(), float(number)) for letter, number in WORD_RE.findall(code)]
        if not words:
            continue
        g_codes = [int(round(value)) for letter, value in words if letter == "G"]
        m_codes = [int(round(value)) for letter, value in words if letter == "M"]
        program.g_codes_seen.update(g_codes)
        program.m_codes_seen.update(m_codes)

        if 20 in g_codes:
            unit_scale = 25.4
            program.units_seen.add(20)
        if 21 in g_codes:
            unit_scale = 1.0
            program.units_seen.add(21)
        if 90 in g_codes:
            absolute = True
            program.distance_modes_seen.add(90)
        if 91 in g_codes:
            absolute = False
            program.distance_modes_seen.add(91)
        for value in g_codes:
            if 54 <= value <= 59:
                wcs = f"G{value}"
        if 43 in g_codes:
            program.has_tool_length_comp = True

        for letter, value in words:
            if letter == "T":
                pending_tool = int(round(value))
            if letter in {"X", "Y", "Z", "A", "B", "C", "U", "V", "W"}:
                program.axes_seen.add(letter)
        if 6 in m_codes:
            if pending_tool is None or pending_tool <= 0:
                raise ValueError("M6 without a valid tool")
            current_tool = pending_tool
            if current_tool not in program.tools:
                program.tools.append(current_tool)
            spindle_on = False
        if 3 in m_codes or 4 in m_codes:
            spindle_on = True
        if 5 in m_codes:
            spindle_on = False
        if 30 in m_codes:
            program.m30_lines.append(line_number)

        if 80 in g_codes:
            modal_motion = None
        explicit_motion = next((value for value in g_codes if value in {0, 1, 2, 3}), None)
        if explicit_motion is not None:
            modal_motion = explicit_motion

        converted: dict[str, float] = {}
        if unit_scale is not None:
            converted = {
                letter.lower(): value * unit_scale
                for letter, value in words
                if letter in {"X", "Y", "Z", "I", "J", "K", "R"}
            }
            feed_words = [value * unit_scale for letter, value in words if letter == "F"]
            if feed_words:
                modal_feed = feed_words[-1]

        machine_return = 28 in g_codes or 30 in g_codes
        start = dict(position)
        if not machine_return and unit_scale is not None:
            for axis in ("x", "y", "z"):
                if axis not in converted:
                    continue
                if absolute:
                    position[axis] = converted[axis]
                elif position[axis] is not None:
                    position[axis] += converted[axis]
                else:
                    raise ValueError("incremental motion before an absolute work position")

        if machine_return or current_tool is None or modal_motion is None:
            continue
        if not any(axis in converted for axis in ("x", "y", "z")) and not (
            modal_motion in {2, 3} and ("i" in converted or "j" in converted or "r" in converted)
        ):
            continue
        program.records.append(
            Record(
                line=line_number,
                motion=modal_motion,
                start=start,
                end=dict(position),
                explicit=converted,
                tool=current_tool,
                wcs=wcs,
                spindle_on=spindle_on,
                feed=modal_feed,
            )
        )
    return program


def xy_changed(record: Record) -> bool:
    start, end = record.start, record.end
    return (
        None not in (start["x"], start["y"], end["x"], end["y"])
        and (not close(start["x"], end["x"], 1.0e-6) or not close(start["y"], end["y"], 1.0e-6))
    )


def is_cutting(record: Record) -> bool:
    if record.motion == 1:
        return xy_changed(record)
    if record.motion in {2, 3}:
        return xy_changed(record) or "i" in record.explicit or "j" in record.explicit or "r" in record.explicit
    return False


def cutting(records: list[Record] | tuple[Record, ...]) -> list[Record]:
    return [record for record in records if is_cutting(record)]


def point_states(record: Record) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for state in (record.start, record.end):
        if state["x"] is not None and state["y"] is not None:
            result.append((state["x"], state["y"]))
    return result


def bbox(records: list[Record]) -> tuple[float, float, float, float] | None:
    points = [point for record in records for point in point_states(record)]
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), max(xs), min(ys), max(ys)


def bounds_center(bounds: tuple[float, float, float, float]) -> tuple[float, float]:
    return (bounds[0] + bounds[1]) / 2.0, (bounds[2] + bounds[3]) / 2.0


def bounds_spans(bounds: tuple[float, float, float, float]) -> tuple[float, float]:
    width, height = bounds[1] - bounds[0], bounds[3] - bounds[2]
    return max(width, height), min(width, height)


def diameter_hint(comments: str) -> float | None:
    metric = re.findall(r"(?<![\d.])(\d+(?:\.\d+)?)\s*MM\b", comments, re.IGNORECASE)
    if metric:
        return float(metric[0])
    inch = re.findall(r"(?<![\d.])(\d+(?:\.\d+)?)\s*(?:IN|INCH)\b", comments, re.IGNORECASE)
    if inch:
        return 25.4 * float(inch[0])
    fraction = re.findall(r"(?<!\d)(\d+\s*/\s*\d+)(?!\d)", comments)
    if fraction:
        return 25.4 * float(Fraction(fraction[0].replace(" ", "")))
    return None


def operations(program: Program, source: str) -> list[Operation]:
    raw_lines = source.splitlines()
    headers: list[tuple[int, str]] = []
    for line_number, raw in enumerate(raw_lines):
        comments = " ".join(COMMENT_RE.findall(raw))
        if OPERATION_RE.search(comments):
            headers.append((line_number, comments.strip()))
    result: list[Operation] = []
    for index, (line, comment) in enumerate(headers):
        end = headers[index + 1][0] if index + 1 < len(headers) else len(raw_lines)
        section_comments = " ".join(
            text for raw in raw_lines[line:end] for text in COMMENT_RE.findall(raw)
        )
        records = tuple(record for record in program.records if line < record.line < end)
        if cutting(records):
            result.append(Operation(line, end, comment, diameter_hint(section_comments), records))
    return result


def groups_at_floor(records: tuple[Record, ...], floor: float) -> list[list[Record]]:
    groups: list[list[Record]] = []
    current: list[Record] = []
    for record in records:
        qualifies = (
            is_cutting(record)
            and record.end["z"] is not None
            and close(record.end["z"], floor, DEPTH_TOL_MM)
        )
        if not qualifies:
            if current:
                groups.append(current)
                current = []
            continue
        current.append(record)
    if current:
        groups.append(current)
    return groups


def closed_linear_rectangle(group: list[Record]) -> Rectangle | None:
    lines = [record for record in group if record.motion == 1 and xy_changed(record)]
    if len(lines) < 4:
        return None
    first = lines[0].start
    last = lines[-1].end
    if None in (first["x"], first["y"], last["x"], last["y"]):
        return None
    if not close(first["x"], last["x"], 0.35) or not close(first["y"], last["y"], 0.35):
        return None
    bounds = bbox(lines)
    if bounds is None:
        return None
    width = bounds[1] - bounds[0]
    height = bounds[3] - bounds[2]
    long_span, short_span = bounds_spans(bounds)
    if short_span <= 0.2:
        return None
    horizontal = sum(
        close(record.start["y"], record.end["y"], 0.08)
        and abs(record.end["x"] - record.start["x"]) >= 0.65 * width
        for record in lines
    )
    vertical = sum(
        close(record.start["x"], record.end["x"], 0.08)
        and abs(record.end["y"] - record.start["y"]) >= 0.65 * height
        for record in lines
    )
    if horizontal < 2 or vertical < 2:
        return None
    return Rectangle(bounds, bounds_center(bounds), long_span, short_span)


def unique_rectangles(rectangles: list[Rectangle]) -> list[Rectangle]:
    result: list[Rectangle] = []
    for rectangle in rectangles:
        if any(math.dist(rectangle.center, other.center) <= 1.0 for other in result):
            continue
        result.append(rectangle)
    return result


def full_circle(record: Record) -> tuple[float, float, float] | None:
    if record.motion not in {2, 3} or "i" not in record.explicit or "j" not in record.explicit:
        return None
    if None in (record.start["x"], record.start["y"], record.end["x"], record.end["y"]):
        return None
    if not close(record.start["x"], record.end["x"], 0.08) or not close(record.start["y"], record.end["y"], 0.08):
        return None
    cx = record.start["x"] + record.explicit["i"]
    cy = record.start["y"] + record.explicit["j"]
    radius = math.hypot(record.explicit["i"], record.explicit["j"])
    return (cx, cy, radius) if radius > 0.1 else None


def unique_circles(groups: list[list[Record]]) -> list[tuple[float, float, float]]:
    result: list[tuple[float, float, float]] = []
    for group in groups:
        circles = [circle for record in group if (circle := full_circle(record)) is not None]
        if not circles:
            continue
        candidate = circles[0]
        if sum(math.dist(candidate[:2], circle[:2]) <= 0.2 and close(candidate[2], circle[2], 0.15) for circle in circles) < 1:
            continue
        if any(math.dist(candidate[:2], other[:2]) <= 1.0 for other in result):
            continue
        result.append(candidate)
    return result


def normalize_point(
    point: tuple[float, float], outer: Rectangle
) -> tuple[float, float]:
    x, y = point
    cx, cy = outer.center
    width = outer.bounds[1] - outer.bounds[0]
    height = outer.bounds[3] - outer.bounds[2]
    return (x - cx, y - cy) if width >= height else (y - cy, x - cx)


def valid_window_pattern(rectangles: list[Rectangle], outer: Rectangle) -> bool:
    if len(rectangles) < 2:
        return False
    normalized = [normalize_point(rectangle.center, outer) for rectangle in rectangles]
    central = [point for point in normalized if abs(point[0]) <= 1.0 and abs(point[1]) <= 1.0]
    offset = [point for point in normalized if close(abs(point[0]), 35.0, 1.0) and abs(point[1]) <= 1.0]
    return bool(central and offset)


def valid_hole_pattern(circles: list[tuple[float, float, float]], outer: Rectangle) -> bool:
    matching: list[tuple[float, float]] = []
    for circle in circles:
        u, v = normalize_point(circle[:2], outer)
        if close(abs(u), 65.0, 1.0) and close(abs(v), 35.0, 1.0):
            matching.append((u, v))
    quadrants = {(1 if u > 0 else -1, 1 if v > 0 else -1) for u, v in matching}
    return len(quadrants) == 4


def allowance_ok(value: float) -> bool:
    return close(value, OFFSET_TARGET_MM, OFFSET_TOL_MM)


def rectangle_allowance(rectangle: Rectangle, diameter: float, nominal_long: float, nominal_short: float, internal: bool) -> bool:
    if internal:
        values = [
            (nominal_long - diameter - rectangle.long_span) / 2.0,
            (nominal_short - diameter - rectangle.short_span) / 2.0,
        ]
    else:
        values = [
            (rectangle.long_span - nominal_long - diameter) / 2.0,
            (rectangle.short_span - nominal_short - diameter) / 2.0,
        ]
    return all(allowance_ok(value) for value in values) and close(values[0], values[1], 0.10)


def safe_traverses(program: Program) -> bool:
    for record in program.records:
        if record.motion != 0 or not xy_changed(record):
            continue
        if record.end["z"] is None or record.end["z"] >= SAFE_CLEARANCE_MM:
            continue
        return False
    return True


def read_gcode(path: Path) -> str | None:
    try:
        if not path.is_file() or not 500 <= path.stat().st_size <= 2_000_000:
            return None
        data = path.read_bytes()
        if b"\x00" in data:
            return None
        source = data.decode("latin-1")
        printable = sum(character in "\t\r\n" or 32 <= ord(character) <= 126 for character in source)
        return source if printable / max(1, len(source)) >= 0.98 else None
    except Exception:
        return None


def validate_gcode(path: Path) -> bool:
    source = read_gcode(path)
    if source is None:
        return False
    try:
        program = parse_program(source)
    except Exception:
        return False

    if len(program.units_seen) != 1 or 90 not in program.distance_modes_seen:
        return False
    if not program.tools or not ({0, 1} <= {record.motion for record in program.records}):
        return False
    if program.axes_seen & {"A", "B", "C", "U", "V", "W"}:
        return False
    if not {3, 6, 30} <= program.m_codes_seen or not program.has_tool_length_comp:
        return False
    if len(program.m30_lines) != 1:
        return False
    if any(WORD_RE.search(line) for line in program.code_lines[program.m30_lines[0] + 1 :]):
        return False
    all_cuts = cutting(program.records)
    if len(all_cuts) < 80 or any(
        not record.spindle_on or record.wcs is None or record.feed is None or record.feed <= 0
        for record in all_cuts
    ):
        return False
    if not safe_traverses(program):
        return False

    sections = operations(program, source)
    if len(sections) < 3 or any(section.diameter_mm is None for section in sections):
        return False

    analyses: list[dict[str, object]] = []
    for section in sections:
        section_cuts = cutting(section.records)
        z_values = [record.end["z"] for record in section_cuts if record.end["z"] is not None]
        if not z_values:
            continue
        floor = min(z_values)
        groups = groups_at_floor(section.records, floor)
        rectangles = unique_rectangles(
            [rectangle for group in groups if (rectangle := closed_linear_rectangle(group)) is not None]
        )
        circles = unique_circles(groups)
        analyses.append(
            {
                "section": section,
                "floor": floor,
                "groups": groups,
                "rectangles": rectangles,
                "circles": circles,
            }
        )
    if len(analyses) < 3:
        return False
    if any(not close(float(item["floor"]), -6.0, DEPTH_TOL_MM) for item in analyses):
        return False

    last = analyses[-1]
    last_section = last["section"]
    assert isinstance(last_section, Operation)
    last_rectangles = last["rectangles"]
    assert isinstance(last_rectangles, list)
    outer_candidates = [
        rectangle
        for rectangle in last_rectangles
        if isinstance(rectangle, Rectangle) and rectangle.long_span >= 175.0 and rectangle.short_span >= 95.0
    ]
    if not outer_candidates:
        return False
    outer = max(outer_candidates, key=lambda rectangle: rectangle.long_span * rectangle.short_span)
    outer_diameter = float(last_section.diameter_mm)
    if not 1.0 <= outer_diameter <= 20.0 or not rectangle_allowance(outer, outer_diameter, 180.0, 100.0, False):
        return False

    window_matches: list[tuple[Operation, list[Rectangle]]] = []
    hole_matches: list[tuple[Operation, list[tuple[float, float, float]]]] = []
    for item in analyses[:-1]:
        section = item["section"]
        rectangles = item["rectangles"]
        circles = item["circles"]
        assert isinstance(section, Operation) and isinstance(rectangles, list) and isinstance(circles, list)
        diameter = section.diameter_mm
        if diameter is None or not 1.0 <= diameter < 7.7:
            continue
        useful_rectangles = [
            rectangle
            for rectangle in rectangles
            if isinstance(rectangle, Rectangle)
            and rectangle_allowance(rectangle, diameter, 34.0, 24.0, True)
        ]
        if valid_window_pattern(useful_rectangles, outer):
            window_matches.append((section, useful_rectangles))
        useful_circles = [
            circle
            for circle in circles
            if allowance_ok(4.0 - diameter / 2.0 - circle[2])
        ]
        if valid_hole_pattern(useful_circles, outer):
            hole_matches.append((section, useful_circles))

    if not window_matches or not hole_matches:
        return False
    if any(section.header_line >= last_section.header_line for section, _ in window_matches + hole_matches):
        return False
    return True


def evaluate() -> bool:
    return validate_gcode(TARGET / OUTPUT_NAME)


if __name__ == "__main__":
    try:
        result = evaluate()
    except Exception:
        result = False
    print("True" if result else "False")
