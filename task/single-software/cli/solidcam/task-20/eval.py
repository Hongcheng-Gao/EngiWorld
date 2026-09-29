from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from pathlib import Path


TARGET = Path(os.environ.get("EVAL_TARGET_DIR", r"C:\Users\User\Desktop"))
NC_NAME = "task-20.nc"
WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))")

CONTRACT = {
    "program": 2040,
    "part_half": (60.0, 40.0),
    "tools": {
        1: {"diameter": 16.0, "spindle": 6500.0, "feed": 700.0},
        2: {"diameter": 10.0, "spindle": 8000.0, "feed": 500.0},
        3: {"diameter": 5.0, "spindle": 5000.0, "feed": 180.0},
        4: {"diameter": 8.0, "spindle": 5500.0, "feed": 220.0},
    },
    "pockets": (
        (-48.0, -22.0, -10.0, 10.0),
        (-13.0, 13.0, -10.0, 10.0),
        (22.0, 48.0, -10.0, 10.0),
    ),
    "holes": tuple(
        (x, y)
        for x in (-45.0, -15.0, 15.0, 45.0)
        for y in (-28.0, -12.0, 12.0, 28.0)
    ),
    "counterbores": ((-30.0, 25.0), (30.0, 25.0)),
}


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


@dataclass
class Program:
    segments: list[Segment]
    tools: list[int]
    programs: list[int]
    terminated: bool
    executable_lines: int


def close(actual: float, expected: float, tolerance: float) -> bool:
    return abs(actual - expected) <= tolerance


def distance(a: Point, b: Point) -> float:
    return math.dist((a.x, a.y, a.z), (b.x, b.y, b.z))


def path_length(points: list[Point]) -> float:
    return sum(distance(a, b) for a, b in zip(points, points[1:]))


def dense_line(a: Point, b: Point, spacing: float = 0.5) -> list[Point]:
    count = max(1, int(math.ceil(distance(a, b) / spacing)))
    return [
        Point(
            a.x + (b.x - a.x) * index / count,
            a.y + (b.y - a.y) * index / count,
            a.z + (b.z - a.z) * index / count,
        )
        for index in range(count + 1)
    ]


def arc_points(a: Point, b: Point, i: float, j: float, clockwise: bool) -> list[Point]:
    cx, cy = a.x + i, a.y + j
    radius = math.hypot(a.x - cx, a.y - cy)
    end_radius = math.hypot(b.x - cx, b.y - cy)
    if radius <= 1e-6 or not close(end_radius, radius, 0.25):
        raise EvaluationError("invalid I/J arc")
    start = math.atan2(a.y - cy, a.x - cx)
    finish = math.atan2(b.y - cy, b.x - cx)
    sweep = (start - finish) % (2 * math.pi) if clockwise else (finish - start) % (2 * math.pi)
    if sweep <= 1e-9:
        sweep = 2 * math.pi
    direction = -1.0 if clockwise else 1.0
    count = max(16, int(math.ceil(radius * sweep / 0.35)))
    return [
        Point(
            cx + radius * math.cos(start + direction * sweep * index / count),
            cy + radius * math.sin(start + direction * sweep * index / count),
            a.z + (b.z - a.z) * index / count,
        )
        for index in range(count + 1)
    ]


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


