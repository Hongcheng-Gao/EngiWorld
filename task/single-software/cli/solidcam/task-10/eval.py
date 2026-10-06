from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path


TARGET = Path(os.environ.get("EVAL_TARGET_DIR", r"C:\Users\User\Desktop"))
NC_NAME = "task-10.nc"
MAX_BYTES = 2_000_000
MAX_LINES = 20_000
MAX_EXECUTED_BLOCKS = 50_000
MAX_SEGMENTS = 8_000
MAX_SAMPLES = 250_000
TOOL_RADIUS_MM = 4.0
SPINDLE_RPM = 8000.0
FEED_MM_MIN = 500.0
POCKET_HALF_X_MM = 21.0
POCKET_HALF_Y_MM = 13.0
CENTER_LIMIT_X_MM = POCKET_HALF_X_MM - TOOL_RADIUS_MM
CENTER_LIMIT_Y_MM = POCKET_HALF_Y_MM - TOOL_RADIUS_MM
FIXTURE_RELATIVE_BOX = (-60.0, 60.0, 39.0, 51.0, -16.0, 8.0)
REQUIRED_FIXTURE_CLEARANCE_MM = 3.0
WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))")
INTEGER_WORDS = {"N", "O", "M", "T", "H", "D", "P", "L"}
ALLOWED_WORDS = set("NOGMXYZIJKRFS THDPL".replace(" ", ""))
ALLOWED_G = {
    0.0, 1.0, 2.0, 3.0, 17.0, 20.0, 21.0, 28.0, 40.0, 41.0, 42.0,
    43.0, 49.0, 52.0, 53.0, 54.0, 55.0, 56.0, 57.0, 58.0, 59.0,
    80.0, 90.0, 91.0, 94.0,
}
ALLOWED_M = {2, 3, 4, 5, 6, 8, 9, 30, 98, 99}


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
    local_shift: Point
    length_comp: bool
    h_offset: int | None
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
    local_shift: Point = Point(0.0, 0.0, 0.0)
    length_comp: bool = False
    h_offset: int | None = None


@dataclass
class ProgramResult:
    segments: list[Segment] = field(default_factory=list)
    selected_tools: list[int] = field(default_factory=list)
    changed_tools: list[int] = field(default_factory=list)
    called_programs: list[int] = field(default_factory=list)
    executed_blocks: int = 0
    sample_count: int = 0
    terminated: bool = False


