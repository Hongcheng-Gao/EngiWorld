from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_TARGET = r"C:\Users\User\Desktop"
TARGET = Path(os.environ.get("EVAL_TARGET_DIR", os.environ.get("OUTPUT_ROOT", DEFAULT_TARGET)))
OUTPUT_NAME = "task-7.nc"

DEPTH_TOL_MM = 0.35
GEOMETRY_TOL_MM = 1.25
SAFE_CLEARANCE_MM = 0.5

WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))", re.IGNORECASE)
PAREN_COMMENT_RE = re.compile(r"\(([^()]*)\)")
ROUGH_COMMENT_RE = re.compile(r"\b(?:ROUGH(?:\s+MILL)?|POCKET)\b", re.IGNORECASE)
FINISH_COMMENT_RE = re.compile(r"\b(?:CONTOUR(?:\s+MILL)?|PROFILE|FINISH)\b", re.IGNORECASE)


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
    kind: str
    header_line: int
    records: tuple[Record, ...]


def close(left: float, right: float, tolerance: float = GEOMETRY_TOL_MM) -> bool:
    return abs(float(left) - float(right)) <= tolerance


def split_line(raw: str) -> str:
    code = PAREN_COMMENT_RE.sub(" ", raw.upper())
    return code.split(";", 1)[0]


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
                raise ValueError("M6 without a valid selected tool")
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

        if unit_scale is None:
            converted: dict[str, float] = {}
        else:
            converted = {
                letter.lower(): value * unit_scale
                for letter, value in words
                if letter in {"X", "Y", "Z", "I", "J", "K", "R"}
            }
            feed_words = [value * unit_scale for letter, value in words if letter == "F"]
            if feed_words:
                modal_feed = feed_words[-1]

        # G28/G30 values are intermediate/reference-return values, not work coordinates.
        machine_reference_return = 28 in g_codes or 30 in g_codes
        start = dict(position)
        if not machine_reference_return and unit_scale is not None:
            for axis in ("x", "y", "z"):
                if axis not in converted:
                    continue
                if absolute:
                    position[axis] = converted[axis]
                elif position[axis] is not None:
                    position[axis] += converted[axis]
                else:
                    raise ValueError("incremental move before an absolute work position")

        if machine_reference_return or current_tool is None or modal_motion is None:
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


def cutting_xy(program: Program) -> list[Record]:
    return [
        record for record in program.records
        if record.motion in {1, 2, 3} and xy_changed(record)
    ]


def record_points(record: Record) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for state in (record.start, record.end):
        if state["x"] is not None and state["y"] is not None:
            points.append((state["x"], state["y"]))
    return points


def bbox(records: list[Record]) -> tuple[float, float, float, float] | None:
    points = [point for record in records for point in record_points(record)]
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), max(xs), min(ys), max(ys)


def distinct_levels(records: list[Record]) -> list[float]:
    return sorted(
        {round(record.end["z"], 3) for record in records if record.end["z"] is not None},
        reverse=True,
    )


def spatial_cluster(records: list[Record], gap: float = 20.0) -> list[list[Record]]:
    """Cluster disconnected rough/finish passes that occupy the same local feature."""
    groups: list[list[Record]] = []
    for record in records:
        points = record_points(record)
        if not points:
            continue
        center = (
            sum(point[0] for point in points) / len(points),
            sum(point[1] for point in points) / len(points),
        )
        for group in groups:
            group_points = [point for item in group for point in record_points(item)]
            group_center = (
                sum(point[0] for point in group_points) / len(group_points),
                sum(point[1] for point in group_points) / len(group_points),
            )
            if math.hypot(center[0] - group_center[0], center[1] - group_center[1]) <= gap:
                group.append(record)
                break
        else:
            groups.append([record])
    return groups


def normalized_spans(bounds: tuple[float, float, float, float]) -> tuple[float, float]:
    width = bounds[1] - bounds[0]
    height = bounds[3] - bounds[2]
    return max(width, height), min(width, height)


