from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_TARGET = r"C:\Users\User\Desktop"
TARGET = Path(os.environ.get("EVAL_TARGET_DIR", os.environ.get("OUTPUT_ROOT", DEFAULT_TARGET)))
OUTPUT_NAME = "task-13.nc"
WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))", re.IGNORECASE)
COMMENT_RE = re.compile(r"\([^()]*\)")
LINEAR_TOL = 1.5
Z_TOL = 0.65


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
    operation: str | None
    spindle_on: bool
    feed: float | None
    explicit_feed: float | None
    cutter_comp: int | None
    tool_diameter: float | None


@dataclass
class Section:
    tool: int
    tool_diameter: float | None
    records: list[Record] = field(default_factory=list)
    has_g43: bool = False


@dataclass
class Program:
    records: list[Record] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    units_seen: set[int] = field(default_factory=set)
    axes_seen: set[str] = field(default_factory=set)
    m_codes_seen: set[int] = field(default_factory=set)
    m30_lines: list[int] = field(default_factory=list)
    code_lines: list[str] = field(default_factory=list)


@dataclass
class Rectangle:
    z: float
    section: int
    center: tuple[float, float]
    axis: tuple[float, float]
    normal: tuple[float, float]
    long_dim: float
    short_dim: float
    compensated: bool
    tool_diameter: float | None


@dataclass
class FacePattern:
    z: float
    tracks: int
    along_span: float
    cross_span: float
    tool_diameter: float | None


def close(left: float, right: float, tolerance: float = LINEAR_TOL) -> bool:
    return abs(float(left) - float(right)) <= tolerance


def code_only(raw: str) -> str:
    return COMMENT_RE.sub(" ", raw.upper()).split(";", 1)[0]


def operation_from_comments(raw: str, current: str | None) -> str | None:
    for comment in COMMENT_RE.findall(raw.upper()):
        if re.search(r"\b(?:CONTOUR|PROFILE)\b", comment):
            current = "profile"
        elif re.search(r"\bFACE(?:\s+MILL(?:ING)?)?\b", comment):
            current = "face"
    return current


def diameter_from_comments(raw: str) -> float | None:
    for comment in COMMENT_RE.findall(raw.upper()):
        metric = re.search(r"\b(\d+(?:\.\d+)?)\s*MM\b", comment)
        if metric:
            candidate = float(metric.group(1))
            return candidate if 1.0 <= candidate <= 100.0 else None
        inch = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:IN|INCH)\b", comment)
        if inch:
            candidate = float(inch.group(1)) * 25.4
            return candidate if 1.0 <= candidate <= 100.0 else None
        body = comment[1:-1].strip()
        fraction = re.search(r"^(\d{1,2})\s*/\s*(\d{1,2})\s+(?:EM|END\s+MILL)\b", body)
        if fraction:
            numerator, denominator = map(int, fraction.groups())
            if (
                denominator in {2, 4, 8, 16, 32, 64}
                and 0 < numerator < denominator
                and math.gcd(numerator, denominator) == 1
            ):
                candidate = numerator / denominator * 25.4
                return candidate if 1.0 <= candidate <= 100.0 else None
    return None


