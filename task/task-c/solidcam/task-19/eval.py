from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from pathlib import Path


TARGET = Path(os.environ.get("EVAL_TARGET_DIR", r"C:\Users\User\Desktop"))
NC_NAME = "task-19.nc"
TOOL_SPEC = {
    1: {"diameter": 4.0, "spindle": 8500.0, "feed": 420.0},
    2: {"diameter": 4.0, "spindle": 6500.0, "feed": 360.0},
}
WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))")
ALLOWED_LETTERS = set("NGMXYZIJKRFSTHDP")


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
    points: tuple[Point, ...]
    motion: int
    tool: int | None
    spindle: float | None
    spindle_on: bool
    feed: float | None
    wcs: int | None
    length_comp: bool
    h_offset: int | None
    cutter_comp: int | None


@dataclass
class Program:
    segments: list[Segment]
    tool_changes: list[int]
    terminated: bool
    executable_blocks: int
    units_selected: bool
    distance_mode_selected: bool


@dataclass(frozen=True)
class Frame:
    ux: float
    uy: float
    vx: float
    vy: float
    cx: float
    cy: float
    umin: float
    umax: float
    vmin: float
    vmax: float
    surface_z: float
    profile_bottom_z: float

    def map(self, point: Point) -> tuple[float, float, float]:
        dx, dy = point.x - self.cx, point.y - self.cy
        return dx * self.ux + dy * self.uy, dx * self.vx + dy * self.vy, point.z


def close(actual: float, expected: float, tolerance: float) -> bool:
    return abs(actual - expected) <= tolerance


def distance(a: Point, b: Point) -> float:
    return math.dist((a.x, a.y, a.z), (b.x, b.y, b.z))


def dense_points(a: Point, b: Point, spacing: float = 0.5) -> tuple[Point, ...]:
    count = max(1, int(math.ceil(distance(a, b) / spacing)))
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


def parse_program(source: str) -> Program:
    units: str | None = None
    absolute: bool | None = None
    motion: int | None = None
    current = Point(0.0, 0.0, 0.0)
    pending_tool = active_tool = None
    spindle = feed = None
    spindle_on = False
    wcs = None
    length_comp = False
    h_offset = None
    cutter_comp = None
    terminated = False
    executable = 0
    segments: list[Segment] = []
    tool_changes: list[int] = []

    for line in strip_comments(source):
        if not line or line == "%":
            continue
        if terminated:
            raise EvaluationError("executable content after M30")
        if any(char in line for char in "#[]="):
            raise EvaluationError("expressions and macros are unsupported")
        if re.fullmatch(r"/?\s*O\d+", line):
            executable += 1
            continue
        words = WORD_RE.findall(line)
        residue = re.sub(r"[\s/]+", "", WORD_RE.sub("", line))
        if not words or residue:
            raise EvaluationError(f"unknown executable content: {line!r}")
        executable += 1
        grouped: dict[str, list[float]] = {}
        for letter, raw_value in words:
            if letter not in ALLOWED_LETTERS:
                raise EvaluationError(f"unsupported address word {letter}")
            grouped.setdefault(letter, []).append(float(raw_value))
        if any(letter in grouped for letter in ("A", "B", "C")):
            raise EvaluationError("rotary-axis output is forbidden")
        for letter in ("X", "Y", "Z", "I", "J", "K", "R", "F", "S", "T", "H", "D", "P"):
            if len(grouped.get(letter, [])) > 1:
                raise EvaluationError(f"ambiguous repeated {letter} word")

        reference_return = False
        for raw_g in grouped.get("G", []):
            rounded = int(round(raw_g))
            if not close(raw_g, rounded, 1e-7):
                raise EvaluationError(f"unsupported non-integral G code G{raw_g:g}")
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
            elif rounded in (54, 55, 56, 57, 58, 59):
                wcs = rounded
            elif rounded == 43:
                length_comp = True
            elif rounded == 49:
                length_comp = False
                h_offset = None
            elif rounded == 40:
                cutter_comp = None
            elif rounded in (41, 42):
                cutter_comp = rounded
            elif rounded in (17, 80, 94):
                pass
            else:
                raise EvaluationError(f"unsupported G code G{rounded}")

        mcodes: list[int] = []
        for raw_m in grouped.get("M", []):
            if not close(raw_m, round(raw_m), 1e-7):
                raise EvaluationError("non-integral M code")
            mcode = int(round(raw_m))
            if mcode not in (0, 1, 2, 3, 4, 5, 6, 8, 9, 30):
                raise EvaluationError(f"unsupported M code M{mcode}")
            mcodes.append(mcode)

        if "T" in grouped:
            raw_tool = grouped["T"][0]
            if not close(raw_tool, round(raw_tool), 1e-7):
                raise EvaluationError("non-integral tool number")
            pending_tool = int(round(raw_tool))
        if "S" in grouped:
            spindle = grouped["S"][0]
        if "H" in grouped:
            raw_h = grouped["H"][0]
            if not close(raw_h, round(raw_h), 1e-7):
                raise EvaluationError("non-integral H offset")
            h_offset = int(round(raw_h))
        if 6 in mcodes:
            if pending_tool is None:
                raise EvaluationError("M6 without pending tool")
            active_tool = pending_tool
            tool_changes.append(active_tool)
        if 3 in mcodes or 4 in mcodes:
            spindle_on = True
        if 5 in mcodes:
            spindle_on = False
        if 30 in mcodes:
            if mcodes != [30] or any(letter not in {"N", "M"} for letter in grouped):
                raise EvaluationError("M30 must be a terminal-only block")
            terminated = True
            continue

        coordinate_letters = {"X", "Y", "Z"} & grouped.keys()
        if units is None and (coordinate_letters or "F" in grouped):
            raise EvaluationError("coordinate/feed before unit selection")
        factor = 25.4 if units == "inch" else 1.0
        if "F" in grouped:
            feed = grouped["F"][0] * factor
        if reference_return:
            continue
        if absolute is None and coordinate_letters:
            raise EvaluationError("coordinate before distance mode")

        def coordinate(letter: str, old: float) -> float:
            if letter not in grouped:
                return old
            value = grouped[letter][0] * factor
            return value if absolute else old + value

        new_point = Point(
            coordinate("X", current.x),
            coordinate("Y", current.y),
            coordinate("Z", current.z),
        )
        if coordinate_letters and motion is not None and distance(current, new_point) > 1e-9:
            segments.append(
                Segment(
                    current,
                    new_point,
                    dense_points(current, new_point),
                    motion,
                    active_tool,
                    spindle,
                    spindle_on,
                    feed,
                    wcs,
                    length_comp,
                    h_offset,
                    cutter_comp,
                )
            )
        current = new_point

    return Program(
        segments,
        tool_changes,
        terminated,
        executable,
        units is not None,
        absolute is not None,
    )


