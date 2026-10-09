from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path


DEFAULT_TARGET = r"C:\Users\User\Desktop"
TARGET = Path(os.environ.get("EVAL_TARGET_DIR", os.environ.get("OUTPUT_ROOT", DEFAULT_TARGET)))
OUTPUT_NAME = "task-14.nc"

WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))", re.IGNORECASE)
PAREN_COMMENT_RE = re.compile(r"\(([^()]*)\)")

SAFE_POINTS = (
    (-30.0, -20.0),
    (-30.0, 0.0),
    (-30.0, 20.0),
    (0.0, -20.0),
    (0.0, 0.0),
    (0.0, 20.0),
    (0.0, 30.0),
    (30.0, -20.0),
    (30.0, 0.0),
    (30.0, 20.0),
)
RISK_POINTS = ((-30.0, 30.0), (30.0, 30.0))

XY_TOL = 0.65
MIN_BOTTOM_Z = -21.5
MAX_BOTTOM_Z = -17.9
MIN_GENERAL_TRAVERSE_Z = 1.0
RISK_SAFE_Z = 11.0
RISK_CLEARANCE = 0.5
RISK_RECTS = ((-39.0, 30.0, -21.0, 38.0), (21.0, 30.0, 39.0, 38.0))
ALLOWED_G_CODES = {
    0, 1, 2, 3, 4, 17, 20, 21, 28, 30, 40, 41, 42, 43, 44, 49, 53,
    54, 55, 56, 57, 58, 59, 61, 64, 73, 80, 81, 82, 83, 90, 91, 94, 98, 99,
}
ALLOWED_M_CODES = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 19, 30}


@dataclass
class Record:
    line: int
    section: int
    motion: int
    start: dict[str, float | None]
    end: dict[str, float | None]
    explicit: dict[str, float]
    tool: int
    wcs: str | None
    spindle_on: bool
    spindle_speed: float | None
    feed: float | None
    tool_length_active: bool
    length_offset: int | None


@dataclass
class DrillEvent:
    line: int
    section: int
    tool: int
    wcs: str
    x: float
    y: float
    bottom: float
    retract: float
    cycle: int | None
    q: float | None
    spindle_on: bool
    spindle_speed: float | None
    feed: float | None
    tool_length_active: bool
    length_offset: int | None
    record_index: int | None = None


@dataclass
class Section:
    tool: int
    line: int
    records: list[Record] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)
    has_g43: bool = False


@dataclass
class Program:
    records: list[Record] = field(default_factory=list)
    cycle_events: list[DrillEvent] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    comments: list[tuple[int, str]] = field(default_factory=list)
    code_lines: list[str] = field(default_factory=list)
    units_seen: set[int] = field(default_factory=set)
    distance_modes_seen: set[int] = field(default_factory=set)
    axes_seen: set[str] = field(default_factory=set)
    m_codes_seen: set[int] = field(default_factory=set)
    m30_lines: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class Frame:
    expected_origin: tuple[float, float]
    actual_origin: tuple[float, float]
    expected_axis: tuple[float, float]
    expected_normal: tuple[float, float]
    actual_axis: tuple[float, float]
    actual_normal: tuple[float, float]
    handedness: float

    def forward(self, expected: tuple[float, float]) -> tuple[float, float]:
        delta = (
            expected[0] - self.expected_origin[0],
            expected[1] - self.expected_origin[1],
        )
        along = dot(delta, self.expected_axis)
        across = dot(delta, self.expected_normal)
        return (
            self.actual_origin[0]
            + along * self.actual_axis[0]
            + self.handedness * across * self.actual_normal[0],
            self.actual_origin[1]
            + along * self.actual_axis[1]
            + self.handedness * across * self.actual_normal[1],
        )

    def inverse(self, actual: tuple[float, float]) -> tuple[float, float]:
        delta = (actual[0] - self.actual_origin[0], actual[1] - self.actual_origin[1])
        along = dot(delta, self.actual_axis)
        across = self.handedness * dot(delta, self.actual_normal)
        return (
            self.expected_origin[0] + along * self.expected_axis[0] + across * self.expected_normal[0],
            self.expected_origin[1] + along * self.expected_axis[1] + across * self.expected_normal[1],
        )