def rectangle_loop(records: list[Record], minimum_long: float, minimum_short: float) -> bool:
    horizontal: list[tuple[float, float, float]] = []
    vertical: list[tuple[float, float, float]] = []
    for record in records:
        start, end = record.start, record.end
        if None in (start["x"], start["y"], end["x"], end["y"]):
            continue
        dx = abs(end["x"] - start["x"])
        dy = abs(end["y"] - start["y"])
        if dy <= 0.5 and dx >= 2.0:
            horizontal.append(((start["y"] + end["y"]) / 2.0, min(start["x"], end["x"]), max(start["x"], end["x"])))
        if dx <= 0.5 and dy >= 2.0:
            vertical.append(((start["x"] + end["x"]) / 2.0, min(start["y"], end["y"]), max(start["y"], end["y"])))
    if len(horizontal) < 2 or len(vertical) < 2:
        return False

    left = min(track[0] for track in vertical)
    right = max(track[0] for track in vertical)
    bottom = min(track[0] for track in horizontal)
    top = max(track[0] for track in horizontal)
    x_span, y_span = right - left, top - bottom
    long_span, short_span = max(x_span, y_span), min(x_span, y_span)
    if long_span < minimum_long or short_span < minimum_short:
        return False

    edge_tolerance = max(GEOMETRY_TOL_MM, 0.03 * short_span)

    def merged_coverage(intervals: list[tuple[float, float]]) -> float:
        if not intervals:
            return 0.0
        merged: list[list[float]] = []
        for start, end in sorted(intervals):
            if not merged or start > merged[-1][1] + edge_tolerance:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)
        return sum(end - start for start, end in merged)

    bottom_intervals = [(start, end) for coordinate, start, end in horizontal if abs(coordinate - bottom) <= edge_tolerance]
    top_intervals = [(start, end) for coordinate, start, end in horizontal if abs(coordinate - top) <= edge_tolerance]
    left_intervals = [(start, end) for coordinate, start, end in vertical if abs(coordinate - left) <= edge_tolerance]
    right_intervals = [(start, end) for coordinate, start, end in vertical if abs(coordinate - right) <= edge_tolerance]
    return (
        merged_coverage(bottom_intervals) >= 0.70 * x_span
        and merged_coverage(top_intervals) >= 0.70 * x_span
        and merged_coverage(left_intervals) >= 0.70 * y_span
        and merged_coverage(right_intervals) >= 0.70 * y_span
    )


def operation_headers(source: str) -> list[tuple[int, str]]:
    headers: list[tuple[int, str]] = []
    for line_number, raw in enumerate(source.splitlines()):
        comments = " ".join(PAREN_COMMENT_RE.findall(raw.upper()))
        if ROUGH_COMMENT_RE.search(comments):
            headers.append((line_number, "rough"))
        elif FINISH_COMMENT_RE.search(comments):
            headers.append((line_number, "finish"))
    return headers


def operations(program: Program, source: str) -> list[Operation]:
    headers = operation_headers(source)
    result: list[Operation] = []
    for index, (line, kind) in enumerate(headers):
        end = headers[index + 1][0] if index + 1 < len(headers) else 10**12
        records = tuple(record for record in program.records if line < record.line < end)
        if records:
            result.append(Operation(kind, line, records))
    return result


def feature_clusters(records: list[Record], gap: float = 25.0) -> list[list[Record]]:
    groups: list[list[Record]] = []
    for record in records:
        points = record_points(record)
        if not points:
            continue
        center = (
            sum(point[0] for point in points) / len(points),
            sum(point[1] for point in points) / len(points),
        )
        for group in groups:
            group_points = [point for item in group for point in record_points(item)]
            group_center = (
                sum(point[0] for point in group_points) / len(group_points),
                sum(point[1] for point in group_points) / len(group_points),
            )
            if math.dist(center, group_center) <= gap:
                group.append(record)
                break
        else:
            groups.append([record])
    return groups


def operation_pocket_clusters(
    records: list[Record], *, minimum_records: int, require_loop: bool,
) -> list[list[Record]]:
    candidates: list[list[Record]] = []
    for group in feature_clusters(records):
        bounds = bbox(group)
        if bounds is None or len(group) < minimum_records:
            continue
        long_span, short_span = normalized_spans(bounds)
        if not (18.0 <= long_span <= 55.0 and 8.0 <= short_span <= 40.0):
            continue
        if require_loop and not rectangle_loop(group, 18.0, 8.0):
            continue
        candidates.append(group)
    return candidates