def parse_program(source: str) -> Program:
    program = Program()
    position: dict[str, float | None] = {"x": None, "y": None, "z": None}
    unit_scale: float | None = None
    absolute = True
    wcs: str | None = None
    operation: str | None = None
    pending_tool_diameter: float | None = None
    pending_tool_diameter_line: int | None = None
    pending_tool: int | None = None
    current_tool: int | None = None
    section_index: int | None = None
    modal_motion: int | None = None
    spindle_on = False
    modal_feed: float | None = None
    cutter_comp: int | None = None

    for line_number, raw in enumerate(source.splitlines()):
        operation = operation_from_comments(raw, operation)
        diameter_hint = diameter_from_comments(raw)
        if diameter_hint is not None:
            pending_tool_diameter = diameter_hint
            pending_tool_diameter_line = line_number
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
        for letter, value in words:
            if letter == "T":
                pending_tool = int(round(value))
            if letter in {"X", "Y", "Z", "A", "B", "C", "U", "V", "W"}:
                program.axes_seen.add(letter)
        if 6 in m_codes:
            if pending_tool is None or pending_tool <= 0:
                raise ValueError("M6 without a valid tool")
            current_tool = pending_tool
            recent_diameter = (
                pending_tool_diameter
                if pending_tool_diameter_line is not None and line_number - pending_tool_diameter_line <= 3
                else None
            )
            program.sections.append(Section(current_tool, recent_diameter))
            section_index = len(program.sections) - 1
            pending_tool_diameter = None
            pending_tool_diameter_line = None
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
        if 40 in g_codes:
            cutter_comp = None
        if 41 in g_codes or 42 in g_codes:
            cutter_comp = 41 if 41 in g_codes else 42
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
            feeds = [value * unit_scale for letter, value in words if letter == "F"]
            if feeds:
                modal_feed = feeds[-1]
        explicit_feed = feeds[-1] if unit_scale is not None and feeds else None
        machine_coordinate = 53 in g_codes or 28 in g_codes or 30 in g_codes
        start = dict(position)
        if not machine_coordinate and unit_scale is not None:
            for axis in ("x", "y", "z"):
                if axis not in converted:
                    continue
                if absolute:
                    position[axis] = converted[axis]
                elif position[axis] is not None:
                    position[axis] += converted[axis]
                else:
                    raise ValueError("incremental motion before a known work position")
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
            operation,
            spindle_on,
            modal_feed,
            explicit_feed,
            cutter_comp,
            program.sections[section_index].tool_diameter,
        )
        program.records.append(record)
        program.sections[section_index].records.append(record)
    return program


def point(record: Record, which: str = "end") -> tuple[float, float] | None:
    state = record.start if which == "start" else record.end
    if state["x"] is None or state["y"] is None:
        return None
    return float(state["x"]), float(state["y"])


def xy_length(record: Record) -> float:
    start, end = point(record, "start"), point(record)
    return 0.0 if start is None or end is None else math.dist(start, end)


def is_xy_cut(record: Record) -> bool:
    return record.motion in {1, 2, 3} and (
        xy_length(record) > 1.0e-6
        or (record.motion in {2, 3} and any(axis in record.explicit for axis in ("i", "j", "r")))
    )


def project(value: tuple[float, float], axis: tuple[float, float]) -> float:
    return value[0] * axis[0] + value[1] * axis[1]


def cluster_tracks(items: list[tuple[float, float, float]], tolerance: float = 1.2):
    clusters: list[dict[str, object]] = []
    for fixed, low, high in sorted(items):
        target = next((item for item in clusters if abs(float(item["fixed"]) - fixed) <= tolerance), None)
        if target is None:
            clusters.append({"fixed": fixed, "values": [fixed], "intervals": [(low, high)]})
        else:
            values = target["values"]
            intervals = target["intervals"]
            assert isinstance(values, list) and isinstance(intervals, list)
            values.append(fixed)
            intervals.append((low, high))
            target["fixed"] = sum(values) / len(values)
    return clusters


def covered_fraction(intervals: list[tuple[float, float]], low: float, high: float) -> float:
    clipped = sorted((max(low, a), min(high, b)) for a, b in intervals if min(high, b) > max(low, a))
    if not clipped or high <= low:
        return 0.0
    merged: list[list[float]] = []
    for left, right in clipped:
        if not merged or left > merged[-1][1] + 1.0:
            merged.append([left, right])
        else:
            merged[-1][1] = max(merged[-1][1], right)
    return sum(right - left for left, right in merged) / (high - low)


