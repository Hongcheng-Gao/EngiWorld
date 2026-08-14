from __future__ import annotations

import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


TARGET = Path(os.environ.get("EVAL_TARGET_DIR", r"C:\Users\User\Desktop"))
NC_NAME = "task-06.nc"
MAX_BYTES = 2_000_000
TOOLS = {
    1: {"diameter": 10.0, "spindle": 7500.0, "feed": 520.0},
    2: {"diameter": 5.0, "spindle": 5000.0, "feed": 180.0},
    3: {"diameter": 6.0, "spindle": 9000.0, "feed": 650.0},
}
HOLES = [(-35.0, -20.0), (-35.0, 20.0), (35.0, -20.0), (35.0, 20.0)]
WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))")
ALLOWED_WORDS = {"N", "O", "G", "M", "X", "Y", "Z", "I", "J", "R", "P", "Q", "T", "S", "F", "H", "D"}


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
    tool: int | None
    spindle: float | None
    spindle_on: bool
    feed: float | None
    wcs: str | None
    length_comp: bool
    h_offset: int | None
    comp: int
    d_offset: int | None
    machine_coordinates: bool
    cycle: int | None
    line_number: int


@dataclass
class Program:
    segments: list[Segment]
    tool_changes: list[int]
    tool_references: set[int]
    terminated: bool
    explicit_units: bool
    explicit_distance: bool
    executable_lines: int


def close(a: float, b: float, tolerance: float) -> bool:
    return abs(a - b) <= tolerance


def integral(value: float, label: str) -> int:
    if not math.isfinite(value) or not close(value, round(value), 1e-9):
        raise EvaluationError(f"non-integral {label}")
    return int(round(value))


def distance(a: Point, b: Point) -> float:
    return math.dist((a.x, a.y, a.z), (b.x, b.y, b.z))


def dense_line(start: Point, end: Point, spacing: float = 0.75) -> list[Point]:
    count = max(1, int(math.ceil(distance(start, end) / spacing)))
    return [
        Point(
            start.x + (end.x - start.x) * index / count,
            start.y + (end.y - start.y) * index / count,
            start.z + (end.z - start.z) * index / count,
        )
        for index in range(count + 1)
    ]


def strip_comments(source: str) -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []
    depth = 0
    for line_number, raw in enumerate(source.upper().splitlines(), 1):
        clean: list[str] = []
        for char in raw:
            if char == ";" and depth == 0:
                break
            if char == "(":
                depth += 1
            elif char == ")":
                if depth == 0:
                    raise EvaluationError("unmatched comment close")
                depth -= 1
            elif depth == 0:
                clean.append(char)
        rows.append((line_number, "".join(clean).strip()))
    if depth:
        raise EvaluationError("unterminated comment")
    return rows


def sweep_for(center_x: float, center_y: float, start: Point, end: Point, clockwise: bool) -> tuple[float, float, float]:
    start_angle = math.atan2(start.y - center_y, start.x - center_x)
    end_angle = math.atan2(end.y - center_y, end.x - center_x)
    sweep = (start_angle - end_angle) % (2 * math.pi) if clockwise else (end_angle - start_angle) % (2 * math.pi)
    if sweep <= 1e-9:
        sweep = 2 * math.pi
    return start_angle, sweep, -1.0 if clockwise else 1.0


def sampled_arc(start: Point, end: Point, center_x: float, center_y: float, clockwise: bool) -> list[Point]:
    radius = math.hypot(start.x - center_x, start.y - center_y)
    if radius <= 1e-6 or not close(math.hypot(end.x - center_x, end.y - center_y), radius, 0.25):
        raise EvaluationError("invalid arc geometry")
    start_angle, sweep, direction = sweep_for(center_x, center_y, start, end, clockwise)
    count = max(12, int(math.ceil(radius * sweep / 0.75)))
    return [
        Point(
            center_x + radius * math.cos(start_angle + direction * sweep * index / count),
            center_y + radius * math.sin(start_angle + direction * sweep * index / count),
            start.z + (end.z - start.z) * index / count,
        )
        for index in range(count + 1)
    ]


def arc_points_ij(start: Point, end: Point, i_value: float, j_value: float, clockwise: bool) -> list[Point]:
    return sampled_arc(start, end, start.x + i_value, start.y + j_value, clockwise)


