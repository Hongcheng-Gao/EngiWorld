from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


TARGET = Path(os.environ.get("EVAL_TARGET_DIR", r"C:\Users\User\Desktop"))
NC_NAME = "task-09.nc"
MAX_BYTES = 2_000_000
MAX_LINES = 20_000
MAX_EXECUTED_BLOCKS = 50_000
MAX_SEGMENTS = 8_000
MAX_SAMPLES = 250_000
TOOL_DIAMETER_MM = 8.0
TOOL_RADIUS_MM = TOOL_DIAMETER_MM / 2.0
SPINDLE_RPM = 8000.0
FEED_MM_MIN = 500.0
PART_X = 45.0
PART_Y = 30.0
PART_Z = 10.0
WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))")
INTEGER_WORDS = {"N", "O", "M", "T", "H", "D", "P", "L"}
ALLOWED_WORDS = set("NOGMXYZIJKRFS THDPL".replace(" ", ""))
ALLOWED_G = {0.0, 1.0, 2.0, 3.0, 17.0, 20.0, 21.0, 28.0, 40.0, 41.0, 42.0,
             43.0, 49.0, 52.0, 53.0, 54.0, 55.0, 56.0, 57.0, 58.0, 59.0,
             80.0, 90.0, 91.0, 94.0}
ALLOWED_M = {2, 3, 5, 6, 8, 9, 30, 98, 99}


class EvaluationError(ValueError):
    pass


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    z: float


@dataclass
class Block:
    line_no: int
    words: dict[str, list[float]]


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
    machine: bool


@dataclass
class State:
    units: str | None = None
    absolute: bool | None = None
    motion: int | None = None
    current: Point = Point(0.0, 0.0, 0.0)
    pending_tool: int | None = None
    tool: int | None = None
    spindle: float | None = None
    spindle_on: bool = False
    feed: float | None = None
    wcs: str | None = None
    length_comp: bool = False
    h_offset: int | None = None
    comp: int = 40
    d_offset: int | None = None


@dataclass
class ProgramResult:
    segments: list[Segment] = field(default_factory=list)
    selected_tools: list[int] = field(default_factory=list)
    changed_tools: list[int] = field(default_factory=list)
    called_programs: list[int] = field(default_factory=list)
    executed_blocks: int = 0
    sample_count: int = 0
    terminated: bool = False


def close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def integer(value: float, label: str) -> int:
    rounded = int(round(value))
    if abs(value - rounded) > 1e-4:
        raise EvaluationError(f"{label} must be integer-valued")
    return rounded


def distance(a: Point, b: Point) -> float:
    return math.dist((a.x, a.y, a.z), (b.x, b.y, b.z))


def strip_comments(src: str) -> list[str]:
    lines: list[str] = []
    depth = 0
    for raw in src.upper().splitlines():
        clean: list[str] = []
        for char in raw:
            if char == ";" and depth == 0:
                break
            if char == "(":
                depth += 1
            elif char == ")":
                if depth == 0:
                    raise EvaluationError("unmatched comment")
                depth -= 1
            elif depth == 0:
                clean.append(char)
        lines.append("".join(clean).strip())
    if depth:
        raise EvaluationError("unterminated comment")
    return lines


def tokenize(src: str) -> tuple[list[int], dict[int, list[Block]]]:
    if len(src.encode("utf-8")) > MAX_BYTES or len(src.splitlines()) > MAX_LINES:
        raise EvaluationError("program exceeds resource limits")
    order: list[int] = []
    programs: dict[int, list[Block]] = {}
    current: int | None = None
    for line_no, line in enumerate(strip_comments(src), 1):
        if not line or line == "%":
            continue
        if any(char in line for char in "#[]="):
            raise EvaluationError("expressions and macros are not accepted")
        found = WORD_RE.findall(line)
        residue = re.sub(r"[\s/]+", "", WORD_RE.sub("", line))
        if not found or residue:
            raise EvaluationError(f"unknown executable text on line {line_no}")
        words: dict[str, list[float]] = {}
        for letter, raw in found:
            if letter not in ALLOWED_WORDS:
                raise EvaluationError(f"unsupported address {letter}")
            value = float(raw)
            if not math.isfinite(value) or abs(value) > 1e7:
                raise EvaluationError("non-finite or excessive numeric value")
            words.setdefault(letter, []).append(value)
        for letter, values in words.items():
            if letter not in {"G", "M"} and len(values) > 1:
                raise EvaluationError(f"duplicate {letter} address")
            if letter in INTEGER_WORDS:
                for value in values:
                    integer(value, letter)
        if "O" in words:
            if len(words) != 1:
                raise EvaluationError("O program label must be on its own line")
            current = integer(words["O"][0], "O")
            if current in programs:
                raise EvaluationError("duplicate O program")
            order.append(current)
            programs[current] = []
            continue
        if current is None:
            raise EvaluationError("executable block before first O program")
        programs[current].append(Block(line_no, words))
    if not order:
        raise EvaluationError("missing O program")
    return order, programs