def rectangles_at_level(records: list[Record], z: float, section: int) -> list[Rectangle]:
    straight = [
        record
        for record in records
        if record.section == section
        and record.motion == 1
        and record.end["z"] is not None
        and close(float(record.end["z"]), z, 0.3)
        and xy_length(record) >= 8.0
    ]
    found: list[Rectangle] = []
    for seed in straight:
        start, end = point(seed, "start"), point(seed)
        assert start is not None and end is not None
        delta = (end[0] - start[0], end[1] - start[1])
        length = math.hypot(*delta)
        axis = (delta[0] / length, delta[1] / length)
        normal = (-axis[1], axis[0])
        along: list[tuple[float, float, float]] = []
        across: list[tuple[float, float, float]] = []
        for record in straight:
            left, right = point(record, "start"), point(record)
            assert left is not None and right is not None
            vector = (right[0] - left[0], right[1] - left[1])
            segment_length = math.hypot(*vector)
            if segment_length <= 1.0e-9:
                continue
            direction = (vector[0] / segment_length, vector[1] / segment_length)
            if abs(direction[0] * axis[0] + direction[1] * axis[1]) >= 0.995:
                values = sorted((project(left, axis), project(right, axis)))
                along.append(((project(left, normal) + project(right, normal)) / 2.0, *values))
            elif abs(direction[0] * normal[0] + direction[1] * normal[1]) >= 0.995:
                values = sorted((project(left, normal), project(right, normal)))
                across.append(((project(left, axis) + project(right, axis)) / 2.0, *values))
        u_tracks, v_tracks = cluster_tracks(along), cluster_tracks(across)
        for first_u_index, first_u in enumerate(u_tracks):
            for second_u in u_tracks[first_u_index + 1 :]:
                v_low, v_high = sorted((float(first_u["fixed"]), float(second_u["fixed"])))
                for first_v_index, first_v in enumerate(v_tracks):
                    for second_v in v_tracks[first_v_index + 1 :]:
                        u_low, u_high = sorted((float(first_v["fixed"]), float(second_v["fixed"])))
                        dimensions = sorted((u_high - u_low, v_high - v_low), reverse=True)
                        compensated = any(record.cutter_comp in {41, 42} for record in straight)
                        diameter = next((record.tool_diameter for record in straight if record.tool_diameter), None)
                        nominal_path = close(dimensions[0], 70.0, 3.0) and close(dimensions[1], 50.0, 3.0)
                        tool_center_offset_path = (
                            diameter is not None
                            and close(dimensions[0], 70.0 + diameter, 3.0)
                            and close(dimensions[1], 50.0 + diameter, 3.0)
                        )
                        if not (nominal_path or tool_center_offset_path):
                            continue
                        edge_items = (first_u, second_u, first_v, second_v)
                        spans = (
                            covered_fraction(first_u["intervals"], u_low, u_high),
                            covered_fraction(second_u["intervals"], u_low, u_high),
                            covered_fraction(first_v["intervals"], v_low, v_high),
                            covered_fraction(second_v["intervals"], v_low, v_high),
                        )
                        if min(spans) < 0.72:
                            continue
                        center_u, center_v = (u_low + u_high) / 2.0, (v_low + v_high) / 2.0
                        center = (
                            center_u * axis[0] + center_v * normal[0],
                            center_u * axis[1] + center_v * normal[1],
                        )
                        long_axis, short_axis = axis, normal
                        if u_high - u_low < v_high - v_low:
                            long_axis, short_axis = normal, (-axis[0], -axis[1])
                        found.append(
                            Rectangle(
                                z,
                                section,
                                center,
                                long_axis,
                                short_axis,
                                dimensions[0],
                                dimensions[1],
                                compensated,
                                diameter,
                            )
                        )
    unique: list[Rectangle] = []
    for item in found:
        if not any(
            close(item.long_dim, old.long_dim, 0.8)
            and close(item.short_dim, old.short_dim, 0.8)
            and math.dist(item.center, old.center) <= 1.0
            for old in unique
        ):
            unique.append(item)
    return unique


def find_profile(records: list[Record]) -> Rectangle | None:
    candidates: list[Rectangle] = []
    sections = sorted({record.section for record in records})
    for section in sections:
        levels = sorted(
            {
                round(float(record.end["z"]), 2)
                for record in records
                if record.section == section and record.end["z"] is not None and is_xy_cut(record)
            }
        )
        for level in levels:
            candidates.extend(rectangles_at_level(records, level, section))
    return min(candidates, key=lambda item: item.z) if candidates else None


def local(value: tuple[float, float], rectangle: Rectangle) -> tuple[float, float]:
    delta = (value[0] - rectangle.center[0], value[1] - rectangle.center[1])
    return project(delta, rectangle.axis), project(delta, rectangle.normal)