def arc_points_r(start: Point, end: Point, r_value: float, clockwise: bool) -> list[Point]:
    chord_x, chord_y = end.x - start.x, end.y - start.y
    chord = math.hypot(chord_x, chord_y)
    radius = abs(r_value)
    if chord <= 1e-9 or radius < chord / 2 - 1e-6:
        raise EvaluationError("invalid R arc")
    middle_x, middle_y = (start.x + end.x) / 2, (start.y + end.y) / 2
    height = math.sqrt(max(0.0, radius * radius - (chord / 2) ** 2))
    normal_x, normal_y = -chord_y / chord, chord_x / chord
    centers = [
        (middle_x + normal_x * height, middle_y + normal_y * height),
        (middle_x - normal_x * height, middle_y - normal_y * height),
    ]
    choices = []
    for center_x, center_y in centers:
        _start_angle, sweep, _direction = sweep_for(center_x, center_y, start, end, clockwise)
        choices.append((center_x, center_y, sweep))
    if r_value >= 0:
        center_x, center_y, _sweep = min(choices, key=lambda item: item[2])
    else:
        center_x, center_y, _sweep = max(choices, key=lambda item: item[2])
    return sampled_arc(start, end, center_x, center_y, clockwise)


def parse_program(source: str) -> Program:
    units: str | None = None
    absolute: bool | None = None
    motion: int | None = None
    current = Point(0.0, 0.0, 0.0)
    pending_tool: int | None = None
    tool: int | None = None
    tool_references: set[int] = set()
    tool_changes: list[int] = []
    spindle: float | None = None
    spindle_on = False
    feed: float | None = None
    wcs: str | None = None
    length_comp = False
    h_offset: int | None = None
    comp = 40
    d_offset: int | None = None
    cycle: int | None = None
    cycle_z: float | None = None
    cycle_r: float | None = None
    terminated = False
    executable_lines = 0
    segments: list[Segment] = []

    for line_number, line in strip_comments(source):
        if not line or line == "%":
            continue
        if any(char in line for char in "#[]="):
            raise EvaluationError("macros and expressions are unsupported")
        found = WORD_RE.findall(line)
        if not found:
            raise EvaluationError(f"unparsed executable text on line {line_number}")
        residue = re.sub(r"[\s/]+", "", WORD_RE.sub("", line))
        if residue:
            raise EvaluationError(f"unknown executable text on line {line_number}")
        if terminated:
            raise EvaluationError("executable code after M30")
        executable_lines += 1

        grouped: dict[str, list[float]] = {}
        for letter, raw_value in found:
            if letter not in ALLOWED_WORDS:
                raise EvaluationError(f"unsupported address {letter}")
            value = float(raw_value)
            if not math.isfinite(value):
                raise EvaluationError("non-finite numeric word")
            grouped.setdefault(letter, []).append(value)
        for letter, values in grouped.items():
            if letter not in {"G", "M"} and len(values) != 1:
                raise EvaluationError(f"duplicate {letter} address")
        for letter in ("N", "O", "T", "H", "D"):
            if letter in grouped:
                integral(grouped[letter][0], letter)

        gcodes = grouped.get("G", [])
        mcodes = [integral(value, "M") for value in grouped.get("M", [])]
        if any(code not in {0, 1, 3, 4, 5, 6, 8, 9, 30} for code in mcodes):
            raise EvaluationError("unsupported M code")
        if "T" in grouped:
            pending_tool = integral(grouped["T"][0], "T")
            tool_references.add(pending_tool)
        if 6 in mcodes:
            if pending_tool is None:
                raise EvaluationError("M6 without tool")
            tool = pending_tool
            tool_changes.append(tool)
            spindle = None
            spindle_on = False
            feed = None
            length_comp = False
            h_offset = None
            comp = 40
            d_offset = None
            cycle = None
            cycle_z = None
            cycle_r = None

        machine_coordinates = any(close(code, 53.0, 1e-6) for code in gcodes)
        reference_return = any(close(code, 28.0, 1e-6) for code in gcodes)
        for code in gcodes:
            rounded = int(round(code))
            if close(code, 20.0, 1e-6):
                units = "inch"
            elif close(code, 21.0, 1e-6):
                units = "mm"
            elif close(code, 90.0, 1e-6):
                absolute = True
            elif close(code, 91.0, 1e-6):
                absolute = False
            elif rounded in (0, 1, 2, 3) and close(code, rounded, 1e-6):
                motion = rounded
            elif rounded in (54, 55, 56, 57, 58, 59) and close(code, rounded, 1e-6):
                wcs = f"G{rounded}"
            elif close(code, 54.1, 1e-6):
                if "P" not in grouped:
                    raise EvaluationError("G54.1 requires P")
                p_value = integral(grouped["P"][0], "P")
                if p_value <= 0:
                    raise EvaluationError("invalid G54.1 offset")
                wcs = f"G54.1P{p_value}"
            elif close(code, 43.0, 1e-6):
                length_comp = True
            elif close(code, 49.0, 1e-6):
                length_comp = False
                h_offset = None
            elif rounded in (40, 41, 42) and close(code, rounded, 1e-6):
                comp = rounded
                if rounded == 40:
                    d_offset = None
            elif rounded in (81, 82, 83) and close(code, rounded, 1e-6):
                cycle = rounded
            elif rounded == 80 and close(code, 80.0, 1e-6):
                cycle = None
            elif any(close(code, value, 1e-6) for value in (4.0, 17.0, 28.0, 53.0, 94.0, 98.0, 99.0)):
                pass
            else:
                raise EvaluationError(f"unsupported G code G{code:g}")

        factor = 25.4 if units == "inch" else 1.0
        if "S" in grouped:
            spindle = grouped["S"][0]
        if "F" in grouped:
            feed = grouped["F"][0] * factor
        if "H" in grouped:
            h_offset = integral(grouped["H"][0], "H")
        if "D" in grouped:
            d_offset = integral(grouped["D"][0], "D")
        if (3 in mcodes or 4 in mcodes) and 5 in mcodes:
            raise EvaluationError("conflicting spindle commands")
        if 3 in mcodes or 4 in mcodes:
            spindle_on = True
        if 5 in mcodes:
            spindle_on = False

        has_coordinates = any(letter in grouped for letter in ("X", "Y", "Z"))
        if absolute is None and has_coordinates:
            raise EvaluationError("motion before explicit G90/G91")
        if units is None and any(letter in grouped for letter in ("X", "Y", "Z", "I", "J", "R", "Q", "F")):
            raise EvaluationError("dimensional word before explicit G20/G21")

        def coordinate(axis: str, old_value: float) -> float:
            if axis not in grouped:
                return old_value
            new_value = grouped[axis][0] * factor
            return new_value if absolute else old_value + new_value

        new = Point(coordinate("X", current.x), coordinate("Y", current.y), coordinate("Z", current.z))
        if reference_return:
            current = new
        elif machine_coordinates:
            pass
        elif cycle is not None and has_coordinates:
            if "Z" in grouped:
                cycle_z = new.z
            if "R" in grouped:
                r_word = grouped["R"][0] * factor
                cycle_r = r_word if absolute else current.z + r_word
            if cycle_z is None or cycle_r is None:
                raise EvaluationError("incomplete drilling cycle")
            at_xy = Point(new.x, new.y, current.z)
            top = Point(new.x, new.y, cycle_r)
            bottom = Point(new.x, new.y, cycle_z)
            if distance(current, at_xy) > 1e-6:
                segments.append(Segment(current, at_xy, dense_line(current, at_xy), 0, tool, spindle, spindle_on, feed, wcs, length_comp, h_offset, comp, d_offset, False, cycle, line_number))
            if distance(at_xy, top) > 1e-6:
                segments.append(Segment(at_xy, top, dense_line(at_xy, top), 0, tool, spindle, spindle_on, feed, wcs, length_comp, h_offset, comp, d_offset, False, cycle, line_number))
            segments.append(Segment(top, bottom, dense_line(top, bottom), 1, tool, spindle, spindle_on, feed, wcs, length_comp, h_offset, comp, d_offset, False, cycle, line_number))
            current = top
        elif has_coordinates and motion is not None:
            if motion in (2, 3):
                has_ij = "I" in grouped or "J" in grouped
                has_r = "R" in grouped
                if has_ij and has_r:
                    raise EvaluationError("arc cannot mix I/J and R")
                if has_ij:
                    if "I" not in grouped or "J" not in grouped:
                        raise EvaluationError("XY arc requires both I and J")
                    samples = arc_points_ij(current, new, grouped["I"][0] * factor, grouped["J"][0] * factor, motion == 2)
                elif has_r:
                    samples = arc_points_r(current, new, grouped["R"][0] * factor, motion == 2)
                else:
                    raise EvaluationError("arc requires I/J or R")
            else:
                samples = dense_line(current, new)
            segments.append(Segment(current, new, samples, motion, tool, spindle, spindle_on, feed, wcs, length_comp, h_offset, comp, d_offset, False, None, line_number))
            current = new
        if 30 in mcodes:
            terminated = True

    return Program(segments, tool_changes, tool_references, terminated, units is not None, absolute is not None, executable_lines)