def validate_program_structure(order: list[int], programs: dict[int, list[Block]]) -> None:
    main = order[0]
    for number in order:
        blocks = programs[number]
        terminals: list[tuple[int, int]] = []
        for index, block in enumerate(blocks):
            for value in block.words.get("M", []):
                code = integer(value, "M")
                if code not in ALLOWED_M:
                    raise EvaluationError(f"unsupported M{code}")
                if code in {2, 30, 99}:
                    terminals.append((index, code))
        expected = {2, 30} if number == main else {99}
        if len(terminals) != 1 or terminals[0][1] not in expected:
            raise EvaluationError(f"invalid terminal for O{number}")
        if terminals[0][0] != len(blocks) - 1:
            raise EvaluationError(f"code after terminal in O{number}")


def line_samples(a: Point, b: Point, spacing: float = 0.5) -> list[Point]:
    length = distance(a, b)
    count = max(1, min(4000, int(math.ceil(length / spacing))))
    return [
        Point(
            a.x + (b.x - a.x) * index / count,
            a.y + (b.y - a.y) * index / count,
            a.z + (b.z - a.z) * index / count,
        )
        for index in range(count + 1)
    ]


def arc_center_from_r(a: Point, b: Point, radius_word: float, clockwise: bool) -> tuple[float, float]:
    chord = math.hypot(b.x - a.x, b.y - a.y)
    radius = abs(radius_word)
    if chord <= 1e-9 or radius < chord / 2.0 - 1e-6:
        raise EvaluationError("invalid R arc")
    mx, my = (a.x + b.x) / 2.0, (a.y + b.y) / 2.0
    height = math.sqrt(max(radius * radius - (chord / 2.0) ** 2, 0.0))
    nx, ny = -(b.y - a.y) / chord, (b.x - a.x) / chord
    candidates = [(mx + nx * height, my + ny * height), (mx - nx * height, my - ny * height)]
    choices: list[tuple[float, float, float]] = []
    for cx, cy in candidates:
        a0 = math.atan2(a.y - cy, a.x - cx)
        a1 = math.atan2(b.y - cy, b.x - cx)
        sweep = (a0 - a1) % (2 * math.pi) if clockwise else (a1 - a0) % (2 * math.pi)
        choices.append((sweep, cx, cy))
    desired_major = radius_word < 0
    filtered = [value for value in choices if (value[0] > math.pi) == desired_major]
    _, cx, cy = (filtered or choices)[0]
    return cx, cy


def arc_samples(a: Point, b: Point, words: dict[str, list[float]], factor: float, clockwise: bool) -> list[Point]:
    if "I" in words or "J" in words:
        if "I" not in words or "J" not in words:
            raise EvaluationError("arc requires both I and J")
        cx = a.x + words["I"][-1] * factor
        cy = a.y + words["J"][-1] * factor
    elif "R" in words:
        cx, cy = arc_center_from_r(a, b, words["R"][-1] * factor, clockwise)
    else:
        raise EvaluationError("arc requires I/J or R")
    radius = math.hypot(a.x - cx, a.y - cy)
    if radius <= 1e-6 or not close(math.hypot(b.x - cx, b.y - cy), radius, 0.25):
        raise EvaluationError("invalid arc geometry")
    a0 = math.atan2(a.y - cy, a.x - cx)
    a1 = math.atan2(b.y - cy, b.x - cx)
    sweep = (a0 - a1) % (2 * math.pi) if clockwise else (a1 - a0) % (2 * math.pi)
    if sweep <= 1e-9:
        sweep = 2 * math.pi
    count = max(12, min(4000, int(math.ceil(radius * sweep / 0.5))))
    direction = -1.0 if clockwise else 1.0
    return [
        Point(
            cx + radius * math.cos(a0 + direction * sweep * index / count),
            cy + radius * math.sin(a0 + direction * sweep * index / count),
            a.z + (b.z - a.z) * index / count,
        )
        for index in range(count + 1)
    ]


