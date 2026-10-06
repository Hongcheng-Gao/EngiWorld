from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_TARGET = r"C:\Users\User\Desktop"
TARGET = Path(os.environ.get("EVAL_TARGET_DIR", os.environ.get("OUTPUT_ROOT", DEFAULT_TARGET)))
OUTPUT_NAME = "task-12.nc"
WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))", re.IGNORECASE)
COMMENT_RE = re.compile(r"\([^()]*\)")
XY_TOL = 1.2
Z_TOL = 0.6


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
    feed: float | None
    cutter_comp: int | None


@dataclass
class Section:
    tool: int
    records: list[Record] = field(default_factory=list)
    has_g43: bool = False
    compensation: set[int] = field(default_factory=set)


@dataclass
class Program:
    records: list[Record] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    units_seen: set[int] = field(default_factory=set)
    axes_seen: set[str] = field(default_factory=set)
    m_codes_seen: set[int] = field(default_factory=set)
    m30_lines: list[int] = field(default_factory=list)
    code_lines: list[str] = field(default_factory=list)


def close(left: float, right: float, tolerance: float = XY_TOL) -> bool:
    return abs(float(left) - float(right)) <= tolerance


def code_only(raw: str) -> str:
    return COMMENT_RE.sub(" ", raw.upper()).split(";", 1)[0]


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
    spindle_on = False
    modal_feed: float | None = None
    cutter_comp: int | None = None

    for line_number, raw in enumerate(source.splitlines()):
        code = code_only(raw)
        program.code_lines.append(code)
        words = [(letter.upper(), float(value)) for letter, value in WORD_RE.findall(code)]
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
        if 91 in g_codes:
            absolute = False
        for value in g_codes:
            if 54 <= value <= 59:
                wcs = f"G{value}"
        if 40 in g_codes:
            cutter_comp = None
        if 41 in g_codes or 42 in g_codes:
            cutter_comp = 41 if 41 in g_codes else 42
        for letter, value in words:
            if letter == "T":
                pending_tool = int(round(value))
            if letter in {"X", "Y", "Z", "A", "B", "C", "U", "V", "W"}:
                program.axes_seen.add(letter)
        if 6 in m_codes:
            if pending_tool is None or pending_tool <= 0:
                raise ValueError("M6 without a valid tool")
            current_tool = pending_tool
            program.sections.append(Section(current_tool))
            section_index = len(program.sections) - 1
            spindle_on = False
            cutter_comp = None
        if 3 in m_codes or 4 in m_codes:
            spindle_on = True
        if 5 in m_codes:
            spindle_on = False
        if 30 in m_codes:
            program.m30_lines.append(line_number)
        if 43 in g_codes and section_index is not None:
            program.sections[section_index].has_g43 = True
        if cutter_comp is not None and section_index is not None:
            program.sections[section_index].compensation.add(cutter_comp)
        if 80 in g_codes:
            modal_motion = None
        explicit_motion = next((value for value in g_codes if value in {0, 1, 2, 3, 81, 82, 83, 84, 85, 86, 87, 88, 89}), None)
        if explicit_motion is not None:
            modal_motion = explicit_motion

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
        if machine_return or current_tool is None or section_index is None or modal_motion is None:
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
            modal_feed,
            cutter_comp,
        )
        program.records.append(record)
        program.sections[section_index].records.append(record)
    return program


def xy(record: Record, which: str = "end") -> tuple[float, float] | None:
    state = record.start if which == "start" else record.end
    if state["x"] is None or state["y"] is None:
        return None
    return float(state["x"]), float(state["y"])


def xy_changed(record: Record) -> bool:
    start, end = xy(record, "start"), xy(record)
    return start is not None and end is not None and math.dist(start, end) > 1.0e-6


def is_xy_cut(record: Record) -> bool:
    return record.motion in {1, 2, 3} and (
        xy_changed(record) or (record.motion in {2, 3} and any(axis in record.explicit for axis in ("i", "j", "r")))
    )


def unique_points(points: list[tuple[float, float]], tolerance: float = XY_TOL) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for point in points:
        if not any(math.dist(point, other) <= tolerance for other in result):
            result.append(point)
    return result


def drill_points(section: Section) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for record in section.records:
        point = xy(record)
        if point is None:
            continue
        if 81 <= record.motion <= 89:
            result.append(point)
            continue
        if record.motion == 1 and record.start["z"] is not None and record.end["z"] is not None:
            if not xy_changed(record) and float(record.start["z"]) - float(record.end["z"]) >= 10.0:
                result.append(point)
    return unique_points(result)