def dot(left: tuple[float, float], right: tuple[float, float]) -> float:
    return left[0] * right[0] + left[1] * right[1]


def close(left: float, right: float, tolerance: float = XY_TOL) -> bool:
    return abs(float(left) - float(right)) <= tolerance


def split_line(raw: str) -> tuple[str, list[str]]:
    upper = raw.upper()
    comments = [item.strip() for item in PAREN_COMMENT_RE.findall(upper) if item.strip()]
    code = PAREN_COMMENT_RE.sub(" ", upper)
    if ";" in code:
        code, semicolon_comment = code.split(";", 1)
        if semicolon_comment.strip():
            comments.append(semicolon_comment.strip())
    return code, comments


def integer_controls(words: list[tuple[str, float]], letter: str) -> list[int]:
    result: list[int] = []
    for word_letter, value in words:
        if word_letter != letter:
            continue
        rounded = int(round(value))
        if abs(value - rounded) > 1.0e-9:
            raise ValueError(f"fractional {letter} control word")
        result.append(rounded)
    return result


def parse_program(source: str) -> Program:
    program = Program()
    position: dict[str, float | None] = {"x": None, "y": None, "z": None}
    unit_scale: float | None = None
    absolute = True
    wcs: str | None = None
    pending_tool: int | None = None
    current_tool: int | None = None
    section_index: int | None = None
    modal_motion: int | None = None
    active_cycle: int | None = None
    cycle_bottom: float | None = None
    cycle_r: float | None = None
    cycle_q: float | None = None
    cycle_initial: float | None = None
    return_to_initial = False
    spindle_on = False
    spindle_speed: float | None = None
    modal_feed: float | None = None
    tool_length_active = False
    length_offset: int | None = None

    for line_number, raw in enumerate(source.splitlines()):
        code, comments = split_line(raw)
        if re.search(r"[A-Z]\s*[+-]?(?:NAN|INF(?:INITY)?)\b", code, re.IGNORECASE):
            raise ValueError("non-finite numeric word")
        program.code_lines.append(code)
        program.comments.extend((line_number, comment) for comment in comments)
        words = [(letter.upper(), float(value)) for letter, value in WORD_RE.findall(code)]
        if not words:
            continue
        g_codes = integer_controls(words, "G")
        m_codes = integer_controls(words, "M")
        if any(value not in ALLOWED_G_CODES for value in g_codes):
            raise ValueError("unsupported G code")
        if any(value not in ALLOWED_M_CODES for value in m_codes):
            raise ValueError("unsupported M code")
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
        if 98 in g_codes:
            return_to_initial = True
        if 99 in g_codes:
            return_to_initial = False
        for value in g_codes:
            if 54 <= value <= 59:
                wcs = f"G{value}"
        for letter, value in words:
            if letter == "T":
                rounded = int(round(value))
                if abs(value - rounded) > 1.0e-9:
                    raise ValueError("fractional T control word")
                pending_tool = rounded
            if letter in {"X", "Y", "Z", "A", "B", "C", "U", "V", "W"}:
                program.axes_seen.add(letter)

        if 6 in m_codes:
            if pending_tool is None or pending_tool <= 0:
                raise ValueError("M6 without a valid selected tool")
            current_tool = pending_tool
            program.sections.append(Section(current_tool, line_number))
            section_index = len(program.sections) - 1
            spindle_on = False
            spindle_speed = None
            tool_length_active = False
            length_offset = None
            active_cycle = None
            modal_motion = None
        if 3 in m_codes or 4 in m_codes:
            spindle_on = True
        if 5 in m_codes:
            spindle_on = False
        speeds = [value for letter, value in words if letter == "S"]
        if speeds:
            spindle_speed = speeds[-1]
        if 30 in m_codes:
            program.m30_lines.append(line_number)
        h_codes = integer_controls(words, "H")
        if h_codes:
            if len(h_codes) != 1 or h_codes[0] <= 0:
                raise ValueError("invalid H offset")
            length_offset = h_codes[0]
        if 49 in g_codes:
            tool_length_active = False
            length_offset = None
        if (43 in g_codes or 44 in g_codes) and section_index is not None:
            if length_offset is None or length_offset <= 0:
                raise ValueError("length compensation without a positive H offset")
            tool_length_active = True
            program.sections[section_index].has_g43 = True

        if 80 in g_codes:
            active_cycle = None
            cycle_bottom = None
            cycle_r = None
            cycle_q = None
            cycle_initial = None
            modal_motion = None
        explicit_cycle = next((value for value in g_codes if value in {73, 81, 82, 83}), None)
        explicit_motion = next((value for value in g_codes if value in {0, 1, 2, 3}), None)
        if explicit_cycle is not None:
            active_cycle = explicit_cycle
            modal_motion = explicit_cycle
            cycle_initial = position["z"]
        elif explicit_motion is not None:
            modal_motion = explicit_motion
            active_cycle = None

        converted: dict[str, float] = {}
        if unit_scale is not None:
            converted = {
                letter.lower(): value * unit_scale
                for letter, value in words
                if letter in {"X", "Y", "Z", "I", "J", "K", "R", "Q"}
            }
            feeds = [value * unit_scale for letter, value in words if letter == "F"]
            if feeds:
                modal_feed = feeds[-1]

        if active_cycle is not None:
            if "z" in converted:
                cycle_bottom = converted["z"] if absolute else (
                    None if position["z"] is None else float(position["z"]) + converted["z"]
                )
            if "r" in converted:
                cycle_r = converted["r"] if absolute else (
                    None if position["z"] is None else float(position["z"]) + converted["r"]
                )
            if "q" in converted:
                cycle_q = converted["q"]

        machine_coordinate = 53 in g_codes or 28 in g_codes or 30 in g_codes
        start = dict(position)
        if not machine_coordinate and unit_scale is not None:
            for axis in ("x", "y", "z"):
                if axis not in converted:
                    continue
                if active_cycle is not None and axis == "z":
                    continue
                if absolute:
                    position[axis] = converted[axis]
                elif position[axis] is not None:
                    position[axis] = float(position[axis]) + converted[axis]
                else:
                    raise ValueError("incremental move before a known work position")

        is_cycle_visit = (
            active_cycle is not None
            and current_tool is not None
            and section_index is not None
            and (explicit_cycle is not None or "x" in converted or "y" in converted)
        )
        if is_cycle_visit:
            retract = cycle_initial if return_to_initial else cycle_r
            if None in (position["x"], position["y"], cycle_bottom, retract, wcs):
                raise ValueError("incomplete canned drilling cycle")
            event = DrillEvent(
                line_number,
                section_index,
                current_tool,
                str(wcs),
                float(position["x"]),
                float(position["y"]),
                float(cycle_bottom),
                float(retract),
                active_cycle,
                cycle_q,
                spindle_on,
                spindle_speed,
                modal_feed,
                tool_length_active,
                length_offset,
            )
            program.cycle_events.append(event)
            position["z"] = float(retract)
            continue

        if machine_coordinate or current_tool is None or section_index is None or modal_motion is None:
            continue
        if not any(axis in converted for axis in ("x", "y", "z")) and not (
            modal_motion in {2, 3} and any(axis in converted for axis in ("i", "j", "r"))
        ):
            continue
        record = Record(
            line_number,
            section_index,
            modal_motion,
            start,
            dict(position),
            converted,
            current_tool,
            wcs,
            spindle_on,
            spindle_speed,
            modal_feed,
            tool_length_active,
            length_offset,
        )
        program.records.append(record)
        program.sections[section_index].records.append(record)

    if program.sections:
        program_end = program.m30_lines[0] if program.m30_lines else len(program.code_lines)
        for comment_line, comment in program.comments:
            if comment_line >= program_end:
                continue
            assigned: int | None = None
            upcoming = [
                index
                for index, section in enumerate(program.sections)
                if 0 < section.line - comment_line <= 6
            ]
            if upcoming:
                assigned = min(upcoming, key=lambda index: program.sections[index].line - comment_line)
            for index, section in enumerate(program.sections):
                if assigned is not None:
                    break
                next_line = program.sections[index + 1].line if index + 1 < len(program.sections) else program_end
                if section.line <= comment_line < next_line:
                    assigned = index
                    break
            if assigned is not None:
                program.sections[assigned].comments.append(comment)
    return program


