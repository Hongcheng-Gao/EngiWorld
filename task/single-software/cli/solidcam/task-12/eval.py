from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from pathlib import Path


TARGET = Path(os.environ.get("EVAL_TARGET_DIR", r"C:\Users\User\Desktop"))
NC_NAME = "task-12.nc"
MAX_BYTES = 1_000_000
MAX_LINES = 12_000
MAX_WORDS_PER_LINE = 40
MAX_SEGMENTS = 20_000
MAX_SAMPLES = 250_000
WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))")

PROGRAM = 2032
TOOLS = {
    1: {"diameter": 6.0, "spindle": 7200.0, "feed": 430.0},
    2: {"diameter": 6.0, "spindle": 7600.0, "feed": 520.0},
    3: {"diameter": 5.0, "spindle": 5000.0, "feed": 180.0},
    4: {"diameter": 12.0, "spindle": 9000.0, "feed": 650.0},
}
UPPER_RECTS = ((-37.0, -13.0, -12.0, 12.0), (-18.0, 18.0, -10.0, 10.0))
DEEP_RECT = (-18.0, 18.0, -10.0, 10.0)
HOLES = ((-30.0, -20.0), (-30.0, 20.0), (30.0, -20.0), (30.0, 20.0))
STOCK = (-60.0, 60.0, -40.0, 40.0)


class EvaluationError(ValueError):
    pass


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    z: float


@dataclass
class Segment:
    start: Point
    end: Point
    samples: list[Point]
    motion: int
    cycle: int | None
    tool: int | None
    spindle: float | None
    spindle_direction: int | None
    feed: float | None
    wcs: str | None
    plane17: bool
    length_comp: bool
    h_offset: int | None
    comp: int
    d_offset: int | None
    line_number: int


@dataclass
class Program:
    segments: list[Segment]
    selections: list[int]
    changes: list[int]
    programs: list[int]
    terminated: bool
    executable_lines: int


def close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def distance(a: Point, b: Point) -> float:
    return math.dist((a.x, a.y, a.z), (b.x, b.y, b.z))


def dense_line(a: Point, b: Point, spacing: float = 0.7) -> list[Point]:
    length = distance(a, b)
    if not math.isfinite(length) or length > 1000.0:
        raise EvaluationError("invalid or excessive segment length")
    count = max(1, int(math.ceil(length / spacing)))
    return [
        Point(a.x + (b.x - a.x) * i / count, a.y + (b.y - a.y) * i / count, a.z + (b.z - a.z) * i / count)
        for i in range(count + 1)
    ]


def strip_comments(src: str) -> list[str]:
    if len(src.encode("utf-8")) > MAX_BYTES:
        raise EvaluationError("NC file exceeds evaluator resource limit")
    raw_lines = src.upper().splitlines()
    if len(raw_lines) > MAX_LINES:
        raise EvaluationError("NC line count exceeds evaluator resource limit")
    output: list[str] = []
    depth = 0
    for raw in raw_lines:
        clean: list[str] = []
        for char in raw:
            if char == ";" and depth == 0:
                break
            if char == "(":
                depth += 1
                if depth > 8:
                    raise EvaluationError("excessive nested comment")
            elif char == ")":
                if depth == 0:
                    raise EvaluationError("unmatched comment close")
                depth -= 1
            elif depth == 0:
                clean.append(char)
        output.append("".join(clean).strip())
    if depth:
        raise EvaluationError("unterminated comment")
    return output


def exact_integer(value: float, label: str, minimum: int = 0, maximum: int = 1_000_000) -> int:
    if not math.isfinite(value):
        raise EvaluationError(f"non-finite {label}")
    integer = round(value)
    if abs(value - integer) > 1e-4 or integer < minimum or integer > maximum:
        raise EvaluationError(f"invalid integer {label}")
    return int(integer)