def execute(src: str) -> ProgramResult:
    order, programs = tokenize(src)
    validate_program_structure(order, programs)
    result = ProgramResult()
    state = State()
    active_calls: list[int] = []

    def run(number: int) -> None:
        if number in active_calls or len(active_calls) >= 8:
            raise EvaluationError("recursive or excessive subprogram calls")
        active_calls.append(number)
        for block in programs[number]:
            result.executed_blocks += 1
            if result.executed_blocks > MAX_EXECUTED_BLOCKS:
                raise EvaluationError("executed-block limit exceeded")
            words = block.words
            gcodes = words.get("G", [])
            mcodes = [integer(value, "M") for value in words.get("M", [])]
            for code in mcodes:
                if code not in ALLOWED_M:
                    raise EvaluationError(f"unsupported M{code}")
            for value in gcodes:
                if not any(close(value, allowed, 1e-6) for allowed in ALLOWED_G) and not close(value, 54.1, 1e-6):
                    raise EvaluationError(f"unsupported G{value:g}")

            if any(close(value, 20.0, 1e-6) for value in gcodes):
                state.units = "inch"
            if any(close(value, 21.0, 1e-6) for value in gcodes):
                state.units = "mm"
            factor = 25.4 if state.units == "inch" else 1.0
            machine = any(close(value, 28.0, 1e-6) or close(value, 53.0, 1e-6) for value in gcodes)
            g52 = any(close(value, 52.0, 1e-6) for value in gcodes)
            if g52 and any(abs(words[axis][-1] * factor) > 1e-6 for axis in ("X", "Y", "Z") if axis in words):
                raise EvaluationError("nonzero G52 shift is outside this task contract")

            for value in gcodes:
                rounded = int(round(value))
                if close(value, 90.0, 1e-6):
                    state.absolute = True
                elif close(value, 91.0, 1e-6):
                    state.absolute = False
                elif rounded in {0, 1, 2, 3} and close(value, float(rounded), 1e-6):
                    state.motion = rounded
                elif rounded in {54, 55, 56, 57, 58, 59} and close(value, float(rounded), 1e-6):
                    state.wcs = f"G{rounded}"
                elif close(value, 54.1, 1e-6):
                    if "P" not in words:
                        raise EvaluationError("G54.1 requires P")
                    p_value = integer(words["P"][-1], "P")
                    if p_value <= 0:
                        raise EvaluationError("invalid G54.1 P")
                    state.wcs = f"G54.1P{p_value}"
                elif close(value, 43.0, 1e-6):
                    state.length_comp = True
                elif close(value, 49.0, 1e-6):
                    state.length_comp = False
                    state.h_offset = None
                elif rounded in {40, 41, 42} and close(value, float(rounded), 1e-6):
                    state.comp = rounded
                    if rounded == 40:
                        state.d_offset = None

            if "T" in words:
                state.pending_tool = integer(words["T"][-1], "T")
                result.selected_tools.append(state.pending_tool)
            if "S" in words:
                state.spindle = words["S"][-1]
            if "F" in words:
                state.feed = words["F"][-1] * factor
            if "H" in words:
                state.h_offset = integer(words["H"][-1], "H")
            if "D" in words:
                state.d_offset = integer(words["D"][-1], "D")
            if 6 in mcodes:
                if state.pending_tool is None:
                    raise EvaluationError("M6 without T")
                state.tool = state.pending_tool
                result.changed_tools.append(state.tool)
            if 3 in mcodes:
                state.spindle_on = True
            if 5 in mcodes:
                state.spindle_on = False

            has_axis = any(axis in words for axis in ("X", "Y", "Z"))
            if has_axis and not (machine or g52):
                if state.units is None or state.absolute is None or state.motion is None:
                    raise EvaluationError("motion before units/distance/motion mode")

                def coordinate(axis: str, old: float) -> float:
                    if axis not in words:
                        return old
                    value = words[axis][-1] * factor
                    return value if state.absolute else old + value

                new = Point(
                    coordinate("X", state.current.x),
                    coordinate("Y", state.current.y),
                    coordinate("Z", state.current.z),
                )
                samples = (
                    arc_samples(state.current, new, words, factor, state.motion == 2)
                    if state.motion in {2, 3}
                    else line_samples(state.current, new)
                )
                result.sample_count += len(samples)
                if len(result.segments) >= MAX_SEGMENTS or result.sample_count > MAX_SAMPLES:
                    raise EvaluationError("geometry resource limit exceeded")
                result.segments.append(
                    Segment(
                        state.current,
                        new,
                        samples,
                        state.motion,
                        state.tool,
                        state.spindle,
                        state.spindle_on,
                        state.feed,
                        state.wcs,
                        state.length_comp,
                        state.h_offset,
                        state.comp,
                        state.d_offset,
                        False,
                    )
                )
                state.current = new
            elif has_axis and close(next((value for value in gcodes if close(value, 53.0, 1e-6)), 0.0), 53.0, 1e-6):
                # Preserve evidence of explicit G53 cutting attempts while not
                # mixing machine coordinates with local work geometry.
                if state.motion in {1, 2, 3}:
                    result.segments.append(
                        Segment(state.current, state.current, [state.current], state.motion, state.tool,
                                state.spindle, state.spindle_on, state.feed, state.wcs,
                                state.length_comp, state.h_offset, state.comp, state.d_offset, True)
                    )

            if 98 in mcodes:
                if "P" not in words:
                    raise EvaluationError("M98 requires P")
                target = integer(words["P"][-1], "P")
                repeats = integer(words.get("L", [1])[-1], "L")
                if target not in programs or target == order[0] or not 1 <= repeats <= 20:
                    raise EvaluationError("invalid M98 target or repeat")
                result.called_programs.extend([target] * repeats)
                for _ in range(repeats):
                    run(target)
            if number == order[0] and (2 in mcodes or 30 in mcodes):
                result.terminated = True
                break
            if number != order[0] and 99 in mcodes:
                break
        active_calls.pop()

    run(order[0])
    called = set(result.called_programs)
    if called != set(order[1:]):
        raise EvaluationError("unreferenced or missing subprogram")
    return result


