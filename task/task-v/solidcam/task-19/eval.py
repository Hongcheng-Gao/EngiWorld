from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from pathlib import Path


TARGET = Path(os.environ.get("EVAL_TARGET_DIR", os.environ.get("OUTPUT_ROOT", r"C:\Users\User\Desktop")))
NC_NAME = "task-19.nc"
WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))")
ALLOWED_LETTERS = set("NGMXYZABCIJKRFSTHDPL")


class EvaluationError(ValueError):
    pass


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class Segment:
    start: Point
    end: Point
    samples: tuple[Point, ...]
    motion: int
    tool: int | None
    spindle_on: bool
    spindle: float | None
    feed: float | None
    wcs: int | None
    line_number: int


@dataclass
class Program:
    segments: list[Segment]
    tools: list[int]
    terminated: bool
    units_selected: bool
    distance_mode_selected: bool
    executable_blocks: int


def close(actual: float, expected: float, tolerance: float) -> bool:
    return abs(actual - expected) <= tolerance


def xy_distance(a: Point, b: Point) -> float:
    return math.hypot(b.x - a.x, b.y - a.y)


def dense_line(a: Point, b: Point, spacing: float = 0.5) -> tuple[Point, ...]:
    length = math.dist((a.x, a.y, a.z), (b.x, b.y, b.z))
    count = max(1, int(math.ceil(length / spacing)))
    return tuple(
        Point(
            a.x + (b.x - a.x) * index / count,
            a.y + (b.y - a.y) * index / count,
            a.z + (b.z - a.z) * index / count,
        )
        for index in range(count + 1)
    )


def strip_comments(source: str) -> list[str]:
    lines: list[str] = []
    depth = 0
    for raw in source.upper().splitlines():
        clean: list[str] = []
        for char in raw:
            if char == ";" and depth == 0:
                break
            if char == "(":
                depth += 1
            elif char == ")":
                if depth == 0:
                    raise EvaluationError("unmatched closing comment")
                depth -= 1
            elif depth == 0:
                clean.append(char)
        lines.append("".join(clean).strip())
    if depth:
        raise EvaluationError("unterminated parenthesis comment")
    return lines


def directed_sweep(start: float, end: float, clockwise: bool) -> float:
    if clockwise:
        sweep = -((start - end) % (2.0 * math.pi))
        return -2.0 * math.pi if abs(sweep) < 1e-12 else sweep
    sweep = (end - start) % (2.0 * math.pi)
    return 2.0 * math.pi if abs(sweep) < 1e-12 else sweep


def arc_samples(
    start: Point,
    end: Point,
    clockwise: bool,
    i: float | None,
    j: float | None,
    radius_word: float | None,
    arc_center_absolute: bool,
) -> tuple[Point, ...]:
    if i is not None or j is not None:
        if i is None or j is None:
            raise EvaluationError("arc requires both I and J")
        cx = i if arc_center_absolute else start.x + i
        cy = j if arc_center_absolute else start.y + j
    elif radius_word is not None:
        dx, dy = end.x - start.x, end.y - start.y
        chord = math.hypot(dx, dy)
        radius = abs(radius_word)
        if chord <= 1e-9 or chord > 2.0 * radius + 1e-6:
            raise EvaluationError("invalid R arc")
        mx, my = (start.x + end.x) / 2.0, (start.y + end.y) / 2.0
        height = math.sqrt(max(0.0, radius * radius - (chord / 2.0) ** 2))
        nx, ny = -dy / chord, dx / chord
        candidates = [(mx + nx * height, my + ny * height), (mx - nx * height, my - ny * height)]
        choices = []
        for candidate_x, candidate_y in candidates:
            a0 = math.atan2(start.y - candidate_y, start.x - candidate_x)
            a1 = math.atan2(end.y - candidate_y, end.x - candidate_x)
            sweep = directed_sweep(a0, a1, clockwise)
            choices.append((candidate_x, candidate_y, sweep))
        want_major = radius_word < 0.0
        selected = min(choices, key=lambda row: abs((abs(row[2]) > math.pi) - want_major))
        cx, cy = selected[0], selected[1]
    else:
        raise EvaluationError("G2/G3 requires I/J or R")

    radius = math.hypot(start.x - cx, start.y - cy)
    if radius <= 1e-9 or abs(math.hypot(end.x - cx, end.y - cy) - radius) > 0.5:
        raise EvaluationError("inconsistent arc radius")
    start_angle = math.atan2(start.y - cy, start.x - cx)
    end_angle = math.atan2(end.y - cy, end.x - cx)
    sweep = directed_sweep(start_angle, end_angle, clockwise)
    count = max(8, int(math.ceil(abs(sweep) * radius / 0.5)))
    return tuple(
        Point(
            cx + radius * math.cos(start_angle + sweep * index / count),
            cy + radius * math.sin(start_angle + sweep * index / count),
            start.z + (end.z - start.z) * index / count,
        )
        for index in range(count + 1)
    )