def parse_program(src: str) -> Program:
    units: str | None = None
    absolute: bool | None = None
    motion: int | None = None
    current = Point(0.0, 0.0, 0.0)
    pending_tool: int | None = None
    tool: int | None = None
    spindle: float | None = None
    feed: float | None = None
    spindle_on = False
    wcs: str | None = None
    length_comp = False
    h_offset: int | None = None
    cycle: int | None = None
    cycle_z: float | None = None
    cycle_r: float | None = None
    terminated = False
    executable = 0
    tools: list[int] = []
    programs: list[int] = []
    segments: list[Segment] = []

    for line in strip_comments(src):
        if not line or line == "%":
            continue
        if any(char in line for char in "#[]="):
            raise EvaluationError("macros and expressions are unsupported")
        if re.fullmatch(r"O\d+", line):
            if terminated:
                raise EvaluationError("code after M30")
            programs.append(int(line[1:]))
            executable += 1
            continue
        words = WORD_RE.findall(line)
        remainder = re.sub(r"[\s/]+", "", WORD_RE.sub("", line))
        if not words or remainder:
            raise EvaluationError("unknown executable text")
        if terminated:
            raise EvaluationError("code after M30")
        executable += 1
        grouped: dict[str, list[float]] = {}
        for letter, value in words:
            grouped.setdefault(letter, []).append(float(value))
        if any(axis in grouped for axis in ("A", "B", "C")):
            raise EvaluationError("rotary axis is forbidden")
        if any(letter not in "NGMXYZIJRQPTSFHD" for letter in grouped):
            raise EvaluationError("unsupported address word")

        machine_move = False
        set_length: bool | None = None
        for g in grouped.get("G", []):
            rounded = int(round(g))
            if close(g, 20.0, 1e-6):
                units = "inch"
            elif close(g, 21.0, 1e-6):
                units = "mm"
            elif close(g, 90.0, 1e-6):
                absolute = True
            elif close(g, 91.0, 1e-6):
                absolute = False
            elif rounded in (0, 1, 2, 3) and close(g, float(rounded), 1e-6):
                motion = rounded
            elif rounded in (54, 55, 56, 57, 58, 59) and close(g, float(rounded), 1e-6):
                wcs = f"G{rounded}"
            elif close(g, 54.1, 1e-6):
                p_value = int(round(grouped.get("P", [0.0])[-1]))
                if p_value <= 0:
                    raise EvaluationError("invalid extended WCS")
                wcs = f"G54.1P{p_value}"
            elif close(g, 43.0, 1e-6):
                set_length = True
            elif close(g, 49.0, 1e-6):
                set_length = False
            elif rounded in (81, 82, 83) and close(g, float(rounded), 1e-6):
                cycle = rounded
            elif close(g, 80.0, 1e-6):
                cycle = None
            elif rounded in (28, 53) and close(g, float(rounded), 1e-6):
                machine_move = True
            elif rounded in (17, 40, 41, 42, 94, 98, 99) and close(g, float(rounded), 1e-6):
                pass
            else:
                raise EvaluationError(f"unsupported G{g:g}")

        mcodes = [int(round(value)) for value in grouped.get("M", [])]
        if any(code not in (0, 1, 3, 4, 5, 6, 8, 9, 30) for code in mcodes):
            raise EvaluationError("unsupported M code")
        if "T" in grouped:
            pending_tool = int(round(grouped["T"][-1]))
            if pending_tool <= 0:
                raise EvaluationError("invalid tool number")
        if 6 in mcodes:
            if pending_tool is None:
                raise EvaluationError("M6 without T")
            tool = pending_tool
            tools.append(tool)
            spindle = None
            feed = None
            spindle_on = False
            length_comp = False
            h_offset = None
            cycle = None
            cycle_z = None
            cycle_r = None

        factor = 25.4 if units == "inch" else 1.0
        if "S" in grouped:
            spindle = grouped["S"][-1]
        if "F" in grouped:
            feed = grouped["F"][-1] * factor
        if "H" in grouped:
            h_offset = int(round(grouped["H"][-1]))
        if set_length is True:
            length_comp = True
        elif set_length is False:
            length_comp = False
            h_offset = None
        if 3 in mcodes or 4 in mcodes:
            spindle_on = True
        if 5 in mcodes:
            spindle_on = False
        if 30 in mcodes:
            terminated = True

        has_position = any(axis in grouped for axis in ("X", "Y", "Z"))
        has_arc = motion in (2, 3) and "I" in grouped and "J" in grouped
        if (has_position or has_arc or "F" in grouped) and units is None:
            raise EvaluationError("motion or feed before units")
        if has_position and absolute is None:
            raise EvaluationError("position before distance mode")

        def coordinate(axis: str, old: float) -> float:
            if axis not in grouped:
                return old
            value = grouped[axis][-1] * factor
            return value if absolute else old + value

        new = Point(
            coordinate("X", current.x),
            coordinate("Y", current.y),
            coordinate("Z", current.z),
        )
        if machine_move:
            continue
        if cycle is not None and has_position:
            if "Z" in grouped:
                cycle_z = new.z
            if "R" in grouped:
                r_value = grouped["R"][-1] * factor
                cycle_r = r_value if absolute else current.z + r_value
            if cycle_z is None or cycle_r is None:
                raise EvaluationError("incomplete drill cycle")
            top = Point(new.x, new.y, cycle_r)
            bottom = Point(new.x, new.y, cycle_z)
            segments.append(Segment(current, top, dense_line(current, top), 0, tool, spindle, spindle_on, feed, wcs, length_comp, h_offset))
            segments.append(Segment(top, bottom, dense_line(top, bottom), 1, tool, spindle, spindle_on, feed, wcs, length_comp, h_offset))
            current = top
            continue
        if (has_position or has_arc) and motion is not None:
            if motion in (2, 3):
                if "I" not in grouped or "J" not in grouped:
                    raise EvaluationError("arc requires I/J")
                samples = arc_points(
                    current,
                    new,
                    grouped["I"][-1] * factor,
                    grouped["J"][-1] * factor,
                    motion == 2,
                )
            else:
                samples = dense_line(current, new)
            segments.append(Segment(current, new, samples, motion, tool, spindle, spindle_on, feed, wcs, length_comp, h_offset))
            current = new
    return Program(segments, tools, programs, terminated, executable)