def cutting_segments(program: Program, tool: int) -> list[Segment]:
    expected = TOOL_SPEC[tool]
    rows = []
    for segment in program.segments:
        if segment.tool != tool or segment.motion not in (1, 2, 3) or distance(segment.start, segment.end) <= 0.01:
            continue
        if (
            not segment.spindle_on
            or segment.spindle is None
            or not close(segment.spindle, expected["spindle"], 1.0)
            or segment.feed is None
            or not close(segment.feed, expected["feed"], 0.8)
            or segment.wcs is None
            or not segment.length_comp
            or segment.h_offset is None
            or segment.h_offset <= 0
        ):
            raise EvaluationError(f"tool {tool} cutting state is incomplete or incorrect")
        rows.append(segment)
    if not rows:
        raise EvaluationError(f"tool {tool} has no valid cutting motion")
    return rows


def projected(point: Point, ux: float, uy: float, vx: float, vy: float) -> tuple[float, float]:
    return point.x * ux + point.y * uy, point.x * vx + point.y * vy


def profile_frame(tool2: list[Segment]) -> Frame:
    bottom = min(min(segment.start.z, segment.end.z) for segment in tool2)
    full_depth = [
        segment
        for segment in tool2
        if abs(segment.start.z - bottom) <= 0.4
        and abs(segment.end.z - bottom) <= 0.4
        and math.hypot(segment.end.x - segment.start.x, segment.end.y - segment.start.y) >= 20.0
    ]
    if len(full_depth) < 4:
        raise EvaluationError("outside profile lacks four full-depth boundary spans")
    longest = max(
        full_depth,
        key=lambda segment: math.hypot(segment.end.x - segment.start.x, segment.end.y - segment.start.y),
    )
    dx, dy = longest.end.x - longest.start.x, longest.end.y - longest.start.y
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    vx, vy = -uy, ux
    endpoints = [point for segment in full_depth for point in (segment.start, segment.end)]
    raw = [projected(point, ux, uy, vx, vy) for point in endpoints]
    umin, umax = min(x for x, _ in raw), max(x for x, _ in raw)
    vmin, vmax = min(y for _, y in raw), max(y for _, y in raw)
    width, height = umax - umin, vmax - vmin
    center_u, center_v = (umin + umax) / 2.0, (vmin + vmax) / 2.0
    cx = center_u * ux + center_v * vx
    cy = center_u * uy + center_v * vy
    umin -= center_u
    umax -= center_u
    vmin -= center_v
    vmax -= center_v
    centerline_profile = close(width, 84.0, 1.2) and close(height, 50.0, 1.2)
    compensated_nominal = close(width, 80.0, 1.2) and close(height, 46.0, 1.2)
    if not (centerline_profile or compensated_nominal):
        raise EvaluationError(f"outside profile dimensions are incorrect: {width:g} x {height:g}")
    if compensated_nominal and not all(segment.cutter_comp in (41, 42) for segment in full_depth):
        raise EvaluationError("nominal outside contour requires active G41/G42 compensation")

    samples = []
    for segment in full_depth:
        samples.extend(
            (
                (point.x - cx) * ux + (point.y - cy) * uy,
                (point.x - cx) * vx + (point.y - cy) * vy,
            )
            for point in segment.points
        )
    side_tolerance = 0.7
    u_low = [v for u, v in samples if abs(u - umin) <= side_tolerance]
    u_high = [v for u, v in samples if abs(u - umax) <= side_tolerance]
    v_low = [u for u, v in samples if abs(v - vmin) <= side_tolerance]
    v_high = [u for u, v in samples if abs(v - vmax) <= side_tolerance]
    if (
        not u_low
        or not u_high
        or not v_low
        or not v_high
        or min(u_low) > vmin + 1.2
        or max(u_low) < vmax - 1.2
        or min(u_high) > vmin + 1.2
        or max(u_high) < vmax - 1.2
        or min(v_low) > umin + 1.2
        or max(v_low) < umax - 1.2
        or min(v_high) > umin + 1.2
        or max(v_high) < umax - 1.2
    ):
        raise EvaluationError("outside profile is open or misses a boundary side")
    return Frame(ux, uy, vx, vy, cx, cy, umin, umax, vmin, vmax, bottom + 10.0, bottom)