def same_point(left: Record, right: Record, tolerance: float = 0.08) -> bool:
    left_point, right_point = point(left), point(right, "start")
    if left_point is None or right_point is None:
        return False
    left_z, right_z = left.end["z"], right.start["z"]
    return (
        math.dist(left_point, right_point) <= tolerance
        and left_z is not None
        and right_z is not None
        and close(float(left_z), float(right_z), tolerance)
    )


def segment_intersects_nominal_interior(
    start: tuple[float, float], end: tuple[float, float]
) -> bool:
    # Liang-Barsky against a slightly shrunken open 70 x 50 mm rectangle.
    xmin, xmax, ymin, ymax = -34.95, 34.95, -24.95, 24.95
    dx, dy = end[0] - start[0], end[1] - start[1]
    p = (-dx, dx, -dy, dy)
    q = (start[0] - xmin, xmax - start[0], start[1] - ymin, ymax - start[1])
    low, high = 0.0, 1.0
    for denominator, numerator in zip(p, q):
        if abs(denominator) <= 1.0e-12:
            if numerator < 0.0:
                return False
            continue
        ratio = numerator / denominator
        if denominator < 0.0:
            low = max(low, ratio)
        else:
            high = min(high, ratio)
        if low > high:
            return False
    return True


def valid_zero_feed_link(record: Record, records: list[Record], profile: Rectangle) -> bool:
    if record.motion != 1 or record.explicit_feed is None or abs(record.explicit_feed) > 1.0e-9:
        return False
    if record.start["z"] is None or record.end["z"] is None:
        return False
    if not close(float(record.start["z"]), float(record.end["z"]), 0.05):
        return False
    start, end = point(record, "start"), point(record)
    if start is None or end is None:
        return False
    try:
        index = records.index(record)
    except ValueError:
        return False
    neighbors = []
    if index > 0:
        neighbors.append((records[index - 1], same_point(records[index - 1], record)))
    if index + 1 < len(records):
        neighbors.append((records[index + 1], same_point(record, records[index + 1])))
    if not any(
        shared
        and neighbor.motion == 1
        and neighbor.feed is not None
        and neighbor.feed > 0
        and neighbor.end["z"] is not None
        and close(float(neighbor.end["z"]), float(record.end["z"]), 0.05)
        for neighbor, shared in neighbors
    ):
        return False
    return not segment_intersects_nominal_interior(local(start, profile), local(end, profile))


def face_patterns(records: list[Record], rectangle: Rectangle) -> list[FacePattern]:
    result: list[FacePattern] = []
    for section in sorted({record.section for record in records}):
        levels = sorted(
            {
                round(float(record.end["z"]), 2)
                for record in records
                if record.section == section and record.end["z"] is not None and is_xy_cut(record)
            }
        )
        for level in levels:
            level_records = [
                record
                for record in records
                if record.section == section
                and record.motion == 1
                and record.feed is not None
                and record.feed > 0
                and record.end["z"] is not None
                and close(float(record.end["z"]), level, 0.3)
                and xy_length(record) >= 8.0
            ]
            for direction, cross_direction, nominal_along, nominal_cross in (
                (rectangle.axis, rectangle.normal, 70.0, 50.0),
                (rectangle.normal, rectangle.axis, 50.0, 70.0),
            ):
                tracks: list[tuple[float, float, float]] = []
                for record in level_records:
                    start, end = point(record, "start"), point(record)
                    assert start is not None and end is not None
                    vector = (end[0] - start[0], end[1] - start[1])
                    length = math.hypot(*vector)
                    alignment = abs((vector[0] * direction[0] + vector[1] * direction[1]) / length)
                    if alignment < 0.995 or length < nominal_along * 0.72:
                        continue
                    along = sorted((project(start, direction), project(end, direction)))
                    cross = (project(start, cross_direction) + project(end, cross_direction)) / 2.0
                    tracks.append((cross, along[0], along[1]))
                clustered = cluster_tracks(tracks)
                if not clustered:
                    continue
                cross_values = [float(item["fixed"]) for item in clustered]
                along_low = min(low for _, low, _ in tracks)
                along_high = max(high for _, _, high in tracks)
                center_cross = project(rectangle.center, cross_direction)
                center_along = project(rectangle.center, direction)
                cross_span = max(cross_values) - min(cross_values)
                tool_diameter = next((record.tool_diameter for record in level_records if record.tool_diameter), None)
                if tool_diameter is not None and not 3.0 <= tool_diameter <= 100.0:
                    continue
                radius = (tool_diameter or 0.0) / 2.0
                if along_high - along_low + 2.0 * radius < nominal_along - 2.0:
                    continue
                if not (
                    along_low - radius <= center_along - nominal_along / 2.0 + 2.0
                    and along_high + radius >= center_along + nominal_along / 2.0 - 2.0
                ):
                    continue
                if cross_span + 2.0 * radius < nominal_cross - 2.0:
                    continue
                if not (
                    min(cross_values) - radius <= center_cross - nominal_cross / 2.0 + 2.0
                    and max(cross_values) + radius >= center_cross + nominal_cross / 2.0 - 2.0
                ):
                    continue
                result.append(
                    FacePattern(float(level), len(clustered), along_high - along_low, cross_span, tool_diameter)
                )
    return result