def frame_from_holes(points: list[tuple[float, float]]):
    if len(points) != 4:
        return None
    distances = sorted(math.dist(points[i], points[j]) for i in range(4) for j in range(i + 1, 4))
    expected = (40.0, 40.0, 70.0, 70.0, math.hypot(70.0, 40.0), math.hypot(70.0, 40.0))
    if any(not close(actual, target, 1.5) for actual, target in zip(distances, expected)):
        return None
    origin = (sum(point[0] for point in points) / 4.0, sum(point[1] for point in points) / 4.0)
    long_pairs = [
        (points[i], points[j])
        for i in range(4)
        for j in range(i + 1, 4)
        if close(math.dist(points[i], points[j]), 70.0, 1.5)
    ]
    if len(long_pairs) != 2:
        return None
    delta = (long_pairs[0][1][0] - long_pairs[0][0][0], long_pairs[0][1][1] - long_pairs[0][0][1])
    length = math.hypot(*delta)
    axis = (delta[0] / length, delta[1] / length)
    normal = (-axis[1], axis[0])
    local_points = [(local(point, (origin, axis, normal))) for point in points]
    if not all(close(abs(u), 35.0, 1.2) and close(abs(v), 20.0, 1.2) for u, v in local_points):
        return None
    return origin, axis, normal


def local(point: tuple[float, float], frame) -> tuple[float, float]:
    origin, axis, normal = frame
    delta = (point[0] - origin[0], point[1] - origin[1])
    return delta[0] * axis[0] + delta[1] * axis[1], delta[0] * normal[0] + delta[1] * normal[1]


def cut_z(record: Record) -> float | None:
    return None if record.end["z"] is None else float(record.end["z"])


def section_face(section: Section, frame):
    candidates = [record for record in section.records if is_xy_cut(record) and cut_z(record) is not None]
    if len(candidates) < 6:
        return None
    levels = sorted({round(cut_z(record), 2) for record in candidates})
    for level in levels:
        at_level = [record for record in candidates if close(cut_z(record), level, 0.25)]
        tracks: dict[float, list[float]] = {}
        for record in at_level:
            start, end = xy(record, "start"), xy(record)
            if start is None or end is None:
                continue
            u1, v1 = local(start, frame)
            u2, v2 = local(end, frame)
            if abs(v2 - v1) <= 0.35 and abs(u2 - u1) >= 20.0:
                key = round((v1 + v2) / 2.0, 1)
                tracks.setdefault(key, []).extend((u1, u2))
        covered = [(v, max(values) - min(values)) for v, values in tracks.items() if max(values) - min(values) >= 115.0]
        if len(covered) >= 3 and max(v for v, _ in covered) - min(v for v, _ in covered) >= 55.0:
            return float(level)
    return None


def profile_info(section: Section, frame, top: float):
    cuts = [record for record in section.records if is_xy_cut(record) and cut_z(record) is not None]
    if len(cuts) < 12 or not section.compensation:
        return None
    depths = sorted({round(top - cut_z(record), 2) for record in cuts if top - cut_z(record) > 0.5})
    if len(depths) < 3 or max(depths) < 13.5 or max(depths) > 15.0:
        return None
    if any(right - left > 8.0 for left, right in zip(depths, depths[1:])):
        return None
    floor = top - max(depths)
    floor_cuts = [record for record in cuts if close(cut_z(record), floor, Z_TOL)]
    horizontal: list[tuple[float, float, float]] = []
    vertical: list[tuple[float, float, float]] = []
    for record in floor_cuts:
        start, end = xy(record, "start"), xy(record)
        if start is None or end is None or record.motion not in {1, 2, 3}:
            continue
        u1, v1 = local(start, frame)
        u2, v2 = local(end, frame)
        if abs(v2 - v1) <= 0.4 and abs(u2 - u1) >= 55.0:
            horizontal.append((u1, u2, (v1 + v2) / 2.0))
        if abs(u2 - u1) <= 0.4 and abs(v2 - v1) >= 65.0:
            vertical.append((v1, v2, (u1 + u2) / 2.0))
    if len(horizontal) < 3 or len(vertical) < 2:
        return None
    u_values = [value for row in horizontal for value in row[:2]] + [row[2] for row in vertical]
    v_values = [row[2] for row in horizontal] + [value for row in vertical for value in row[:2]]
    width, height = max(u_values) - min(u_values), max(v_values) - min(v_values)
    center = ((max(u_values) + min(u_values)) / 2.0, (max(v_values) + min(v_values)) / 2.0)
    if not (120.0 <= width <= 145.0 and 80.0 <= height <= 105.0):
        return None
    if abs(center[0]) > 1.5 or abs(center[1]) > 1.5:
        return None
    return {"floor": floor, "width": width, "height": height}