def point(record: Record, which: str = "end") -> tuple[float, float] | None:
    value = record.start if which == "start" else record.end
    if value["x"] is None or value["y"] is None:
        return None
    return float(value["x"]), float(value["y"])


def xy_changed(record: Record) -> bool:
    start, end = point(record, "start"), point(record)
    return start is not None and end is not None and math.dist(start, end) > 1.0e-6


def explicit_drill_events(program: Program) -> list[DrillEvent]:
    result: list[DrillEvent] = []
    for index, record in enumerate(program.records):
        if record.motion != 1 or record.feed is None or record.feed <= 0 or xy_changed(record):
            continue
        if None in (record.start["x"], record.start["y"], record.start["z"], record.end["z"], record.wcs):
            continue
        start_z, end_z = float(record.start["z"]), float(record.end["z"])
        if end_z >= start_z - 0.10:
            continue
        retract: float | None = None
        for later in program.records[index + 1 :]:
            if later.section != record.section:
                break
            if xy_changed(later):
                break
            if later.end["z"] is not None and float(later.end["z"]) >= MIN_GENERAL_TRAVERSE_Z:
                retract = float(later.end["z"])
                break
        if retract is None:
            continue
        result.append(
            DrillEvent(
                record.line,
                record.section,
                record.tool,
                str(record.wcs),
                float(record.end["x"]),
                float(record.end["y"]),
                end_z,
                retract,
                None,
                None,
                record.spindle_on,
                record.spindle_speed,
                record.feed,
                record.tool_length_active,
                record.length_offset,
                index,
            )
        )
    return result