def cluster_center(records: list[Record]) -> tuple[float, float]:
    bounds = bbox(records)
    if bounds is None:
        raise ValueError("cluster without bounds")
    return (bounds[0] + bounds[1]) / 2.0, (bounds[2] + bounds[3]) / 2.0


def clears_pocket_area(records: list[Record]) -> bool:
    bounds = bbox(records)
    if bounds is None:
        return False
    cx, cy = cluster_center(records)
    width, height = bounds[1] - bounds[0], bounds[3] - bounds[2]
    core_hits = 0
    for record in records:
        points = record_points(record)
        if not points:
            continue
        midpoint = (
            sum(point[0] for point in points) / len(points),
            sum(point[1] for point in points) / len(points),
        )
        if abs(midpoint[0] - cx) <= 0.30 * width and abs(midpoint[1] - cy) <= 0.30 * height:
            core_hits += 1
    return core_hits >= 3


def two_separate_matching(rough: list[list[Record]], finish: list[list[Record]]) -> bool:
    for first_index, first in enumerate(rough):
        for second in rough[first_index + 1:]:
            rough_centers = [cluster_center(first), cluster_center(second)]
            if math.dist(*rough_centers) < 35.0:
                continue
            remaining = list(finish)
            for expected in rough_centers:
                match = min(
                    remaining,
                    key=lambda candidate: math.dist(expected, cluster_center(candidate)),
                    default=None,
                )
                if match is None or math.dist(expected, cluster_center(match)) > 7.0:
                    break
                remaining.remove(match)
            else:
                return True
    return False


def ordered_operation_matching(
    rough: list[tuple[int, list[Record]]], finish: list[tuple[int, list[Record]]],
) -> bool:
    """Match two separated pockets and require each rough section before its finish."""
    for first_index, (first_line, first) in enumerate(rough):
        for second_line, second in rough[first_index + 1:]:
            rough_items = [(first_line, first), (second_line, second)]
            if math.dist(cluster_center(first), cluster_center(second)) < 35.0:
                continue
            remaining = list(finish)
            for rough_line, rough_records in rough_items:
                expected = cluster_center(rough_records)
                match = min(
                    remaining,
                    key=lambda item: math.dist(expected, cluster_center(item[1])),
                    default=None,
                )
                if (
                    match is None
                    or math.dist(expected, cluster_center(match[1])) > 7.0
                    or rough_line >= match[0]
                ):
                    break
                remaining.remove(match)
            else:
                return True
    return False


def pocket_candidates(records: list[Record]) -> list[tuple[list[Record], tuple[float, float, float, float]]]:
    local_records = []
    for record in records:
        points = record_points(record)
        if not points:
            continue
        span_x = max(point[0] for point in points) - min(point[0] for point in points)
        span_y = max(point[1] for point in points) - min(point[1] for point in points)
        # Exclude the outside profile if the evaluator is considering a level
        # shared by pocket and perimeter operations.
        if span_x > 65.0 or span_y > 65.0:
            continue
        local_records.append(record)
    candidates = []
    for component in spatial_cluster(local_records):
        bounds = bbox(component)
        if bounds is None:
            continue
        left, right, bottom, top = bounds
        width, height = right - left, top - bottom
        if 8.0 <= min(width, height) and max(width, height) <= 55.0 and len(component) >= 4:
            candidates.append((component, bounds))
    return candidates


def has_two_pockets_at(records: list[Record]) -> bool:
    candidates = pocket_candidates(records)
    for first_index, (_first, a) in enumerate(candidates):
        for _second, b in candidates[first_index + 1:]:
            ac = ((a[0] + a[1]) / 2.0, (a[2] + a[3]) / 2.0)
            bc = ((b[0] + b[1]) / 2.0, (b[2] + b[3]) / 2.0)
            if math.hypot(ac[0] - bc[0], ac[1] - bc[1]) < 35.0:
                continue
            if abs((a[1] - a[0]) - (b[1] - b[0])) > 8.0:
                continue
            if abs((a[3] - a[2]) - (b[3] - b[2])) > 8.0:
                continue
            return True
    return False


def robust_two_pocket_test(records: list[Record]) -> bool:
    candidates = pocket_candidates(records)
    valid = []
    for component, bounds in candidates:
        if rectangle_loop(component, 18.0, 8.0) and len(component) >= 4:
            valid.append((component, bounds))
    return has_two_pockets_at([record for component, _bounds in valid for record in component])