def drill_depth_ok(section: Section, top: float) -> bool:
    depths: list[float] = []
    for record in section.records:
        if 81 <= record.motion <= 89 and record.end["z"] is not None:
            depths.append(top - float(record.end["z"]))
        elif record.motion == 1 and not xy_changed(record) and record.end["z"] is not None:
            depths.append(top - float(record.end["z"]))
    return bool(depths) and max(depths) >= 13.5


def safe_rapids(program: Program, top: float) -> bool:
    for record in program.records:
        if record.motion != 0 or not xy_changed(record):
            continue
        z_values = [float(value) for value in (record.start["z"], record.end["z"]) if value is not None]
        if z_values and min(z_values) < top + 3.0 - 0.15:
            return False
    return True


def section_ready(section: Section) -> bool:
    active = [record for record in section.records if record.motion in {1, 2, 3, 81, 82, 83, 84, 85, 86, 87, 88, 89}]
    return bool(active) and section.has_g43 and all(
        record.spindle_on and record.wcs is not None and record.feed is not None and record.feed > 0
        for record in active
    )


def read_nc(path: Path) -> str | None:
    try:
        if not path.is_file() or not 500 <= path.stat().st_size <= 2_000_000:
            return None
        data = path.read_bytes()
        if b"\x00" in data:
            return None
        source = data.decode("latin-1")
        printable = sum(ch in "\t\r\n" or 32 <= ord(ch) <= 126 for ch in source)
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
    if len(program.units_seen) != 1 or program.axes_seen & {"A", "B", "C", "U", "V", "W"}:
        return False
    if not {6, 30} <= program.m_codes_seen or not ({3, 4} & program.m_codes_seen):
        return False
    if len(program.m30_lines) != 1 or any(WORD_RE.search(line) for line in program.code_lines[program.m30_lines[0] + 1 :]):
        return False
    if not 4 <= len(program.sections) <= 7:
        return False
    used_tools = {section.tool for section in program.sections if section.records}
    if len(used_tools) < 4:
        return False
    if not all(section_ready(section) for section in program.sections if section.records):
        return False

    drill_candidates = [(section, drill_points(section)) for section in program.sections]
    drill_candidates = [(section, points) for section, points in drill_candidates if frame_from_holes(points) is not None]
    if len(drill_candidates) != 1:
        return False
    drill_section, holes = drill_candidates[0]
    frame = frame_from_holes(holes)
    if frame is None:
        return False
    faces = [(section, section_face(section, frame)) for section in program.sections]
    faces = [(section, top) for section, top in faces if top is not None]
    if len(faces) != 1:
        return False
    face_section, top = faces[0]
    if not drill_depth_ok(drill_section, top):
        return False
    profiles = [(section, profile_info(section, frame, top)) for section in program.sections]
    profiles = [(section, info) for section, info in profiles if info is not None]
    if len(profiles) != 2:
        return False
    required = {id(drill_section), id(face_section), *(id(section) for section, _ in profiles)}
    if len(required) != 4 or len({drill_section.tool, face_section.tool, *(section.tool for section, _ in profiles)}) != 4:
        return False
    if any(not close(info["floor"], top - 14.0, Z_TOL) for _, info in profiles):
        return False
    widths = sorted(info["width"] for _, info in profiles)
    heights = sorted(info["height"] for _, info in profiles)
    if widths[1] - widths[0] < 5.0 or heights[1] - heights[0] < 5.0:
        return False
    if not safe_rapids(program, top):
        return False
    for section in (drill_section, face_section, *(section for section, _ in profiles)):
        for record in section.records:
            if not is_xy_cut(record) or cut_z(record) is None or cut_z(record) >= top - 0.5:
                continue
            u, v = local(xy(record), frame)
            if section is face_section or (abs(u) < 55.0 and abs(v) < 32.0):
                return False
    for section in program.sections:
        if id(section) in required:
            continue
        if any(is_xy_cut(record) and cut_z(record) is not None and cut_z(record) < top - 0.5 for record in section.records):
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
