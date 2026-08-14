from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path


DEFAULT_TARGET = r"C:\Users\User\Desktop"
TARGET = Path(os.environ.get("EVAL_TARGET_DIR", os.environ.get("OUTPUT_ROOT", DEFAULT_TARGET)))
OUTPUT_NAME = "task-9.nc"

DEPTH_TOL_MM = 0.45
GEOMETRY_TOL_MM = 1.5
SAFE_CLEARANCE_MM = 0.5
WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))", re.IGNORECASE)
COMMENT_RE = re.compile(r"\(([^()]*)\)")
OPERATION_RE = re.compile(
    r"\b(?:ROUGH\s+MILL\s*\d*|POCKET\s*\d*|IREST\s*\d*|REST\s+MACHIN\w*|REST\s+CLEAN\w*|CLEANUP\s*\d*|CONTOUR\s+MILL\s*\d*)\b",
    re.IGNORECASE,
)


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
    has_tool_length_comp: bool = False


@dataclass(frozen=True)
class Operation:
    header_line: int
    end_line: int
    comment: str
    diameter_mm: float | None
    records: tuple[Record, ...]


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
        if not any(axis in converted for axis in ("x", "y", "z")):
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


def cutting_xy(records: list[Record] | tuple[Record, ...]) -> list[Record]:
    return [record for record in records if record.motion in {1, 2, 3} and xy_changed(record)]


def record_points(record: Record) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for state in (record.start, record.end):
        if state["x"] is not None and state["y"] is not None:
            result.append((state["x"], state["y"]))
    return result


def bbox(records: list[Record]) -> tuple[float, float, float, float] | None:
    points = [point for record in records for point in record_points(record)]
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), max(xs), min(ys), max(ys)


def center(bounds: tuple[float, float, float, float]) -> tuple[float, float]:
    return (bounds[0] + bounds[1]) / 2.0, (bounds[2] + bounds[3]) / 2.0


def spans(bounds: tuple[float, float, float, float]) -> tuple[float, float]:
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
        if records:
            result.append(Operation(line, end, comment, diameter_hint(section_comments), records))
    return result


def distinct_levels(records: list[Record]) -> list[float]:
    return sorted({round(record.end["z"], 3) for record in records if record.end["z"] is not None})


def clears_area(records: list[Record]) -> bool:
    bounds = bbox(records)
    if bounds is None:
        return False
    cx, cy = center(bounds)
    width, height = bounds[1] - bounds[0], bounds[3] - bounds[2]
    core = 0
    for record in records:
        points = record_points(record)
        if not points:
            continue
        mx = sum(point[0] for point in points) / len(points)
        my = sum(point[1] for point in points) / len(points)
        if abs(mx - cx) <= 0.33 * width and abs(my - cy) <= 0.33 * height:
            core += 1
    return core >= 5


def cross_topology(records: list[Record]) -> bool:
    bounds = bbox(records)
    if bounds is None:
        return False
    cx, cy = center(bounds)
    width, height = bounds[1] - bounds[0], bounds[3] - bounds[2]
    if width >= height:
        transformed = [((x - cx) / (width / 2.0), (y - cy) / (height / 2.0)) for record in records for x, y in record_points(record)]
    else:
        transformed = [((y - cy) / (height / 2.0), (x - cx) / (width / 2.0)) for record in records for x, y in record_points(record)]
    if not transformed:
        return False
    arms = [
        any(u >= 0.75 and abs(v) <= 0.28 for u, v in transformed),
        any(u <= -0.75 and abs(v) <= 0.28 for u, v in transformed),
        any(v >= 0.75 and abs(u) <= 0.28 for u, v in transformed),
        any(v <= -0.75 and abs(u) <= 0.28 for u, v in transformed),
    ]
    corner_hits = sum(abs(u) >= 0.55 and abs(v) >= 0.55 for u, v in transformed)
    return all(arms) and corner_hits == 0


def extra_cleanup_contribution(small: list[Record], large_bounds: tuple[float, float, float, float]) -> bool:
    margin = 2.0
    outside = []
    for record in small:
        for x, y in record_points(record):
            if x < large_bounds[0] - margin or x > large_bounds[1] + margin or y < large_bounds[2] - margin or y > large_bounds[3] + margin:
                outside.append((x, y))
    return len(outside) >= 20