def validate_channels(tool1: list[Segment], frame: Frame) -> None:
    bottom = frame.surface_z - 3.0
    if any(min(segment.start.z, segment.end.z) < bottom - 0.45 for segment in tool1):
        raise EvaluationError("channel tool cuts below the 3 mm channel floor")
    bottom_points = [
        frame.map(point)
        for segment in tool1
        for point in segment.points
        if abs(point.z - bottom) <= 0.4
    ]
    if not bottom_points:
        raise EvaluationError("no channel-floor cutting motion")
    for center_v in (-12.0, 0.0, 12.0):
        lane = [(u, v) for u, v, _ in bottom_points if abs(v - center_v) <= 0.8]
        if (
            len(lane) < 80
            or min(u for u, _ in lane) > -25.4
            or max(u for u, _ in lane) < 25.4
            or min(v for _, v in lane) > center_v - 0.35
            or max(v for _, v in lane) < center_v + 0.35
        ):
            raise EvaluationError(f"channel at relative Y={center_v:g} is incomplete")
    for segment in tool1:
        for point in segment.points:
            if point.z >= frame.surface_z - 0.1:
                continue
            u, v, _ = frame.map(point)
            in_channel = abs(u) <= 26.7 and any(abs(v - center) <= 0.8 for center in (-12.0, 0.0, 12.0))
            if not in_channel:
                raise EvaluationError("T1 contains destructive cutting outside the three channels")


def validate_profile_exclusivity(tool2: list[Segment], frame: Frame) -> None:
    for segment in tool2:
        if max(segment.start.z, segment.end.z) > frame.surface_z - 0.5:
            continue
        for point in segment.points:
            u, v, _ = frame.map(point)
            outside_or_boundary = (
                u <= frame.umin + 0.8
                or u >= frame.umax - 0.8
                or v <= frame.vmin + 0.8
                or v >= frame.vmax - 0.8
            )
            if not outside_or_boundary:
                raise EvaluationError("T2 contains destructive cutting inside the finished outside profile")


def validate_program(program: Program) -> None:
    if (
        not program.terminated
        or not program.units_selected
        or not program.distance_mode_selected
        or program.executable_blocks < 30
    ):
        raise EvaluationError("program is incomplete")
    if program.tool_changes != [1, 2]:
        raise EvaluationError("expected exactly one T1 change followed by one T2 change")
    for segment in program.segments:
        if segment.motion in (1, 2, 3) and distance(segment.start, segment.end) > 0.01:
            if segment.tool not in (1, 2):
                raise EvaluationError("cutting move uses an unexpected tool")
    tool1 = cutting_segments(program, 1)
    tool2 = cutting_segments(program, 2)
    frame = profile_frame(tool2)
    validate_channels(tool1, frame)
    validate_profile_exclusivity(tool2, frame)


def evaluate_text(source: str) -> bool:
    try:
        validate_program(parse_program(source))
        return True
    except (EvaluationError, ValueError, OverflowError):
        return False


def main() -> bool:
    path = TARGET / NC_NAME
    if not path.is_file() or path.stat().st_size < 150 or path.stat().st_size > 5_000_000:
        return False
    return evaluate_text(path.read_text(encoding="utf-8", errors="strict"))


if __name__ == "__main__":
    try:
        result = main()
    except Exception:
        result = False
    print("True" if result else "False")
    raise SystemExit(0)