def has_interior_deep_cut(records: list[Record], rectangle: Rectangle, face_z: float) -> bool:
    for record in records:
        if not is_xy_cut(record) or record.end["z"] is None or float(record.end["z"]) > face_z - 1.0:
            continue
        start, end = point(record, "start"), point(record)
        if start is None or end is None or xy_length(record) < 3.0:
            continue
        middle = ((start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0)
        u, v = local(middle, rectangle)
        if abs(u) < 30.0 and abs(v) < 20.0:
            return True
    return False


def safe_rapids(program: Program, face_z: dict[str, float]) -> bool:
    for record in program.records:
        if record.motion != 0 or xy_length(record) <= 1.0e-6 or record.wcs not in face_z:
            continue
        heights = [float(value) for value in (record.start["z"], record.end["z"]) if value is not None]
        if heights and min(heights) < face_z[record.wcs] + 0.9:
            return False
    return True


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
    xy_cuts = [record for record in program.records if is_xy_cut(record)]
    if len(xy_cuts) < 20 or {record.wcs for record in xy_cuts} != {"G54", "G55"}:
        return False
    if any(record.operation not in {"face", "profile"} for record in xy_cuts):
        return False
    if any(not record.spindle_on for record in xy_cuts):
        return False
    used_sections = {record.section for record in xy_cuts}
    if any(not program.sections[index].has_g43 for index in used_sections):
        return False

    profiles: dict[str, Rectangle] = {}
    faces: dict[str, FacePattern] = {}
    for wcs in ("G54", "G55"):
        profile_records = [record for record in xy_cuts if record.wcs == wcs and record.operation == "profile"]
        face_records = [record for record in xy_cuts if record.wcs == wcs and record.operation == "face"]
        profile = find_profile(profile_records)
        if profile is None:
            return False
        for record in profile_records:
            if record.feed is None or record.feed <= 0:
                return False
        for record in face_records:
            if record.feed is not None and record.feed > 0:
                continue
            if not valid_zero_feed_link(record, face_records, profile):
                return False
        candidates = [
            item
            for item in face_patterns(face_records, profile)
            if 11.0 <= item.z - profile.z <= 14.5
        ]
        if not candidates:
            return False
        face = max(candidates, key=lambda item: (item.tracks, item.along_span))
        if has_interior_deep_cut(profile_records, profile, face.z):
            return False
        profiles[wcs], faces[wcs] = profile, face

    first_profile, second_profile = profiles["G54"], profiles["G55"]
    if not close(first_profile.long_dim, second_profile.long_dim, 2.0):
        return False
    if not close(first_profile.short_dim, second_profile.short_dim, 2.0):
        return False
    first_depth = faces["G54"].z - first_profile.z
    second_depth = faces["G55"].z - second_profile.z
    if not close(first_depth, second_depth, 1.5):
        return False
    if abs(faces["G54"].tracks - faces["G55"].tracks) > 1:
        return False
    if not close(faces["G54"].along_span, faces["G55"].along_span, 3.0):
        return False
    diameters = (faces["G54"].tool_diameter, faces["G55"].tool_diameter)
    if None not in diameters and not close(float(diameters[0]), float(diameters[1]), 0.5):
        return False
    if not safe_rapids(program, {name: faces[name].z for name in faces}):
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