def parse_program(source: str) -> Program:
    units: str | None = None
    absolute: bool | None = None
    arc_center_absolute = False
    motion: int | None = None
    current = Point(0.0, 0.0, 0.0)
    pending_tool = active_tool = None
    spindle_on = False
    spindle = feed = None
    wcs = None
    terminated = False
    executable_blocks = 0
    segments: list[Segment] = []
    tools: list[int] = []

    for physical_line, line in enumerate(strip_comments(source), 1):
        if not line or line == "%":
            continue
        if terminated:
            raise EvaluationError("executable content after M30")
        if any(char in line for char in "#[]=/{}`"):
            raise EvaluationError("macros, expressions, and block skips are unsupported")
        if re.fullmatch(r"O\d+", line):
            executable_blocks += 1
            continue
        words = WORD_RE.findall(line)
        residue = re.sub(r"\s+", "", WORD_RE.sub("", line))
        if not words or residue:
            raise EvaluationError(f"unknown executable content: {line!r}")
        executable_blocks += 1
        grouped: dict[str, list[float]] = {}
        for letter, raw_value in words:
            if letter not in ALLOWED_LETTERS:
                raise EvaluationError(f"unsupported address word {letter}")
            grouped.setdefault(letter, []).append(float(raw_value))
        if any(letter in grouped for letter in ("A", "B", "C")):
            raise EvaluationError("rotary-axis output is forbidden")
        for letter in "XYZIJKRFSTHDPL":
            if len(grouped.get(letter, [])) > 1:
                raise EvaluationError(f"ambiguous repeated {letter} word")

        reference_return = machine_coordinates = False
        for raw_g in grouped.get("G", []):
            if close(raw_g, 90.1, 1e-7):
                arc_center_absolute = True
                continue
            if close(raw_g, 91.1, 1e-7):
                arc_center_absolute = False
                continue
            rounded = int(round(raw_g))
            if not close(raw_g, rounded, 1e-7):
                raise EvaluationError(f"unsupported G code G{raw_g:g}")
            if rounded == 20:
                units = "inch"
            elif rounded == 21:
                units = "mm"
            elif rounded == 90:
                absolute = True
            elif rounded == 91:
                absolute = False
            elif rounded in (0, 1, 2, 3):
                motion = rounded
            elif rounded == 28:
                reference_return = True
            elif rounded == 53:
                machine_coordinates = True
            elif rounded in (54, 55, 56, 57, 58, 59):
                wcs = rounded
            elif rounded in (4, 17, 40, 41, 42, 43, 49, 80, 94, 98, 99):
                pass
            else:
                raise EvaluationError(f"unsupported G code G{rounded}")

        mcodes: list[int] = []
        for raw_m in grouped.get("M", []):
            if not close(raw_m, round(raw_m), 1e-7):
                raise EvaluationError("non-integral M code")
            code = int(round(raw_m))
            if code not in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 19, 30):
                raise EvaluationError(f"unsupported M code M{code}")
            mcodes.append(code)

        if "T" in grouped:
            raw_tool = grouped["T"][0]
            if not close(raw_tool, round(raw_tool), 1e-7) or raw_tool <= 0:
                raise EvaluationError("invalid tool number")
            pending_tool = int(round(raw_tool))
        if 6 in mcodes:
            if pending_tool is None:
                raise EvaluationError("M6 without pending tool")
            active_tool = pending_tool
            if active_tool not in tools:
                tools.append(active_tool)
        if "S" in grouped:
            spindle = grouped["S"][0]
            if spindle <= 0:
                raise EvaluationError("invalid spindle speed")
        if 3 in mcodes or 4 in mcodes:
            spindle_on = True
        if 5 in mcodes:
            spindle_on = False
        if 30 in mcodes:
            if mcodes != [30] or any(letter not in {"N", "M"} for letter in grouped):
                raise EvaluationError("M30 must be terminal-only")
            terminated = True
            continue

        coordinate_letters = {"X", "Y", "Z"} & grouped.keys()
        if units is None and (coordinate_letters or "F" in grouped):
            raise EvaluationError("coordinate/feed before unit selection")
        factor = 25.4 if units == "inch" else 1.0
        if "F" in grouped:
            feed = grouped["F"][0] * factor
            if feed <= 0:
                raise EvaluationError("invalid feed")
        if reference_return or machine_coordinates:
            continue
        if coordinate_letters and absolute is None:
            raise EvaluationError("coordinate before distance mode")

        def coordinate(letter: str, old: float) -> float:
            if letter not in grouped:
                return old
            raw = grouped[letter][0] * factor
            return raw if absolute else old + raw

        end = Point(coordinate("X", current.x), coordinate("Y", current.y), coordinate("Z", current.z))
        if coordinate_letters and motion is not None and math.dist((current.x, current.y, current.z), (end.x, end.y, end.z)) > 1e-9:
            if motion in (2, 3):
                samples = arc_samples(
                    current,
                    end,
                    motion == 2,
                    grouped.get("I", [None])[0] * factor if "I" in grouped else None,
                    grouped.get("J", [None])[0] * factor if "J" in grouped else None,
                    grouped.get("R", [None])[0] * factor if "R" in grouped else None,
                    arc_center_absolute,
                )
            else:
                samples = dense_line(current, end)
            segments.append(Segment(current, end, samples, motion, active_tool, spindle_on, spindle, feed, wcs, physical_line))
        current = end

    return Program(segments, tools, terminated, units is not None, absolute is not None, executable_blocks)