def cutting_segments(program: Program, tool: int) -> list[Segment]:
    return [
        segment
        for segment in program.segments
        if segment.tool == tool
        and segment.motion in (1, 2, 3)
        and not segment.machine_coordinates
        and distance(segment.start, segment.end) > 1e-5
    ]


def validate_common(program: Program) -> None:
    if not program.terminated or not program.explicit_units or not program.explicit_distance or program.executable_lines < 15:
        raise EvaluationError("incomplete executable program")
    if program.tool_references - set(TOOLS):
        raise EvaluationError("unexpected tool reference")
    if len(program.tool_changes) != 3 or Counter(program.tool_changes) != Counter({1: 1, 2: 1, 3: 1}):
        raise EvaluationError("each supplied tool must be changed exactly once")
    if any(segment.motion in (1, 2, 3) and segment.tool is None for segment in program.segments):
        raise EvaluationError("feed motion before tool change")
    for tool, contract in TOOLS.items():
        segments = cutting_segments(program, tool)
        if not segments:
            raise EvaluationError(f"T{tool} has no cutting motion")
        for segment in segments:
            if not segment.spindle_on:
                raise EvaluationError(f"T{tool} cuts with spindle stopped")
            if segment.spindle is None or not close(segment.spindle, contract["spindle"], 1.0):
                raise EvaluationError(f"T{tool} has wrong spindle speed")
            if segment.feed is None or not close(segment.feed, contract["feed"], 0.75):
                raise EvaluationError(f"T{tool} has wrong cutting feed")
            if segment.wcs != "G54":
                raise EvaluationError(f"T{tool} cuts outside G54")
            if not segment.length_comp or segment.h_offset != tool:
                raise EvaluationError(f"T{tool} lacks matching G43/H{tool}")
        safe_rapids = [
            segment
            for segment in program.segments
            if segment.tool == tool and segment.motion == 0 and not segment.machine_coordinates and max(segment.start.z, segment.end.z) >= 2.0
        ]
        if not safe_rapids:
            raise EvaluationError(f"T{tool} lacks safe rapid clearance")