def safe_traverses(program: Program) -> bool:
    for record in program.records:
        if record.motion != 0 or not xy_changed(record):
            continue
        if record.end["z"] is None or record.end["z"] >= SAFE_CLEARANCE_MM:
            continue
        return False
    return True


def read_nc(path: Path) -> str | None:
    try:
        if not path.is_file() or not 300 <= path.stat().st_size <= 2_000_000:
            return None
        data = path.read_bytes()
        if b"\x00" in data:
            return None
        source = data.decode("latin-1")
        printable = sum(character in "\t\r\n" or 32 <= ord(character) <= 126 for character in source)
        return source if printable / max(1, len(source)) >= 0.98 else None
    except Exception:
        return None


def validate_nc(path: Path) -> bool:
    source = read_nc(path)
    if source is None:
        return False
    try:
        program = parse_program(source)
    except Exception:
        return False
    if len(program.units_seen) != 1 or 90 not in program.distance_modes_seen:
        return False
    if len(program.tools) < 2 or not ({0, 1} <= {record.motion for record in program.records}):
        return False
    if program.axes_seen & {"A", "B", "C", "U", "V", "W"}:
        return False
    if not {3, 6, 30} <= program.m_codes_seen or not program.has_tool_length_comp:
        return False
    if len(program.m30_lines) != 1:
        return False
    if any(WORD_RE.search(line) for line in program.code_lines[program.m30_lines[0] + 1:]):
        return False
    cuts = cutting_xy(program.records)
    if len(cuts) < 60 or any(not record.spindle_on or record.wcs is None or record.feed is None or record.feed <= 0 for record in cuts):
        return False
    if not safe_traverses(program):
        return False

    sections = operations(program, source)
    if len(sections) < 2:
        return False
    candidates: list[tuple[Operation, list[Record], list[Record], tuple[float, float, float, float]]] = []
    for section in sections:
        section_cuts = cutting_xy(section.records)
        if not section_cuts:
            continue
        floor = min(record.end["z"] for record in section_cuts if record.end["z"] is not None)
        floor_cuts = [record for record in section_cuts if record.end["z"] is not None and close(record.end["z"], floor, DEPTH_TOL_MM)]
        bounds = bbox(floor_cuts)
        if bounds is not None:
            candidates.append((section, section_cuts, floor_cuts, bounds))
    if len(candidates) < 2:
        return False

    large, small = candidates[0], candidates[1]
    large_section, large_cuts, large_floor, large_bounds = large
    small_section, small_cuts, small_floor, small_bounds = small
    if large_section.diameter_mm is None or small_section.diameter_mm is None:
        return False
    if not (8.0 <= large_section.diameter_mm <= 22.0 and 2.0 <= small_section.diameter_mm <= 10.0):
        return False
    if large_section.diameter_mm - small_section.diameter_mm < 2.0:
        return False
    if large_section.header_line >= small_section.header_line:
        return False
    if not large_floor or not small_floor:
        return False
    large_z = min(record.end["z"] for record in large_floor if record.end["z"] is not None)
    small_z = min(record.end["z"] for record in small_floor if record.end["z"] is not None)
    if not close(large_z, -10.0, DEPTH_TOL_MM) or not close(small_z, -10.0, DEPTH_TOL_MM):
        return False
    if not close(large_z, small_z, DEPTH_TOL_MM):
        return False

    large_long, large_short = spans(large_bounds)
    small_long, small_short = spans(small_bounds)
    if not (25.0 <= large_long <= 50.0 and 7.0 <= large_short <= 30.0):
        return False
    if not (55.0 <= small_long <= 80.0 and 35.0 <= small_short <= 60.0):
        return False
    if small_long - large_long < 12.0 or small_short - large_short < 12.0:
        return False
    if math.dist(center(large_bounds), center(small_bounds)) > 5.0:
        return False
    if len(large_cuts) < 25 or len(small_cuts) < 55:
        return False
    if len(distinct_levels(large_cuts)) < 2 or len(distinct_levels(small_cuts)) < 2:
        return False
    if not clears_area(large_floor) or not clears_area(small_floor):
        return False
    if not cross_topology(small_floor):
        return False
    if not extra_cleanup_contribution(small_floor, large_bounds):
        return False
    return True


def evaluate() -> bool:
    return validate_nc(TARGET / OUTPUT_NAME)


if __name__ == "__main__":
    try:
        result = evaluate()
    except Exception:
        result = False
    print("True" if result else "False")