def unique_centers(events: list[DrillEvent]) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for event in events:
        candidate = (event.x, event.y)
        if not any(math.dist(candidate, old) <= XY_TOL for old in result):
            result.append(candidate)
    return result


def match_points(actual: list[tuple[float, float]]) -> Frame | None:
    if len(actual) != len(SAFE_POINTS):
        return None
    for e0_index, e0 in enumerate(SAFE_POINTS):
        for e1 in SAFE_POINTS[e0_index + 1 :]:
            e_delta = (e1[0] - e0[0], e1[1] - e0[1])
            e_length = math.hypot(*e_delta)
            if e_length <= 1.0e-9:
                continue
            e_axis = (e_delta[0] / e_length, e_delta[1] / e_length)
            e_normal = (-e_axis[1], e_axis[0])
            for a0_index, a0 in enumerate(actual):
                for a1_index, a1 in enumerate(actual):
                    if a0_index == a1_index:
                        continue
                    a_delta = (a1[0] - a0[0], a1[1] - a0[1])
                    a_length = math.hypot(*a_delta)
                    if not close(a_length, e_length, 1.0):
                        continue
                    a_axis = (a_delta[0] / a_length, a_delta[1] / a_length)
                    a_normal = (-a_axis[1], a_axis[0])
                    for handedness in (1.0, -1.0):
                        frame = Frame(e0, a0, e_axis, e_normal, a_axis, a_normal, handedness)
                        targets = [frame.forward(expected) for expected in SAFE_POINTS]
                        unmatched = list(actual)
                        ok = True
                        for target in targets:
                            matches = [(math.dist(target, candidate), index) for index, candidate in enumerate(unmatched)]
                            distance, match_index = min(matches)
                            if distance > XY_TOL:
                                ok = False
                                break
                            unmatched.pop(match_index)
                        if ok and not unmatched:
                            return frame
    return None