def xy_length(segment: Segment) -> float:
    return math.hypot(segment.end.x - segment.start.x, segment.end.y - segment.start.y)


def horizontal(segment: Segment, tolerance: float = 0.25) -> bool:
    return abs(segment.start.z - segment.end.z) <= tolerance and xy_length(segment) > 1e-4


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise EvaluationError("empty percentile")
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * fraction))))
    return ordered[index]


def outside_distance(x: float, y: float, cx: float, cy: float) -> float:
    dx = abs(x - cx) - PART_X / 2.0
    dy = abs(y - cy) - PART_Y / 2.0
    if dx <= 0 and dy <= 0:
        return -min(-dx, -dy)
    return math.hypot(max(dx, 0.0), max(dy, 0.0))


def covered(points: Iterable[Point], x: float, y: float, tolerance: float) -> bool:
    return any(math.hypot(point.x - x, point.y - y) <= tolerance for point in points)


def rectangle_targets(cx: float, cy: float, half_x: float, half_y: float, spacing: float = 5.0) -> list[tuple[float, float]]:
    targets: list[tuple[float, float]] = []
    count_x = max(1, int(math.ceil(2 * half_x / spacing)))
    count_y = max(1, int(math.ceil(2 * half_y / spacing)))
    for index in range(count_x + 1):
        x = cx - half_x + 2 * half_x * index / count_x
        targets.extend([(x, cy - half_y), (x, cy + half_y)])
    for index in range(count_y + 1):
        y = cy - half_y + 2 * half_y * index / count_y
        targets.extend([(cx - half_x, y), (cx + half_x, y)])
    return targets