def arc_points(a: Point, b: Point, i: float, j: float, clockwise: bool) -> list[Point]:
    cx, cy = a.x + i, a.y + j
    radius = math.hypot(i, j)
    if radius <= 1e-6 or radius > 500.0 or not close(math.hypot(b.x - cx, b.y - cy), radius, 0.15):
        raise EvaluationError("invalid G17 arc")
    start_angle = math.atan2(a.y - cy, a.x - cx)
    end_angle = math.atan2(b.y - cy, b.x - cx)
    sweep = (start_angle - end_angle) % (2 * math.pi) if clockwise else (end_angle - start_angle) % (2 * math.pi)
    if sweep <= 1e-9:
        sweep = 2 * math.pi
    direction = -1.0 if clockwise else 1.0
    count = max(12, int(math.ceil(radius * sweep / 0.7)))
    return [
        Point(
            cx + radius * math.cos(start_angle + direction * sweep * k / count),
            cy + radius * math.sin(start_angle + direction * sweep * k / count),
            a.z + (b.z - a.z) * k / count,
        )
        for k in range(count + 1)
    ]


def parse_program(src: str) -> Program:
    units: str | None = None
    absolute: bool | None = None
    motion: int | None = None
    current = Point(0.0, 0.0, 0.0)
    pending_tool: int | None = None
    active_tool: int | None = None
    spindle: float | None = None
    spindle_direction: int | None = None
    feed: float | None = None
    wcs: str | None = None
    plane17 = False
    length_comp = False
    h_offset: int | None = None
    comp = 40
    d_offset: int | None = None
    cycle: int | None = None
    cycle_z: float | None = None
    cycle_r: float | None = None
    terminated = False
    executable = 0
    previous_sequence: int | None = None
    selections: list[int] = []
    changes: list[int] = []
    programs: list[int] = []
    segments: list[Segment] = []
    sample_count = 0

    for physical_line, line in enumerate(strip_comments(src), start=1):
        if not line or line == "%":
            continue
        if any(char in line for char in "#[]="):
            raise EvaluationError("macros and expressions are unsupported")
        found = WORD_RE.findall(line)
        if not found or len(found) > MAX_WORDS_PER_LINE or re.sub(r"[\s/]+", "", WORD_RE.sub("", line)):
            raise EvaluationError("unknown executable text")
        if terminated:
            raise EvaluationError("executable code after program termination")
        executable += 1
        grouped: dict[str, list[float]] = {}
        for letter, token in found:
            value = float(token)
            if not math.isfinite(value) or abs(value) > 10_000_000:
                raise EvaluationError("non-finite or excessive numeric word")
            grouped.setdefault(letter, []).append(value)
        if set(grouped) - set("NOGMTSFHDPQXYZIJR"):
            raise EvaluationError("unsupported address word")
        for letter in "NOTSFHDPQXYZIJR":
            if len(grouped.get(letter, [])) > 1:
                raise EvaluationError(f"duplicate {letter} address")
        if "N" in grouped:
            sequence = exact_integer(grouped["N"][0], "sequence")
            if previous_sequence is not None and sequence <= previous_sequence:
                raise EvaluationError("non-increasing sequence numbers")
            previous_sequence = sequence
        if "O" in grouped:
            if set(grouped) - {"N", "O"}:
                raise EvaluationError("program number mixed with executable words")
            programs.append(exact_integer(grouped["O"][0], "program", 1, 999999))
            continue

        gcodes = grouped.get("G", [])
        mcodes = [exact_integer(value, "M code", 0, 999) for value in grouped.get("M", [])]
        machine_return = False
        for value in gcodes:
            if close(value, 0.0, 1e-6):
                motion = 0
            elif close(value, 1.0, 1e-6):
                motion = 1
            elif close(value, 2.0, 1e-6):
                motion = 2
            elif close(value, 3.0, 1e-6):
                motion = 3
            elif close(value, 17.0, 1e-6):
                plane17 = True
            elif close(value, 20.0, 1e-6):
                units = "inch"
            elif close(value, 21.0, 1e-6):
                units = "mm"
            elif close(value, 28.0, 1e-6):
                machine_return = True
            elif close(value, 40.0, 1e-6):
                comp, d_offset = 40, None
            elif close(value, 41.0, 1e-6):
                comp = 41
            elif close(value, 42.0, 1e-6):
                comp = 42
            elif close(value, 43.0, 1e-6):
                length_comp = True
            elif close(value, 49.0, 1e-6):
                length_comp, h_offset = False, None
            elif close(value, 54.0, 1e-6):
                wcs = "G54"
            elif any(close(value, code, 1e-6) for code in (55.0, 56.0, 57.0, 58.0, 59.0, 54.1)):
                raise EvaluationError("only G54 is valid for this part")
            elif close(value, 80.0, 1e-6):
                cycle = None
            elif any(close(value, code, 1e-6) for code in (81.0, 82.0, 83.0)):
                cycle = int(round(value))
            elif close(value, 90.0, 1e-6):
                absolute = True
            elif close(value, 91.0, 1e-6):
                absolute = False
            elif any(close(value, code, 1e-6) for code in (94.0, 98.0, 99.0)):
                pass
            else:
                raise EvaluationError(f"unsupported G code {value:g}")

        for code in mcodes:
            if code not in {2, 3, 4, 5, 6, 8, 9, 30}:
                raise EvaluationError(f"unsupported M code M{code}")
        factor = 25.4 if units == "inch" else 1.0
        if "T" in grouped:
            pending_tool = exact_integer(grouped["T"][0], "tool", 1, 99)
            selections.append(pending_tool)
        if "S" in grouped:
            spindle = grouped["S"][0]
            if spindle <= 0 or spindle > 100_000:
                raise EvaluationError("invalid spindle speed")
        if "F" in grouped:
            feed = grouped["F"][0] * factor
            if feed <= 0 or feed > 100_000:
                raise EvaluationError("invalid feed")
        if "H" in grouped:
            h_offset = exact_integer(grouped["H"][0], "H offset", 1, 999)
        if "D" in grouped:
            d_offset = exact_integer(grouped["D"][0], "D offset", 1, 999)
        if "Q" in grouped and (cycle != 83 or grouped["Q"][0] * factor <= 0):
            raise EvaluationError("Q is only valid for positive G83 pecking")
        if 6 in mcodes:
            if pending_tool is None:
                raise EvaluationError("M6 without an exact T word")
            active_tool = pending_tool
            changes.append(active_tool)
            length_comp, h_offset, comp, d_offset = False, None, 40, None
        if 3 in mcodes:
            spindle_direction = 3
        if 4 in mcodes:
            spindle_direction = 4
        if 5 in mcodes:
            spindle_direction = None
        if 2 in mcodes or 30 in mcodes:
            terminated = True

        coordinate_letters = set(grouped) & {"X", "Y", "Z"}
        if coordinate_letters and absolute is None:
            raise EvaluationError("coordinate motion before G90/G91")
        if (coordinate_letters or "F" in grouped or "Q" in grouped or "R" in grouped) and units is None:
            raise EvaluationError("dimensional word before G20/G21")
        if machine_return:
            if absolute is not False or any(abs(grouped[axis][0]) > 1e-9 for axis in coordinate_letters):
                raise EvaluationError("only zero-intermediate G91 G28 return is accepted")
            continue

        def coordinate(axis: str, old: float) -> float:
            if axis not in grouped:
                return old
            value = grouped[axis][0] * factor
            return value if absolute else old + value

        new = Point(coordinate("X", current.x), coordinate("Y", current.y), coordinate("Z", current.z))
        if max(abs(new.x), abs(new.y)) > 250.0 or new.z < -60.0 or new.z > 150.0:
            raise EvaluationError("part-coordinate resource/safety envelope exceeded")

        if cycle is not None and cycle != 80 and (coordinate_letters or any(close(value, cycle, 1e-6) for value in gcodes)):
            if cycle not in {81, 82, 83}:
                raise EvaluationError("unsupported drilling cycle")
            if "Z" in grouped:
                cycle_z = new.z
            if "R" in grouped:
                raw_r = grouped["R"][0] * factor
                cycle_r = raw_r if absolute else current.z + raw_r
            if cycle_z is None or cycle_r is None:
                raise EvaluationError("incomplete drilling cycle")
            top = Point(new.x, new.y, cycle_r)
            bottom = Point(new.x, new.y, cycle_z)
            sample = dense_line(top, bottom)
            segments.append(Segment(top, bottom, sample, 1, cycle, active_tool, spindle, spindle_direction, feed, wcs, plane17, length_comp, h_offset, comp, d_offset, physical_line))
            sample_count += len(sample)
            current = top
        elif coordinate_letters and motion is not None:
            if motion in {2, 3}:
                if not plane17 or len(grouped.get("I", [])) != 1 or len(grouped.get("J", [])) != 1:
                    raise EvaluationError("G2/G3 requires G17 and one I/J pair")
                sample = arc_points(current, new, grouped["I"][0] * factor, grouped["J"][0] * factor, motion == 2)
            else:
                if "I" in grouped or "J" in grouped:
                    raise EvaluationError("I/J supplied outside an arc")
                sample = dense_line(current, new)
            segments.append(Segment(current, new, sample, motion, None, active_tool, spindle, spindle_direction, feed, wcs, plane17, length_comp, h_offset, comp, d_offset, physical_line))
            sample_count += len(sample)
            current = new
        if len(segments) > MAX_SEGMENTS or sample_count > MAX_SAMPLES:
            raise EvaluationError("toolpath sampling resource limit exceeded")

    return Program(segments, selections, changes, programs, terminated, executable)