def cutting_segments(program: Program, tool: int) -> list[Segment]:
    spec = CONTRACT["tools"][tool]
    return [
        segment
        for segment in program.segments
        if segment.tool == tool
        and segment.motion in (1, 2, 3)
        and path_length(segment.samples) > 0.01
        and segment.spindle_on
        and segment.spindle is not None
        and close(segment.spindle, spec["spindle"], 1.0)
        and segment.feed is not None
        and close(segment.feed, spec["feed"], 0.8)
        and segment.wcs == "G54"
        and segment.length_comp
        and segment.h_offset is not None
        and segment.h_offset > 0
    ]


def check_face(program: Program) -> None:
    cuts = cutting_segments(program, 1)
    radius = CONTRACT["tools"][1]["diameter"] / 2.0
    if any(point.z < -0.4 for segment in cuts for point in segment.samples):
        raise EvaluationError("face cut is below the part top")
    points = [point for segment in cuts for point in segment.samples if abs(point.z) <= 0.3]
    targets = [
        (x, y)
        for x in (-60.0, -30.0, 0.0, 30.0, 60.0)
        for y in (-40.0, -20.0, 0.0, 20.0, 40.0)
    ]
    if len(points) < 100 or not all(
        any(math.hypot(point.x - x, point.y - y) <= radius + 0.75 for point in points)
        for x, y in targets
    ):
        raise EvaluationError("face coverage is incomplete")


def check_pockets(program: Program) -> None:
    cuts = cutting_segments(program, 2)
    radius = CONTRACT["tools"][2]["diameter"] / 2.0
    points = [
        point
        for segment in cuts
        if abs(segment.start.z + 3.0) <= 0.35 and abs(segment.end.z + 3.0) <= 0.35
        for point in segment.samples
    ]
    if len(points) < 60:
        raise EvaluationError("pocket-bottom cutting is absent")
    for xmin, xmax, ymin, ymax in CONTRACT["pockets"]:
        local = [
            point
            for point in points
            if xmin - 0.75 <= point.x <= xmax + 0.75
            and ymin - 0.75 <= point.y <= ymax + 0.75
        ]
        targets = [
            (x, y)
            for x in (xmin + radius, (xmin + xmax) / 2.0, xmax - radius)
            for y in (ymin + radius, (ymin + ymax) / 2.0, ymax - radius)
        ]
        if not all(
            any(math.hypot(point.x - x, point.y - y) <= radius + 0.75 for point in local)
            for x, y in targets
        ):
            raise EvaluationError("one or more pockets are incomplete")
    if any(
        not any(
            xmin - 0.75 <= point.x <= xmax + 0.75
            and ymin - 0.75 <= point.y <= ymax + 0.75
            for xmin, xmax, ymin, ymax in CONTRACT["pockets"]
        )
        for point in points
    ):
        raise EvaluationError("unexpected T2 cut at pocket depth")


def unique_locations(values: list[tuple[float, float]], tolerance: float = 0.75) -> list[tuple[float, float]]:
    unique: list[tuple[float, float]] = []
    for x, y in values:
        if not any(math.hypot(x - px, y - py) <= tolerance for px, py in unique):
            unique.append((x, y))
    return unique


def check_drilling(program: Program) -> None:
    cuts = cutting_segments(program, 3)
    if any(point.z < -20.0 for segment in cuts for point in segment.samples):
        raise EvaluationError("drill depth is implausibly deep")
    actual = unique_locations([
        (segment.end.x, segment.end.y)
        for segment in cuts
        if math.hypot(segment.end.x - segment.start.x, segment.end.y - segment.start.y) <= 0.25
        and min(segment.start.z, segment.end.z) <= -11.9
    ])
    expected = [*CONTRACT["holes"], *CONTRACT["counterbores"]]
    if len(actual) != len(expected):
        raise EvaluationError("T3 must drill exactly 18 physical locations")
    if any(
        not any(math.hypot(x - px, y - py) <= 0.75 for px, py in actual)
        for x, y in expected
    ):
        raise EvaluationError("a required T3 through hole is missing")
    if any(
        not any(math.hypot(x - px, y - py) <= 0.75 for x, y in expected)
        for px, py in actual
    ):
        raise EvaluationError("an unexpected T3 through hole is present")