def validate_station(segments: list[Segment], wcs: str) -> None:
    station = [segment for segment in segments if segment.wcs == wcs and not segment.machine]
    cuts = [segment for segment in station if segment.motion in {1, 2, 3} and distance(segment.start, segment.end) > 1e-5]
    if not cuts:
        raise EvaluationError(f"{wcs} has no cutting motion")
    for segment in cuts:
        if (
            segment.tool != 1
            or not segment.spindle_on
            or segment.spindle is None
            or not close(segment.spindle, SPINDLE_RPM, 1.0)
            or segment.feed is None
            or not close(segment.feed, FEED_MM_MIN, 1.0)
            or not segment.length_comp
            or segment.h_offset != 1
        ):
            raise EvaluationError(f"{wcs} contains cutting with invalid T/S/F/H state")

    horizontal_cuts = [segment for segment in cuts if horizontal(segment)]
    if not horizontal_cuts:
        raise EvaluationError(f"{wcs} lacks horizontal machining")
    face_z = max((segment.start.z + segment.end.z) / 2.0 for segment in horizontal_cuts)
    bottom_z = min((segment.start.z + segment.end.z) / 2.0 for segment in horizontal_cuts)
    depth = face_z - bottom_z
    if not 9.5 <= depth <= 10.75:
        raise EvaluationError(f"{wcs} lacks the required 10 mm face-to-contour depth")

    deep_segments = [
        segment
        for segment in horizontal_cuts
        if abs((segment.start.z + segment.end.z) / 2.0 - bottom_z) <= 0.35
    ]
    deep_points = [point for segment in deep_segments for point in segment.samples]
    if len(deep_points) < 40 or sum(xy_length(segment) for segment in deep_segments) < 130.0:
        raise EvaluationError(f"{wcs} contour is incomplete")
    xs = [point.x for point in deep_points]
    ys = [point.y for point in deep_points]
    cx = (percentile(xs, 0.05) + percentile(xs, 0.95)) / 2.0
    cy = (percentile(ys, 0.05) + percentile(ys, 0.95)) / 2.0

    face_segments = [
        segment
        for segment in horizontal_cuts
        if abs((segment.start.z + segment.end.z) / 2.0 - face_z) <= 0.35
    ]
    face_points = [point for segment in face_segments for point in segment.samples]
    if len(face_points) < 80 or sum(xy_length(segment) for segment in face_segments) < 150.0:
        raise EvaluationError(f"{wcs} face sweep is too small")
    for ix in range(10):
        x = cx - PART_X / 2.0 + PART_X * ix / 9.0
        for iy in range(7):
            y = cy - PART_Y / 2.0 + PART_Y * iy / 6.0
            if not covered(face_points, x, y, TOOL_RADIUS_MM + 0.35):
                raise EvaluationError(f"{wcs} face undercoverage")

    offset_targets = rectangle_targets(cx, cy, PART_X / 2.0 + TOOL_RADIUS_MM, PART_Y / 2.0 + TOOL_RADIUS_MM)
    nominal_targets = rectangle_targets(cx, cy, PART_X / 2.0, PART_Y / 2.0)
    offset_ok = all(covered(deep_points, x, y, 1.25) for x, y in offset_targets)
    nominal_ok = all(covered(deep_points, x, y, 1.25) for x, y in nominal_targets)
    if offset_ok:
        if any(outside_distance(point.x, point.y, cx, cy) < 2.7 for point in deep_points):
            raise EvaluationError(f"{wcs} contour intrudes into the part")
    elif nominal_ok:
        if not any(segment.comp in {41, 42} and segment.d_offset is not None and segment.d_offset > 0 for segment in deep_segments):
            raise EvaluationError(f"{wcs} nominal contour lacks controller compensation")
        if any(outside_distance(point.x, point.y, cx, cy) < -0.75 for point in deep_points):
            raise EvaluationError(f"{wcs} compensated contour self-intersects the part")
    else:
        raise EvaluationError(f"{wcs} lacks a closed full outside contour")

    for segment in station:
        if segment.motion != 0 or min(segment.start.z, segment.end.z) >= face_z - 0.5:
            continue
        if any(outside_distance(point.x, point.y, cx, cy) < 2.7 for point in segment.samples):
            raise EvaluationError(f"{wcs} has a rapid move through stock")


def validate_result(result: ProgramResult) -> None:
    if not result.terminated or not result.segments:
        raise EvaluationError("program did not terminate after real motion")
    if not result.selected_tools or any(tool != 1 for tool in result.selected_tools):
        raise EvaluationError("only T1 may be selected")
    if not result.changed_tools or any(tool != 1 for tool in result.changed_tools):
        raise EvaluationError("only T1 may be changed")
    if any(segment.machine and segment.motion in {1, 2, 3} for segment in result.segments):
        raise EvaluationError("machine-coordinate cutting is not station geometry")
    offsets = {segment.wcs for segment in result.segments if segment.wcs is not None and not segment.machine}
    approved = (
        {"G54", "G55", "G56", "G57"},
        {"G54.1P1", "G54.1P2", "G54.1P3", "G54.1P4"},
    )
    expected = next((group for group in approved if offsets == group), None)
    if expected is None:
        raise EvaluationError("program must use exactly four approved posted offsets")
    for wcs in sorted(expected):
        validate_station(result.segments, wcs)


def evaluate_text(src: str) -> bool:
    try:
        validate_result(execute(src))
        return True
    except (EvaluationError, ValueError, OverflowError, RecursionError):
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