def safe_traverses(program: Program) -> bool:
    for record in program.records:
        if record.motion not in {0, 1} or not xy_changed(record):
            continue
        if record.end["z"] is None or record.end["z"] >= SAFE_CLEARANCE_MM:
            continue
        # Low XY motion is allowed only for an actual feed cut with spindle and WCS.
        if record.motion != 1 or not record.spindle_on or record.wcs is None or record.feed is None or record.feed <= 0:
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
    if not program.tools or not ({0, 1} <= {record.motion for record in program.records}):
        return False
    if program.axes_seen & {"A", "B", "C", "U", "V", "W"}:
        return False
    if not {3, 6, 30} <= program.m_codes_seen or not program.has_tool_length_comp:
        return False
    if not program.m30_lines or program.m30_lines[-1] != max(program.m30_lines):
        return False
    if any(WORD_RE.search(line) for line in program.code_lines[program.m30_lines[-1] + 1:]):
        return False

    cuts = cutting_xy(program)
    if len(cuts) < 45 or any(not record.spindle_on or record.wcs is None or record.feed is None or record.feed <= 0 for record in cuts):
        return False
    if not safe_traverses(program):
        return False

    parsed_operations = operations(program, source)
    rough_operations = [operation for operation in parsed_operations if operation.kind == "rough"]
    finish_operations = [operation for operation in parsed_operations if operation.kind == "finish"]
    if not rough_operations or not finish_operations:
        return False
    rough_cuts = [
        record for operation in rough_operations for record in operation.records if record in cuts
    ]
    finish_cuts = [
        record for operation in finish_operations for record in operation.records if record in cuts
    ]
    if not rough_cuts or not finish_cuts:
        return False
    # Default operation comments delimit native sections, but the actual
    # section geometry below is the proof. A forged label alone cannot pass.
    if max(record.line for record in rough_cuts) >= min(record.line for record in finish_cuts):
        return False

    all_levels = distinct_levels(cuts)
    if not all_levels:
        return False
    outer_floor = min(all_levels)
    if outer_floor > -16.5:
        return False
    pocket_floor_candidates = [
        level for level in all_levels
        if 5.3 <= level - outer_floor <= 6.7
    ]
    if not pocket_floor_candidates:
        return False
    pocket_floor = min(pocket_floor_candidates, key=lambda level: abs((level - outer_floor) - 6.0))

    outer_records = [
        record for record in finish_cuts
        if record.end["z"] is not None and close(record.end["z"], outer_floor, DEPTH_TOL_MM)
    ]
    if not rectangle_loop(outer_records, 115.0, 70.0):
        return False
    outer_bounds = bbox(outer_records)
    if outer_bounds is None:
        return False
    outer_long, outer_short = normalized_spans(outer_bounds)
    if not (115.0 <= outer_long <= 165.0 and 70.0 <= outer_short <= 125.0):
        return False

    rough_sections: list[tuple[int, list[Record]]] = []
    for operation in rough_operations:
        records = [
            record for record in operation.records if record in cuts
            and record.end["z"] is not None
            and record.end["z"] >= pocket_floor - DEPTH_TOL_MM
            and record.end["z"] < SAFE_CLEARANCE_MM
        ]
        for cluster in operation_pocket_clusters(records, minimum_records=8, require_loop=False):
            if clears_pocket_area(cluster):
                rough_sections.append((operation.header_line, cluster))

    finish_sections: list[tuple[int, list[Record]]] = []
    for operation in finish_operations:
        records = [
            record for record in operation.records if record in cuts
            and record.end["z"] is not None
            and close(record.end["z"], pocket_floor, DEPTH_TOL_MM)
        ]
        for cluster in operation_pocket_clusters(records, minimum_records=4, require_loop=True):
            finish_sections.append((operation.header_line, cluster))

    return ordered_operation_matching(rough_sections, finish_sections)


def evaluate() -> bool:
    # The NC is the only submitted artifact.  Unrelated scripts elsewhere on
    # Desktop neither prove correctness nor invalidate a valid native program.
    return validate_nc(TARGET / OUTPUT_NAME)


if __name__ == "__main__":
    try:
        result = evaluate()
    except Exception:
        result = False
    print("True" if result else "False")