def cutting_segments(program: Program) -> list[Segment]:
    rows = []
    for segment in program.segments:
        if segment.motion not in (1, 2, 3):
            continue
        if not segment.spindle_on or segment.tool is None or segment.feed is None or segment.feed <= 0 or segment.wcs is None:
            raise EvaluationError(f"incomplete cutting state at line {segment.line_number}")
        rows.append(segment)
    if not rows:
        raise EvaluationError("no cutting motion")
    return rows


def validate_slots(program: Program) -> None:
    if not program.terminated or not program.units_selected or not program.distance_mode_selected:
        raise EvaluationError("program is incomplete")
    if program.executable_blocks < 20 or not program.tools:
        raise EvaluationError("program is too small to establish four slots")
    cuts = cutting_segments(program)
    cutting_wcs = {segment.wcs for segment in cuts}
    if len(cutting_wcs) != 1:
        raise EvaluationError("single setup requires one cutting WCS")

    floor_z = min(point.z for segment in cuts for point in segment.samples)
    floor_tolerance = 0.25
    horizontal = [
        segment
        for segment in cuts
        if abs(segment.start.z - floor_z) <= floor_tolerance
        and abs(segment.end.z - floor_z) <= floor_tolerance
        and xy_distance(segment.start, segment.end) >= 75.0
    ]
    if len(horizontal) < 4:
        raise EvaluationError("too few full-depth slot spans")
    longest = max(horizontal, key=lambda segment: xy_distance(segment.start, segment.end))
    dx, dy = longest.end.x - longest.start.x, longest.end.y - longest.start.y
    norm = math.hypot(dx, dy)
    ux, uy = dx / norm, dy / norm
    vx, vy = -uy, ux

    parallel = []
    for segment in horizontal:
        sx, sy = segment.end.x - segment.start.x, segment.end.y - segment.start.y
        length = math.hypot(sx, sy)
        if abs((sx * ux + sy * uy) / length) < math.cos(math.radians(3.0)):
            raise EvaluationError("full-depth tracks are not parallel")
        midpoint_v = ((segment.start.x + segment.end.x) / 2.0) * vx + ((segment.start.y + segment.end.y) / 2.0) * vy
        parallel.append((midpoint_v, segment))

    groups: list[list[tuple[float, Segment]]] = []
    for item in sorted(parallel, key=lambda row: row[0]):
        if not groups or item[0] - groups[-1][-1][0] > 6.0:
            groups.append([item])
        else:
            groups[-1].append(item)
    if len(groups) != 4:
        raise EvaluationError(f"expected exactly four full-depth slot groups, got {len(groups)}")

    centers = []
    spans = []
    along_bounds = []
    for group in groups:
        values = [value for value, _ in group]
        if max(values) - min(values) > 4.5:
            raise EvaluationError("slot track band is too wide")
        centers.append((min(values) + max(values)) / 2.0)
        along = [point.x * ux + point.y * uy for _, segment in group for point in (segment.start, segment.end)]
        span = max(along) - min(along)
        if span < 89.5:
            raise EvaluationError("slot is shorter than the modeled full-length tool-center span")
        spans.append(span)
        along_bounds.append((min(along), max(along)))

    gaps = [right - left for left, right in zip(centers, centers[1:])]
    if any(not close(gap, 14.0, 1.25) for gap in gaps) or not close(centers[-1] - centers[0], 42.0, 2.0):
        raise EvaluationError("four slot centers do not match the modeled 14 mm pitch")

    floor_points = [point for segment in cuts for point in segment.samples if point.z <= floor_z + floor_tolerance]
    for point in floor_points:
        along = point.x * ux + point.y * uy
        across = point.x * vx + point.y * vy
        nearest = min(range(4), key=lambda index: abs(across - centers[index]))
        if abs(across - centers[nearest]) > 4.0:
            raise EvaluationError("destructive full-depth cutting exists outside the four slots")
        low, high = along_bounds[nearest]
        if along < low - 5.0 or along > high + 5.0:
            raise EvaluationError("destructive full-depth cutting extends beyond the slot ends")

    for center in centers:
        plunges = [
            segment
            for segment in cuts
            if xy_distance(segment.start, segment.end) <= 0.2
            and min(segment.start.z, segment.end.z) <= floor_z + floor_tolerance
            and abs(segment.end.x * vx + segment.end.y * vy - center) <= 4.0
            and abs(segment.end.z - segment.start.z) >= 3.2
        ]
        retracts = [
            segment
            for segment in program.segments
            if segment.motion == 0
            and xy_distance(segment.start, segment.end) <= 0.2
            and min(segment.start.z, segment.end.z) <= floor_z + floor_tolerance
            and abs(segment.start.x * vx + segment.start.y * vy - center) <= 4.0
            and abs(segment.end.z - segment.start.z) >= 3.2
        ]
        if not plunges or not retracts:
            raise EvaluationError("each slot needs full-depth plunge and retract evidence")


def evaluate_text(source: str) -> bool:
    try:
        validate_slots(parse_program(source))
        return True
    except (EvaluationError, ValueError, OverflowError):
        return False


def main() -> bool:
    path = TARGET / NC_NAME
    if not path.is_file() or path.stat().st_size < 200 or path.stat().st_size > 5_000_000:
        return False
    return evaluate_text(path.read_text(encoding="utf-8", errors="strict"))


if __name__ == "__main__":
    try:
        result = main()
    except Exception:
        result = False
    print("True" if result else "False")
    raise SystemExit(0)