def grid_covered(points: list[Point], xs: list[float], ys: list[float], radius: float) -> bool:
    return all(any(math.hypot(point.x - x_value, point.y - y_value) <= radius for point in points) for x_value in xs for y_value in ys)


def validate_pocket(program: Program) -> None:
    segments = cutting_segments(program, 1)
    material_points = [point for segment in segments for point in segment.samples if point.z <= 0.25]
    if not material_points:
        raise EvaluationError("missing pocket cutting")
    if any(abs(point.x) > 17.75 or abs(point.y) > 9.75 for point in material_points):
        raise EvaluationError("T1 cuts outside the D10 pocket-center envelope")
    if any(point.z < -11.25 for point in material_points):
        raise EvaluationError("pocket is over-deep")
    bottom = [point for point in material_points if -11.25 <= point.z <= -10.5]
    if not bottom or min(point.z for point in bottom) > -10.75:
        raise EvaluationError("pocket bottom depth is missing")
    if not grid_covered(bottom, [-17.0, -8.5, 0.0, 8.5, 17.0], [-9.0, 0.0, 9.0], 4.75):
        raise EvaluationError("44 x 28 pocket is not cleared to depth 11")


def nearest_hole(x_value: float, y_value: float) -> tuple[int, float]:
    distances = [math.hypot(x_value - hole_x, y_value - hole_y) for hole_x, hole_y in HOLES]
    index = min(range(len(distances)), key=distances.__getitem__)
    return index, distances[index]


def validate_drill(program: Program) -> None:
    deepest: dict[int, float] = {}
    for segment in cutting_segments(program, 2):
        if math.hypot(segment.end.x - segment.start.x, segment.end.y - segment.start.y) > 0.25:
            raise EvaluationError("T2 performs lateral feed cutting")
        if segment.end.z >= segment.start.z - 0.25:
            raise EvaluationError("T2 drilling feed is not downward")
        index, hole_distance = nearest_hole(segment.end.x, segment.end.y)
        if hole_distance > 0.75:
            raise EvaluationError("T2 drills an unexpected location")
        bottom = min(segment.start.z, segment.end.z)
        if bottom < -20.25:
            raise EvaluationError("drill exceeds permitted through-tip allowance")
        deepest[index] = min(deepest.get(index, float("inf")), bottom)
    if set(deepest) != set(range(4)):
        raise EvaluationError("one or more holes are missing")
    if any(not (-20.25 <= deepest[index] <= -18.0) for index in range(4)):
        raise EvaluationError("one or more holes are not through")