def point_in_rect(x: float, y: float, rect: tuple[float, float, float, float], tolerance: float = 0.0) -> bool:
    xmin, xmax, ymin, ymax = rect
    return xmin - tolerance <= x <= xmax + tolerance and ymin - tolerance <= y <= ymax + tolerance


def point_in_upper(x: float, y: float, tolerance: float = 0.0) -> bool:
    return any(point_in_rect(x, y, rect, tolerance) for rect in UPPER_RECTS)


def disk_inside_region(x: float, y: float, radius: float, region, tolerance: float = 0.18) -> bool:
    for index in range(32):
        angle = 2.0 * math.pi * index / 32.0
        px, py = x + radius * math.cos(angle), y + radius * math.sin(angle)
        if not region(px, py, tolerance):
            return False
    return region(x, y, tolerance)


def distance_to_stock(x: float, y: float) -> float:
    xmin, xmax, ymin, ymax = STOCK
    return math.hypot(max(xmin - x, 0.0, x - xmax), max(ymin - y, 0.0, y - ymax))


def segment_xy_length(segment: Segment) -> float:
    return math.hypot(segment.end.x - segment.start.x, segment.end.y - segment.start.y)


def cutting_state(segment: Segment, tool: int) -> None:
    spec = TOOLS[tool]
    if (
        segment.tool != tool
        or segment.spindle_direction != 3
        or segment.spindle is None
        or not close(segment.spindle, spec["spindle"], 0.5)
        or segment.feed is None
        or segment.feed <= 0
        or segment.wcs != "G54"
        or not segment.length_comp
        or segment.h_offset != tool
    ):
        raise EvaluationError(f"invalid T{tool} WCS/H/S/cutting state")