def section_has_drill_hint(section: Section) -> bool:
    return any(re.search(r"\bDRILL(?:ING)?\b", re.sub(r"[^A-Z0-9]+", " ", comment.upper())) for comment in section.comments)


def section_has_tool_drill_descriptor(section: Section) -> bool:
    for comment in section.comments:
        normalized = re.sub(r"[^A-Z0-9./]+", " ", comment.upper()).strip()
        if "DRILL" not in normalized:
            continue
        if re.fullmatch(r"DRILL(?:ING)?\s*\d*", normalized):
            continue
        return True
    return False


def section_tool_diameters(section: Section) -> list[float]:
    result: list[float] = []
    for comment in section.comments:
        metric = re.search(r"\b(\d+(?:\.\d+)?)\s*MM\b[^\n]*\bDRILL\b", comment.upper())
        if metric:
            result.append(float(metric.group(1)))
        inch = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:IN|INCH)\b[^\n]*\bDRILL\b", comment.upper())
        if inch:
            result.append(float(inch.group(1)) * 25.4)
        fraction = re.search(
            r"\b(\d{1,2})\s*/\s*(\d{1,2})(?:\s*,\s*[A-Z])?\b[^\n]*\bDRILL\b",
            comment.upper(),
        )
        if fraction:
            numerator, denominator = int(fraction.group(1)), int(fraction.group(2))
            valid = (
                0 < numerator < denominator
                and denominator in {2, 4, 8, 16, 32, 64}
                and Fraction(numerator, denominator).denominator == denominator
            )
            diameter = numerator / denominator * 25.4 if valid else float("inf")
            result.append(diameter if 1.0 <= diameter <= 100.0 else float("inf"))
    return result


def segment_intersects_rect(start, end, rect, clearance=RISK_CLEARANCE) -> bool:
    x_min, y_min, x_max, y_max = rect
    x_min -= clearance
    y_min -= clearance
    x_max += clearance
    y_max += clearance
    dx, dy = end[0] - start[0], end[1] - start[1]
    low, high = 0.0, 1.0
    for p, q in (
        (-dx, start[0] - x_min),
        (dx, x_max - start[0]),
        (-dy, start[1] - y_min),
        (dy, y_max - start[1]),
    ):
        if abs(p) <= 1.0e-12:
            if q < 0:
                return False
            continue
        ratio = q / p
        if p < 0:
            low = max(low, ratio)
        else:
            high = min(high, ratio)
        if low > high:
            return False
    return True


def safe_motion(program: Program, events: list[DrillEvent], frame: Frame) -> bool:
    for record in program.records:
        if record.motion == 0 and record.end["z"] is not None and float(record.end["z"]) < -0.05:
            return False
        start_point, end_point = point(record, "start"), point(record)
        if record.motion == 0:
            for candidate, z_value in ((start_point, record.start["z"]), (end_point, record.end["z"])):
                if candidate is None or z_value is None or float(z_value) >= RISK_SAFE_Z:
                    continue
                nominal = frame.inverse(candidate)
                if any(segment_intersects_rect(nominal, nominal, rect) for rect in RISK_RECTS):
                    return False
        if not xy_changed(record):
            continue
        start, end = start_point, end_point
        if start is None or end is None:
            continue
        z_values = [float(value) for value in (record.start["z"], record.end["z"]) if value is not None]
        if z_values and min(z_values) < MIN_GENERAL_TRAVERSE_Z - 0.05:
            return False
        if z_values and min(z_values) < RISK_SAFE_Z:
            nominal_start, nominal_end = frame.inverse(start), frame.inverse(end)
            if any(segment_intersects_rect(nominal_start, nominal_end, rect) for rect in RISK_RECTS):
                return False

    cycles = sorted((event for event in events if event.cycle is not None), key=lambda item: item.line)
    previous: DrillEvent | None = None
    for event in cycles:
        if previous is not None and event.section == previous.section:
            start, end = (previous.x, previous.y), (event.x, event.y)
            traverse_z = min(previous.retract, event.retract)
            if traverse_z < RISK_SAFE_Z:
                nominal_start, nominal_end = frame.inverse(start), frame.inverse(end)
                if any(segment_intersects_rect(nominal_start, nominal_end, rect) for rect in RISK_RECTS):
                    return False
        previous = event
    return True