def close(a: float, b: float, tolerance: float) -> bool:
    return abs(a - b) <= tolerance


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
            if g52:
                if state.units is None:
                    raise EvaluationError("G52 before units")
                state.local_shift = Point(
                    words.get("X", [state.local_shift.x / factor])[-1] * factor,
                    words.get("Y", [state.local_shift.y / factor])[-1] * factor,
                    words.get("Z", [state.local_shift.z / factor])[-1] * factor,
                )
                if max(abs(state.local_shift.x), abs(state.local_shift.y), abs(state.local_shift.z)) > 1000.0:
                    raise EvaluationError("excessive G52 shift")

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

            if "T" in words:
                state.pending_tool = integer(words["T"][-1], "T")
                result.selected_tools.append(state.pending_tool)
            if "S" in words:
                state.spindle = words["S"][-1]
            if "F" in words:
                state.feed = words["F"][-1] * factor
            if "H" in words:
                state.h_offset = integer(words["H"][-1], "H")
            if 6 in mcodes:
                if state.pending_tool is None:
                    raise EvaluationError("M6 without T")
                state.tool = state.pending_tool
                result.changed_tools.append(state.tool)
            if 3 in mcodes or 4 in mcodes:
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
                        state.local_shift,
                        state.length_comp,
                        state.h_offset,
                        False,
                    )
                )
                state.current = new
            elif has_axis and machine and state.motion in {1, 2, 3}:
                result.segments.append(
                    Segment(
                        state.current, state.current, [state.current], state.motion, state.tool,
                        state.spindle, state.spindle_on, state.feed, state.wcs, state.local_shift,
                        state.length_comp, state.h_offset, True,
                    )
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
    if set(result.called_programs) != set(order[1:]):
        raise EvaluationError("unreferenced or missing subprogram")
    return result


def horizontal(segment: Segment, tolerance: float = 0.2) -> bool:
    return abs(segment.start.z - segment.end.z) <= tolerance and math.hypot(
        segment.end.x - segment.start.x, segment.end.y - segment.start.y
    ) > 1e-4


def point_box_distance(point: Point, box: tuple[float, ...]) -> float:
    xmin, xmax, ymin, ymax, zmin, zmax = box
    return math.sqrt(
        max(xmin - point.x, 0.0, point.x - xmax) ** 2
        + max(ymin - point.y, 0.0, point.y - ymax) ** 2
        + max(zmin - point.z, 0.0, point.z - zmax) ** 2
    )


def covered(points: list[Point], x: float, y: float, tolerance: float) -> bool:
    return any(math.hypot(point.x - x, point.y - y) <= tolerance for point in points)


def validate_pocket(result: ProgramResult) -> None:
    if not result.terminated or not result.segments:
        raise EvaluationError("program did not terminate after real motion")
    if not result.selected_tools or any(tool != 1 for tool in result.selected_tools):
        raise EvaluationError("only T1 may be selected")
    if not result.changed_tools or any(tool != 1 for tool in result.changed_tools):
        raise EvaluationError("only T1 may be changed")
    if any(segment.machine and segment.motion in {1, 2, 3} for segment in result.segments):
        raise EvaluationError("machine-coordinate cutting is not pocket geometry")

    cuts = [
        segment
        for segment in result.segments
        if segment.motion in {1, 2, 3} and distance(segment.start, segment.end) > 1e-5
    ]
    if not cuts:
        raise EvaluationError("missing cutting motion")
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
            or (segment.wcs is None and max(abs(segment.local_shift.x), abs(segment.local_shift.y), abs(segment.local_shift.z)) <= 1e-6)
        ):
            raise EvaluationError("cutting motion has invalid T/S/F/H/coordinate state")

    horizontal_cuts = [segment for segment in cuts if horizontal(segment)]
    if not horizontal_cuts:
        raise EvaluationError("missing horizontal pocket clearing")
    bottom_z = min((segment.start.z + segment.end.z) / 2.0 for segment in horizontal_cuts)
    if not close(bottom_z, -10.0, 0.35):
        raise EvaluationError("final pocket depth is not 10 mm")
    bottom_segments = [
        segment
        for segment in horizontal_cuts
        if abs((segment.start.z + segment.end.z) / 2.0 - bottom_z) <= 0.35
    ]
    bottom_points = [point for segment in bottom_segments for point in segment.samples]
    if len(bottom_points) < 80:
        raise EvaluationError("bottom clearing is incomplete")
    xmin, xmax = min(point.x for point in bottom_points), max(point.x for point in bottom_points)
    ymin, ymax = min(point.y for point in bottom_points), max(point.y for point in bottom_points)
    center_x, center_y = (xmin + xmax) / 2.0, (ymin + ymax) / 2.0
    if not (33.0 <= xmax - xmin <= 35.2 and 17.0 <= ymax - ymin <= 19.2):
        raise EvaluationError("D8 tool-center pocket envelope is wrong")
    if any(
        abs(point.x - center_x) > CENTER_LIMIT_X_MM + 0.65
        or abs(point.y - center_y) > CENTER_LIMIT_Y_MM + 0.65
        for point in bottom_points
    ):
        raise EvaluationError("bottom path overcuts the pocket wall")

    # A D8 end mill clears a rectangular pocket with R4 internal corners.
    for ix in range(-10, 11):
        x = center_x + ix * 2.0
        for iy in range(-6, 7):
            y = center_y + iy * 2.0
            corner_dx = max(abs(x - center_x) - CENTER_LIMIT_X_MM, 0.0)
            corner_dy = max(abs(y - center_y) - CENTER_LIMIT_Y_MM, 0.0)
            if math.hypot(corner_dx, corner_dy) <= TOOL_RADIUS_MM + 0.05:
                if not covered(bottom_points, x, y, TOOL_RADIUS_MM + 0.2):
                    raise EvaluationError("pocket bottom undercoverage")

    for segment in cuts:
        if min(segment.start.z, segment.end.z) >= -0.5:
            continue
        if any(
            abs(point.x - center_x) > CENTER_LIMIT_X_MM + 1.25
            or abs(point.y - center_y) > CENTER_LIMIT_Y_MM + 1.25
            for point in segment.samples
        ):
            raise EvaluationError("deep cutting leaves the pocket envelope")

    fixture = (
        center_x + FIXTURE_RELATIVE_BOX[0], center_x + FIXTURE_RELATIVE_BOX[1],
        center_y + FIXTURE_RELATIVE_BOX[2], center_y + FIXTURE_RELATIVE_BOX[3],
        FIXTURE_RELATIVE_BOX[4], FIXTURE_RELATIVE_BOX[5],
    )
    required_center_distance = TOOL_RADIUS_MM + REQUIRED_FIXTURE_CLEARANCE_MM
    for segment in result.segments:
        if segment.machine:
            continue
        if any(point_box_distance(point, fixture) < required_center_distance - 0.05 for point in segment.samples):
            raise EvaluationError("continuous tool sweep violates fixture clearance")
    if not any(
        segment.motion == 0 and max(point.z for point in segment.samples) >= 25.0
        for segment in result.segments if not segment.machine
    ):
        raise EvaluationError("missing fixture-safe clearance approach")


def evaluate_text(src: str) -> bool:
    try:
        validate_pocket(execute(src))
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