def primary_feed(segment: Segment, tool: int) -> bool:
    return segment.feed is not None and close(segment.feed, TOOLS[tool]["feed"], 0.75)


def accessible_grid(rects: tuple[tuple[float, float, float, float], ...], radius: float, region, step: float = 1.5) -> list[tuple[float, float]]:
    xmin = min(rect[0] for rect in rects)
    xmax = max(rect[1] for rect in rects)
    ymin = min(rect[2] for rect in rects)
    ymax = max(rect[3] for rect in rects)
    points: list[tuple[float, float]] = []
    x = xmin
    while x <= xmax + 1e-9:
        y = ymin
        while y <= ymax + 1e-9:
            if disk_inside_region(x, y, radius, region):
                points.append((x, y))
            y += step
        x += step
    return points


def covered(path: list[Point], targets: list[tuple[float, float]], tolerance: float) -> bool:
    return bool(path) and all(any(math.hypot(point.x - x, point.y - y) <= tolerance for point in path) for x, y in targets)


def validate_upper(program: Program) -> None:
    radius = TOOLS[1]["diameter"] / 2.0
    bottom_path: list[Point] = []
    levels: set[float] = set()
    for segment in [value for value in program.segments if value.tool == 1]:
        if min(point.z for point in segment.samples) < 0.05:
            if segment.motion in {1, 2, 3}:
                cutting_state(segment, 1)
            for point in segment.samples:
                if point.z < -10.15:
                    raise EvaluationError("T1 cuts below the upper-pocket floor")
                if point.z < 0.05 and not disk_inside_region(point.x, point.y, radius, point_in_upper):
                    raise EvaluationError("T1 leaves the upper irregular pocket")
        if segment.motion in {1, 2, 3} and segment_xy_length(segment) > 0.05 and min(segment.start.z, segment.end.z) <= 0.0:
            if not primary_feed(segment, 1) or not segment.plane17:
                raise EvaluationError("T1 primary cutting feed/plane mismatch")
            if abs(segment.start.z - segment.end.z) <= 0.15:
                levels.add(round((segment.start.z + segment.end.z) / 2.0, 1))
            if all(abs(point.z + 10.0) <= 0.14 for point in segment.samples):
                bottom_path.extend(segment.samples)
    if len(levels) < 4 or min(levels) > -9.9:
        raise EvaluationError("T1 lacks safe multi-depth cutting to Z-10")
    grid = accessible_grid(UPPER_RECTS, radius, point_in_upper)
    if not covered(bottom_path, grid, 2.5):
        raise EvaluationError("upper irregular pocket bottom is under-cleared")