def signed_area(points: list[Point]) -> float:
    return 0.5 * sum(first.x * second.y - second.x * first.y for first, second in zip(points, points[1:]))


def near_closed_subloops(points: list[Point], minimum_points: int = 40, gap: float = 2.0) -> list[list[Point]]:
    loops: list[list[Point]] = []
    if len(points) >= minimum_points and distance(points[0], points[-1]) <= gap:
        loops.append(points)
    for start in range(len(points) - minimum_points):
        for end in range(start + minimum_points, len(points)):
            if distance(points[start], points[end]) <= gap:
                loops.append(points[start : end + 1])
    return loops


def validate_profile(program: Program) -> None:
    segments = cutting_segments(program, 3)
    material_points = [point for segment in segments for point in segment.samples if point.z <= 0.25]
    if not material_points:
        raise EvaluationError("missing profile cutting")
    if any(point.z < -18.25 for point in material_points):
        raise EvaluationError("profile is over-deep")
    for point in material_points:
        if abs(point.x) > 70.0 or abs(point.y) > 50.0:
            raise EvaluationError("profile contains extreme over-travel")
        if max(abs(point.x) - 60.0, abs(point.y) - 40.0) < -0.75:
            raise EvaluationError("T3 performs destructive cutting inside the nominal perimeter")

    candidates: list[tuple[list[Point], list[Segment]]] = []
    run: list[Point] = []
    run_segments: list[Segment] = []
    for segment in segments:
        horizontal = abs(segment.start.z - segment.end.z) <= 0.3 and -18.25 <= min(segment.start.z, segment.end.z) <= -17.75
        if horizontal:
            if not run or distance(run[-1], segment.start) <= 0.5:
                if not run:
                    run.append(segment.start)
                run.extend(segment.samples[1:])
                run_segments.append(segment)
            else:
                candidates.append((run, run_segments))
                run = [segment.start, *segment.samples[1:]]
                run_segments = [segment]
        elif run:
            candidates.append((run, run_segments))
            run = []
            run_segments = []
    if run:
        candidates.append((run, run_segments))

    for points, candidate_segments in candidates:
        for loop in near_closed_subloops(points):
            xs = [point.x for point in loop]
            ys = [point.y for point in loop]
            offset = (
                close(min(xs), -63.0, 0.75)
                and close(max(xs), 63.0, 0.75)
                and close(min(ys), -43.0, 0.75)
                and close(max(ys), 43.0, 0.75)
                and all(max(abs(point.x) - 60.0, abs(point.y) - 40.0) >= 2.0 for point in loop)
            )
            if offset:
                return
            nominal_points = [point for point in loop if abs(point.x) <= 60.75 and abs(point.y) <= 40.75]
            nominal = (
                nominal_points
                and close(min(point.x for point in nominal_points), -60.0, 0.75)
                and close(max(point.x for point in nominal_points), 60.0, 0.75)
                and close(min(point.y for point in nominal_points), -40.0, 0.75)
                and close(max(point.y for point in nominal_points), 40.0, 0.75)
                and all(
                    any(abs(point.x - x_value) <= 0.75 and abs(point.y - y_value) <= 0.75 for point in nominal_points)
                    for x_value, y_value in ((-60.0, -40.0), (60.0, -40.0), (60.0, 40.0), (-60.0, 40.0))
                )
            )
            if nominal:
                required_comp = 42 if signed_area(nominal_points) > 0 else 41
                if any(segment.comp == required_comp and segment.d_offset is not None and segment.d_offset > 0 for segment in candidate_segments):
                    return
    raise EvaluationError("missing full-depth compensated closed outside profile")


def evaluate_text(source: str) -> bool:
    try:
        program = parse_program(source)
        validate_common(program)
        validate_pocket(program)
        validate_drill(program)
        validate_profile(program)
        return True
    except (EvaluationError, OverflowError, ValueError):
        return False


def main() -> bool:
    path = TARGET / NC_NAME
    if not path.is_file() or path.stat().st_size <= 0 or path.stat().st_size > MAX_BYTES:
        return False
    raw = path.read_bytes()
    if b"\x00" in raw:
        return False
    try:
        source = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return False
    return evaluate_text(source)


if __name__ == "__main__":
    try:
        result = main()
    except Exception:
        result = False
    print("True" if result else "False")
    raise SystemExit(0)