def check_counterbores(program: Program) -> None:
    cuts = cutting_segments(program, 4)
    if any(point.z < -3.5 for segment in cuts for point in segment.samples):
        raise EvaluationError("counterbore is too deep")
    for center_x, center_y in CONTRACT["counterbores"]:
        candidates = []
        for segment in cuts:
            if segment.motion not in (2, 3):
                continue
            samples = [point for point in segment.samples if abs(point.z + 3.0) <= 0.35]
            if len(samples) < 12 or distance(samples[0], samples[-1]) > 1.0:
                continue
            radii = [math.hypot(point.x - center_x, point.y - center_y) for point in samples]
            mean_radius = sum(radii) / len(radii)
            if 0.5 <= mean_radius <= 5.5 and max(abs(value - mean_radius) for value in radii) <= 0.5:
                bins = {
                    int((math.atan2(point.y - center_y, point.x - center_x) % (2 * math.pi)) / (2 * math.pi) * 12) % 12
                    for point in samples
                }
                if len(bins) >= 10:
                    candidates.append(segment)
        if not candidates:
            raise EvaluationError("counterbore lacks a complete circular T4 cut")
    for segment in cuts:
        for point in segment.samples:
            if point.z <= -0.5 and min(
                math.hypot(point.x - x, point.y - y)
                for x, y in CONTRACT["counterbores"]
            ) > 6.0:
                raise EvaluationError("unexpected T4 cutting location")


def profile_runs(program: Program) -> list[list[Point]]:
    runs: list[list[Point]] = []
    run: list[Point] = []
    for segment in cutting_segments(program, 2):
        horizontal = (
            abs(segment.start.z - segment.end.z) <= 0.3
            and min(segment.start.z, segment.end.z) <= -11.65
        )
        if horizontal:
            if run and distance(run[-1], segment.start) > 0.75:
                runs.append(run)
                run = []
            if not run:
                run.append(segment.start)
            run.extend(segment.samples[1:])
        elif run:
            runs.append(run)
            run = []
    if run:
        runs.append(run)
    return runs


def check_profile(program: Program) -> None:
    cuts = cutting_segments(program, 2)
    if any(point.z < -12.5 for segment in cuts for point in segment.samples):
        raise EvaluationError("outside profile is too deep")
    for run in profile_runs(program):
        for offset in (0.0, 5.0):
            xedge, yedge = 60.0 + offset, 40.0 + offset
            anchors = [
                *[(x, yedge) for x in (-xedge, 0.0, xedge)],
                *[(x, -yedge) for x in (-xedge, 0.0, xedge)],
                *[(-xedge, y) for y in (-yedge, 0.0, yedge)],
                *[(xedge, y) for y in (-yedge, 0.0, yedge)],
            ]
            if path_length(run) >= 320.0 and all(
                any(math.hypot(point.x - x, point.y - y) <= 1.75 for point in run)
                for x, y in anchors
            ):
                return
    raise EvaluationError("full-depth outside profile is incomplete")


def validate_program(program: Program) -> None:
    if not program.terminated or program.executable_lines < 50:
        raise EvaluationError("incomplete program")
    if program.programs != [CONTRACT["program"]]:
        raise EvaluationError("wrong O-number")
    if set(program.tools) != set(CONTRACT["tools"]):
        raise EvaluationError("tool set must be exactly T1 through T4")
    for tool in CONTRACT["tools"]:
        if not cutting_segments(program, tool):
            raise EvaluationError(f"T{tool} lacks valid cutting motion")
    check_face(program)
    check_pockets(program)
    check_drilling(program)
    check_counterbores(program)
    check_profile(program)


def evaluate_text(src: str) -> bool:
    try:
        validate_program(parse_program(src))
        return True
    except (EvaluationError, ValueError, OverflowError):
        return False


def main() -> bool:
    path = TARGET / NC_NAME
    if not path.is_file() or path.stat().st_size <= 0 or path.stat().st_size > 2_000_000:
        return False
    return evaluate_text(path.read_text(encoding="utf-8", errors="strict"))


if __name__ == "__main__":
    try:
        ok = main()
    except Exception:
        ok = False
    print("True" if ok else "False")
    raise SystemExit(0)