def validate_deep_step(program: Program) -> None:
    radius = TOOLS[2]["diameter"] / 2.0
    region = lambda x, y, tolerance=0.0: point_in_rect(x, y, DEEP_RECT, tolerance)
    bottom_path: list[Point] = []
    levels: set[float] = set()
    for segment in [value for value in program.segments if value.tool == 2]:
        if min(point.z for point in segment.samples) < -10.0:
            if segment.motion in {1, 2, 3}:
                cutting_state(segment, 2)
            for point in segment.samples:
                if point.z < -11.15:
                    raise EvaluationError("T2 cuts below the deep-step floor")
                if point.z < -10.0 and not disk_inside_region(point.x, point.y, radius, region):
                    raise EvaluationError("T2 leaves the central deep-step boundary")
        elif min(point.z for point in segment.samples) < 0.05:
            for point in segment.samples:
                if point.z < 0.05 and not disk_inside_region(point.x, point.y, radius, point_in_upper):
                    raise EvaluationError("T2 rapid/feed motion leaves the previously cleared upper pocket")
        if segment.motion in {1, 2, 3} and segment_xy_length(segment) > 0.05 and min(segment.start.z, segment.end.z) < -10.35:
            if not primary_feed(segment, 2) or not segment.plane17:
                raise EvaluationError("T2 primary cutting feed/plane mismatch")
            if abs(segment.start.z - segment.end.z) <= 0.15:
                levels.add(round((segment.start.z + segment.end.z) / 2.0, 2))
            if all(abs(point.z + 11.0) <= 0.14 for point in segment.samples):
                bottom_path.extend(segment.samples)
    if len(levels) < 2 or min(levels) > -10.9:
        raise EvaluationError("T2 lacks the Z-11 central deep step")
    grid = accessible_grid((DEEP_RECT,), radius, region)
    if not covered(bottom_path, grid, 1.9):
        raise EvaluationError("central deep-step bottom is under-cleared")


def validate_drilling(program: Program) -> None:
    locations: list[tuple[float, float]] = []
    drill_segments = [value for value in program.segments if value.tool == 3]
    if not drill_segments:
        raise EvaluationError("no T3 drilling segments")
    for segment in drill_segments:
        if segment.cycle not in {81, 82, 83} or segment_xy_length(segment) > 0.05:
            if min(point.z for point in segment.samples) < 0.05:
                raise EvaluationError("T3 contains non-drilling stock motion")
            continue
        cutting_state(segment, 3)
        if not primary_feed(segment, 3):
            raise EvaluationError("T3 drilling feed mismatch")
        if segment.end.z > -18.2 or segment.end.z < -22.0:
            raise EvaluationError("T3 hole is shallow or excessively deep")
        nearest = min(HOLES, key=lambda value: math.hypot(segment.end.x - value[0], segment.end.y - value[1]))
        if math.hypot(segment.end.x - nearest[0], segment.end.y - nearest[1]) > 0.35:
            raise EvaluationError("unexpected T3 hole location")
        locations.append(nearest)
    if set(locations) != set(HOLES):
        raise EvaluationError("four D5 through-hole locations are incomplete")