def read_nc(path: Path) -> str | None:
    try:
        if not path.is_file() or not 200 <= path.stat().st_size <= 2_000_000:
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
    if program.axes_seen & {"A", "B", "C", "U", "V", "W"}:
        return False
    if not program.sections or 6 not in program.m_codes_seen or not ({3, 4} & program.m_codes_seen):
        return False
    if len(program.m30_lines) != 1:
        return False
    if any(WORD_RE.search(line) for line in program.code_lines[program.m30_lines[0] + 1 :]):
        return False

    events = program.cycle_events + explicit_drill_events(program)
    if not events:
        return False
    if any(
        not event.spindle_on
        or event.spindle_speed is None
        or event.spindle_speed <= 0
        or event.feed is None
        or event.feed <= 0
        or event.retract < MIN_GENERAL_TRAVERSE_Z
        or not event.tool_length_active
        or event.length_offset is None
        or event.length_offset <= 0
        or not section_has_drill_hint(program.sections[event.section])
        for event in events
    ):
        return False
    if any(event.line >= program.m30_lines[0] for event in events):
        return False
    deep_event_sections = {
        event.section for event in events if MIN_BOTTOM_Z <= event.bottom <= MAX_BOTTOM_Z
    }
    if any(not section_has_tool_drill_descriptor(program.sections[index]) for index in deep_event_sections):
        return False
    explicit_events = explicit_drill_events(program)
    represented_records = {event.record_index for event in explicit_events}
    plunges = {
        index
        for index, record in enumerate(program.records)
        if record.motion == 1
        and not xy_changed(record)
        and record.start["z"] is not None
        and record.end["z"] is not None
        and float(record.end["z"]) < float(record.start["z"]) - 0.10
    }
    if plunges != represented_records:
        return False
    deep_section_candidates = {
        event.section for event in events if MIN_BOTTOM_Z <= event.bottom <= MAX_BOTTOM_Z
    }
    for section_index in deep_section_candidates:
        diameters = section_tool_diameters(program.sections[section_index])
        if diameters and any(not 4.0 <= diameter <= 6.5 for diameter in diameters):
            return False
    if len({event.wcs for event in events}) != 1:
        return False

    all_centers = unique_centers(events)
    frame = match_points(all_centers)
    if frame is None:
        return False
    deep_events = [event for event in events if MIN_BOTTOM_Z <= event.bottom <= MAX_BOTTOM_Z]
    if len(unique_centers(deep_events)) != len(SAFE_POINTS):
        return False
    if match_points(unique_centers(deep_events)) is None:
        return False
    deepest_by_center: list[float] = []
    for center in all_centers:
        bottoms = [event.bottom for event in deep_events if math.dist(center, (event.x, event.y)) <= XY_TOL]
        if not bottoms:
            return False
        deepest_by_center.append(min(bottoms))
    if max(deepest_by_center) - min(deepest_by_center) > 1.5:
        return False

    for event in program.cycle_events:
        if event.cycle not in {73, 81, 82, 83}:
            return False
        if event.cycle in {73, 83} and (event.q is None or event.q <= 0):
            return False
    cycle_sections = {event.section for event in program.cycle_events}
    for section_index in cycle_sections:
        section_start = program.sections[section_index].line
        section_end = (
            program.sections[section_index + 1].line
            if section_index + 1 < len(program.sections)
            else program.m30_lines[0]
        )
        last_event_line = max(event.line for event in program.cycle_events if event.section == section_index)
        tail = "\n".join(program.code_lines[last_event_line + 1:section_end + 1])
        if not re.search(r"\bG0*80\b", tail):
            return False

    if not safe_motion(program, events, frame):
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