def validate_contour(program: Program) -> None:
    radius = TOOLS[4]["diameter"] / 2.0
    levels: set[float] = set()
    full_depth_path: list[Point] = []
    full_depth_length = 0.0
    for segment in [value for value in program.segments if value.tool == 4]:
        if min(point.z for point in segment.samples) < 0.05:
            if segment.motion in {1, 2, 3}:
                cutting_state(segment, 4)
            for point in segment.samples:
                if point.z < -18.15:
                    raise EvaluationError("T4 cuts below the part bottom")
                if point.z < 0.05 and distance_to_stock(point.x, point.y) < radius - 0.18:
                    raise EvaluationError("T4 enters or crosses the finished part")
        if segment.motion in {1, 2, 3} and segment_xy_length(segment) > 0.05 and min(segment.start.z, segment.end.z) <= -0.1:
            if abs(segment.start.z - segment.end.z) <= 0.15:
                levels.add(round((segment.start.z + segment.end.z) / 2.0, 1))
            if all(abs(point.z + 18.0) <= 0.14 for point in segment.samples) and primary_feed(segment, 4):
                if segment.comp in {41, 42} and segment.d_offset != 24:
                    raise EvaluationError("unexpected native contour compensation register")
                full_depth_path.extend(segment.samples)
                full_depth_length += distance(segment.start, segment.end)
    if len(levels) < 3 or min(levels) > -17.9:
        raise EvaluationError("T4 lacks a multi-depth full contour")
    targets: list[tuple[float, float]] = []
    for index in range(93):
        y = -46.0 + index
        targets.extend(((-66.0, y), (66.0, y)))
    for index in range(133):
        x = -66.0 + index
        targets.extend(((x, -46.0), (x, 46.0)))
    if not covered(full_depth_path, targets, 0.85) or not 430.0 <= full_depth_length <= 520.0:
        raise EvaluationError("T4 full-depth outside contour is incomplete")


def validate_program(program: Program) -> None:
    if not program.terminated:
        raise EvaluationError("NC program is not terminated")
    if program.programs != [PROGRAM]:
        raise EvaluationError("wrong exact O-number")

    def first_occurrence_order(values: list[int]) -> list[int]:
        seen: set[int] = set()
        order: list[int] = []
        for value in values:
            if value not in seen:
                seen.add(value)
                order.append(value)
        return order

    if first_occurrence_order(program.selections) != [1, 2, 3, 4]:
        raise EvaluationError("first tool-selection order must be T1-T4")
    if first_occurrence_order(program.changes) != [1, 2, 3, 4]:
        raise EvaluationError("first effective tool-change order must be T1-T4")
    for segment in program.segments:
        if segment.motion in {1, 2, 3} and min(point.z for point in segment.samples) < 0.05:
            if segment.tool not in TOOLS:
                raise EvaluationError("stock motion without an allowed tool")
            cutting_state(segment, int(segment.tool))
    validate_upper(program)
    validate_deep_step(program)
    validate_drilling(program)
    validate_contour(program)


def evaluate_text(src: str) -> bool:
    try:
        validate_program(parse_program(src))
        return True
    except (EvaluationError, ValueError, OverflowError, MemoryError):
        return False


def main() -> bool:
    path = TARGET / NC_NAME
    if not path.is_file() or path.stat().st_size <= 0 or path.stat().st_size > MAX_BYTES:
        return False
    return evaluate_text(path.read_text(encoding="utf-8", errors="strict"))


if __name__ == "__main__":
    try:
        ok = main()
    except Exception:
        ok = False
    print("True" if ok else "False")
    raise SystemExit(0)
