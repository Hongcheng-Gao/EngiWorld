from __future__ import annotations

import hashlib
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path


TARGET = Path(os.environ.get("EVAL_TARGET_DIR", r"C:\Users\User\Desktop"))
NC_NAME = "task-18.nc"
INPUT_HASHES = {
    "basic_milling_part.step": "9232ff254deb75a5ebd2b8bfb39a30eac63d19ea498e59215140e90a9f8e61a0",
    "tools.csv": "d90267f2c2933687188847eaff937205fb0c2333462d59b4fabb5c2d4b666245",
}
TOOL_CONTRACT = {
    1: {"diameter": 8.0, "spindle": 7800.0, "feed": 480.0},
    2: {"diameter": 5.0, "spindle": 5000.0, "feed": 180.0},
    3: {"diameter": 6.0, "spindle": 8500.0, "feed": 600.0},
}
HOLES = [(-12.0, 0.0), (12.0, 0.0)]
WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))")

MAX_FILE_BYTES = 256_000
MAX_LINES = 5_000
MAX_LINE_CHARS = 1_024
MAX_WORDS = 50_000
MAX_SEGMENTS = 20_000
MAX_SAMPLES = 300_000
MAX_COORDINATE = 10_000.0


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
    spindle_direction: int | None
    feed: float | None
    wcs: str | None
    length_comp: bool
    h_offset: int | None
    comp: int
    d_offset: int | None
    machine_coordinates: bool
    line_number: int


@dataclass
class Program:
    segments: list[Segment]
    tool_changes: list[int]
    terminated: bool
    explicit_units: bool
    explicit_distance_mode: bool
    executable_lines: int


def close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def distance(a: Point, b: Point) -> float:
    return math.dist((a.x, a.y, a.z), (b.x, b.y, b.z))


def dense_line(start: Point, end: Point, spacing: float = 0.5) -> list[Point]:
    length = distance(start, end)
    if length > 2_000.0:
        raise EvaluationError("unreasonable motion length")
    count = max(1, int(math.ceil(length / spacing)))
    return [
        Point(
            start.x + (end.x - start.x) * i / count,
            start.y + (end.y - start.y) * i / count,
            start.z + (end.z - start.z) * i / count,
        )
        for i in range(count + 1)
    ]


def strip_comments(src: str) -> list[tuple[int, str]]:
    raw_lines = src.upper().splitlines()
    if len(raw_lines) > MAX_LINES:
        raise EvaluationError("too many lines")
    out: list[tuple[int, str]] = []
    depth = 0
    for line_number, raw in enumerate(raw_lines, 1):
        if len(raw) > MAX_LINE_CHARS:
            raise EvaluationError("line too long")
        clean: list[str] = []
        for char in raw:
            if char == ";" and depth == 0:
                break
            if char == "(":
                depth += 1
                if depth > 8:
                    raise EvaluationError("comment nesting too deep")
            elif char == ")":
                if depth == 0:
                    raise EvaluationError("unmatched comment close")
                depth -= 1
            elif depth == 0:
                clean.append(char)
        out.append((line_number, "".join(clean).strip()))
    if depth:
        raise EvaluationError("unterminated comment")
    return out


def directed_sweep(start_angle: float, end_angle: float, clockwise: bool) -> float:
    return (start_angle - end_angle) % (2 * math.pi) if clockwise else (end_angle - start_angle) % (2 * math.pi)


def arc_samples(start: Point, end: Point, cx: float, cy: float, clockwise: bool) -> list[Point]:
    radius = math.hypot(start.x - cx, start.y - cy)
    if radius <= 1e-6 or not close(math.hypot(end.x - cx, end.y - cy), radius, 0.25):
        raise EvaluationError("invalid arc geometry")
    a0 = math.atan2(start.y - cy, start.x - cx)
    a1 = math.atan2(end.y - cy, end.x - cx)
    sweep = directed_sweep(a0, a1, clockwise)
    if sweep <= 1e-9:
        sweep = 2 * math.pi
    arc_length = radius * sweep
    if arc_length > 4_000.0:
        raise EvaluationError("unreasonable arc length")
    direction = -1.0 if clockwise else 1.0
    count = max(12, int(math.ceil(arc_length / 0.5)))
    return [
        Point(
            cx + radius * math.cos(a0 + direction * sweep * k / count),
            cy + radius * math.sin(a0 + direction * sweep * k / count),
            start.z + (end.z - start.z) * k / count,
        )
        for k in range(count + 1)
    ]


def arc_points_ij(start: Point, end: Point, i: float, j: float, clockwise: bool) -> list[Point]:
    return arc_samples(start, end, start.x + i, start.y + j, clockwise)


def arc_points_r(start: Point, end: Point, signed_radius: float, clockwise: bool) -> list[Point]:
    chord_x = end.x - start.x
    chord_y = end.y - start.y
    chord = math.hypot(chord_x, chord_y)
    radius = abs(signed_radius)
    if chord <= 1e-6 or radius < chord / 2.0 - 1e-6:
        raise EvaluationError("invalid R arc")
    mid_x = (start.x + end.x) / 2.0
    mid_y = (start.y + end.y) / 2.0
    height = math.sqrt(max(0.0, radius * radius - (chord / 2.0) ** 2))
    perp_x, perp_y = -chord_y / chord, chord_x / chord
    choices: list[tuple[float, float, float]] = []
    for sign in (-1.0, 1.0):
        cx = mid_x + sign * height * perp_x
        cy = mid_y + sign * height * perp_y
        a0 = math.atan2(start.y - cy, start.x - cx)
        a1 = math.atan2(end.y - cy, end.x - cx)
        choices.append((directed_sweep(a0, a1, clockwise), cx, cy))
    if signed_radius >= 0:
        eligible = [item for item in choices if item[0] <= math.pi + 1e-6]
        chosen = min(eligible or choices, key=lambda item: item[0])
    else:
        eligible = [item for item in choices if item[0] >= math.pi - 1e-6]
        chosen = max(eligible or choices, key=lambda item: item[0])
    return arc_samples(start, end, chosen[1], chosen[2], clockwise)


def parse_program(src: str) -> Program:
    units: str | None = None
    absolute: bool | None = None
    motion: int | None = None
    plane = 17
    current = Point(0.0, 0.0, 0.0)
    pending_tool: int | None = None
    tool: int | None = None
    spindle: float | None = None
    spindle_direction: int | None = None
    feed: float | None = None
    wcs: str | None = None
    length_comp = False
    h_offset: int | None = None
    comp = 40
    d_offset: int | None = None
    cycle: int | None = None
    cycle_z: float | None = None
    cycle_r: float | None = None
    cycle_q: float | None = None
    cycle_initial_z: float | None = None
    retract_mode = 98
    suppress_next_work_move = False
    terminated = False
    executable_lines = 0
    word_count = 0
    sample_count = 0
    segments: list[Segment] = []
    tool_changes: list[int] = []

    def add_segment(segment: Segment) -> None:
        nonlocal sample_count
        if len(segments) >= MAX_SEGMENTS:
            raise EvaluationError("too many motion segments")
        sample_count += len(segment.samples)
        if sample_count > MAX_SAMPLES:
            raise EvaluationError("too many sampled points")
        segments.append(segment)

    for line_number, line in strip_comments(src):
        if not line or line == "%":
            continue
        if any(ch in line for ch in "#[]={}@$\\"):
            raise EvaluationError("macros, expressions, and variable syntax are unsupported")
        if re.fullmatch(r"O\d+", line):
            if terminated:
                raise EvaluationError("executable content after M30")
            executable_lines += 1
            continue
        found = WORD_RE.findall(line)
        if not found:
            raise EvaluationError(f"unparsed text on line {line_number}")
        word_count += len(found)
        if word_count > MAX_WORDS:
            raise EvaluationError("too many words")
        residue = WORD_RE.sub("", line)
        residue = re.sub(r"[\s/%]+", "", residue)
        if residue:
            raise EvaluationError(f"unknown executable text on line {line_number}")
        if terminated:
            raise EvaluationError("executable content after M30")
        executable_lines += 1

        grouped: dict[str, list[float]] = {}
        for letter, token in found:
            value = float(token)
            if not math.isfinite(value) or abs(value) > 1e9:
                raise EvaluationError("non-finite or unreasonable numeric word")
            grouped.setdefault(letter, []).append(value)
        if any(letter in grouped for letter in ("A", "B", "C")):
            raise EvaluationError("rotary axes are forbidden")
        allowed_letters = set("NGMXYZIJRQP FSTHD".replace(" ", ""))
        if set(grouped) - allowed_letters:
            raise EvaluationError("unsupported address")
        for letter, values in grouped.items():
            if letter not in ("G", "M") and len(values) > 1:
                raise EvaluationError(f"duplicate {letter} address")
        for letter in ("N", "T", "H", "D", "P"):
            if letter in grouped and not close(grouped[letter][0], round(grouped[letter][0]), 1e-9):
                raise EvaluationError(f"non-integer {letter} register")

        gcodes = grouped.get("G", [])
        mcodes: list[int] = []
        for value in grouped.get("M", []):
            if not close(value, round(value), 1e-9):
                raise EvaluationError("non-integer M code")
            code = int(round(value))
            if code not in {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 30}:
                raise EvaluationError(f"unsupported M code M{code}")
            mcodes.append(code)

        modal_groups = {
            "motion": [], "units": [], "distance": [], "wcs": [],
            "comp": [], "length": [], "retract": [], "plane": [],
        }
        machine_coordinates = False
        reference_return = False
        new_cycle: int | None = None
        cancel_cycle = False
        for g in gcodes:
            rounded = int(round(g))
            if close(g, 20.0, 1e-6) or close(g, 21.0, 1e-6):
                modal_groups["units"].append(g)
                units = "inch" if close(g, 20.0, 1e-6) else "mm"
            elif close(g, 90.0, 1e-6) or close(g, 91.0, 1e-6):
                modal_groups["distance"].append(g)
                absolute = close(g, 90.0, 1e-6)
            elif rounded in (0, 1, 2, 3) and close(g, rounded, 1e-6):
                modal_groups["motion"].append(g)
                motion = rounded
            elif rounded in (54, 55, 56, 57, 58, 59) and close(g, rounded, 1e-6):
                modal_groups["wcs"].append(g)
                wcs = f"G{rounded}"
            elif close(g, 54.1, 1e-6):
                modal_groups["wcs"].append(g)
                p_value = grouped.get("P", [0.0])[0]
                p = int(round(p_value))
                if p <= 0:
                    raise EvaluationError("invalid G54.1 offset")
                wcs = f"G54.1P{p}"
            elif close(g, 43.0, 1e-6):
                modal_groups["length"].append(g)
                length_comp = True
            elif close(g, 49.0, 1e-6):
                modal_groups["length"].append(g)
                length_comp = False
                h_offset = None
            elif rounded in (40, 41, 42) and close(g, rounded, 1e-6):
                modal_groups["comp"].append(g)
                comp = rounded
                if rounded == 40:
                    d_offset = None
            elif rounded in (81, 82, 83) and close(g, rounded, 1e-6):
                modal_groups["motion"].append(g)
                new_cycle = rounded
            elif rounded == 80 and close(g, 80.0, 1e-6):
                modal_groups["motion"].append(g)
                cancel_cycle = True
            elif close(g, 98.0, 1e-6) or close(g, 99.0, 1e-6):
                modal_groups["retract"].append(g)
                retract_mode = int(round(g))
            elif rounded in (17, 18, 19) and close(g, rounded, 1e-6):
                modal_groups["plane"].append(g)
                plane = rounded
            elif close(g, 28.0, 1e-6):
                reference_return = True
            elif close(g, 53.0, 1e-6):
                machine_coordinates = True
            elif close(g, 94.0, 1e-6):
                pass
            else:
                raise EvaluationError(f"unsupported G code G{g:g}")
        if any(len(values) > 1 for values in modal_groups.values()):
            raise EvaluationError("conflicting modal G codes on one line")

        factor = 25.4 if units == "inch" else 1.0
        for letter in ("X", "Y", "Z", "I", "J", "R", "Q"):
            if letter in grouped and abs(grouped[letter][0] * factor) > MAX_COORDINATE:
                raise EvaluationError("coordinate exceeds evaluator bounds")
        if "T" in grouped:
            pending_tool = int(round(grouped["T"][0]))
            if pending_tool <= 0 or pending_tool > 999:
                raise EvaluationError("invalid tool number")
        if "S" in grouped:
            spindle = grouped["S"][0]
            if spindle <= 0 or spindle > 100_000:
                raise EvaluationError("invalid spindle speed")
        if "F" in grouped:
            feed = grouped["F"][0] * factor
            if feed <= 0 or feed > 100_000:
                raise EvaluationError("invalid feed")
        if "H" in grouped:
            h_offset = int(round(grouped["H"][0]))
            if h_offset <= 0:
                raise EvaluationError("invalid H offset")
        if "D" in grouped:
            d_offset = int(round(grouped["D"][0]))
            if d_offset <= 0:
                raise EvaluationError("invalid D offset")
        if 6 in mcodes:
            if pending_tool is None:
                raise EvaluationError("M6 without tool")
            tool = pending_tool
            tool_changes.append(tool)
            spindle_direction = None
            length_comp = False
            h_offset = None
            comp = 40
            d_offset = None
        if 3 in mcodes or 4 in mcodes:
            if 3 in mcodes and 4 in mcodes:
                raise EvaluationError("conflicting spindle direction")
            spindle_direction = 3 if 3 in mcodes else 4
        if 5 in mcodes:
            spindle_direction = None
        if 30 in mcodes:
            terminated = True

        has_coord = any(key in grouped for key in ("X", "Y", "Z"))
        has_arc_data = any(key in grouped for key in ("I", "J", "R"))
        if (has_coord or has_arc_data or "F" in grouped) and units is None:
            raise EvaluationError("motion or feed before explicit G20/G21")
        if has_coord and absolute is None:
            raise EvaluationError("motion before explicit G90/G91")
        if reference_return:
            if has_arc_data or any(abs(grouped[key][0]) > 1e-9 for key in ("X", "Y", "Z") if key in grouped):
                raise EvaluationError("only zero-intermediate G28 is accepted")
            suppress_next_work_move = True
            continue
        if machine_coordinates:
            if motion != 0 or any(key in grouped for key in ("X", "Y", "I", "J", "R")) or "Z" not in grouped:
                raise EvaluationError("only rapid Z-only G53 retracts are accepted")
            continue

        def coord(axis: str, old: float) -> float:
            if axis not in grouped:
                return old
            value = grouped[axis][0] * factor
            result = value if absolute else old + value
            if abs(result) > MAX_COORDINATE:
                raise EvaluationError("resolved coordinate exceeds bounds")
            return result

        if new_cycle is not None:
            cycle = new_cycle
            cycle_initial_z = current.z
            cycle_q = None
        if cancel_cycle:
            cycle = None
            cycle_z = None
            cycle_r = None
            cycle_q = None
            cycle_initial_z = None

        new = Point(coord("X", current.x), coord("Y", current.y), coord("Z", current.z))
        if cycle is not None and has_coord:
            if plane != 17:
                raise EvaluationError("drilling cycles require G17")
            if "Z" in grouped:
                cycle_z = new.z
            if "R" in grouped:
                raw_r = grouped["R"][0] * factor
                cycle_r = raw_r if absolute else current.z + raw_r
            if "Q" in grouped:
                cycle_q = grouped["Q"][0] * factor
            if cycle_z is None or cycle_r is None or cycle_initial_z is None:
                raise EvaluationError("incomplete drilling cycle")
            if cycle == 83 and (cycle_q is None or cycle_q <= 0):
                raise EvaluationError("G83 requires positive Q")
            hole_at_clearance = Point(new.x, new.y, current.z)
            if distance(current, hole_at_clearance) > 1e-9:
                add_segment(Segment(current, hole_at_clearance, dense_line(current, hole_at_clearance), 0, tool, spindle, spindle_direction, feed, wcs, length_comp, h_offset, comp, d_offset, False, line_number))
            top = Point(new.x, new.y, cycle_r)
            if distance(hole_at_clearance, top) > 1e-9:
                add_segment(Segment(hole_at_clearance, top, dense_line(hole_at_clearance, top), 0, tool, spindle, spindle_direction, feed, wcs, length_comp, h_offset, comp, d_offset, False, line_number))
            bottom = Point(new.x, new.y, cycle_z)
            add_segment(Segment(top, bottom, dense_line(top, bottom), 1, tool, spindle, spindle_direction, feed, wcs, length_comp, h_offset, comp, d_offset, False, line_number))
            retract_z = cycle_initial_z if retract_mode == 98 else cycle_r
            retract = Point(new.x, new.y, retract_z)
            add_segment(Segment(bottom, retract, dense_line(bottom, retract), 0, tool, spindle, spindle_direction, feed, wcs, length_comp, h_offset, comp, d_offset, False, line_number))
            current = retract
            continue
        if has_arc_data and motion not in (2, 3):
            raise EvaluationError("arc-center data without arc motion")
        movement = has_coord or (motion in (2, 3) and has_arc_data)
        if movement:
            if motion is None:
                raise EvaluationError("coordinates without a modal motion")
            if motion in (2, 3):
                if plane != 17:
                    raise EvaluationError("only G17 arcs are supported")
                has_ij = "I" in grouped or "J" in grouped
                has_r = "R" in grouped
                if has_ij == has_r:
                    raise EvaluationError("arc requires exactly one of I/J or R")
                if has_ij:
                    samples = arc_points_ij(current, new, grouped.get("I", [0.0])[0] * factor, grouped.get("J", [0.0])[0] * factor, motion == 2)
                else:
                    samples = arc_points_r(current, new, grouped["R"][0] * factor, motion == 2)
            else:
                samples = dense_line(current, new)
            if suppress_next_work_move:
                current = new
                suppress_next_work_move = False
                continue
            add_segment(Segment(current, new, samples, motion, tool, spindle, spindle_direction, feed, wcs, length_comp, h_offset, comp, d_offset, False, line_number))
            current = new

    return Program(segments, tool_changes, terminated, units is not None, absolute is not None, executable_lines)


def cutting_segments(program: Program, tool: int) -> list[Segment]:
    return [s for s in program.segments if s.tool == tool and s.motion in (1, 2, 3) and distance(s.start, s.end) > 1e-6]


def material_segments(program: Program, tool: int) -> list[Segment]:
    return [s for s in cutting_segments(program, tool) if min(s.start.z, s.end.z) < 0.1]


def validate_common(program: Program) -> None:
    if not program.terminated or not program.explicit_units or not program.explicit_distance_mode or program.executable_lines < 25:
        raise EvaluationError("incomplete executable program")
    if program.tool_changes not in ([1, 2, 3], [2, 1, 3]):
        raise EvaluationError("use T1 and T2 once each, followed by T3")
    if any(s.tool not in TOOL_CONTRACT for s in program.segments if s.tool is not None):
        raise EvaluationError("unexpected tool")
    for tool, contract in TOOL_CONTRACT.items():
        segs = material_segments(program, tool)
        if not segs:
            raise EvaluationError(f"T{tool} has no material-cutting motion")
        for segment in segs:
            if segment.spindle_direction != 3:
                raise EvaluationError(f"T{tool} must cut with M3")
            if segment.spindle is None or not close(segment.spindle, contract["spindle"], 1.0):
                raise EvaluationError(f"T{tool} has wrong spindle speed")
            if segment.feed is None or not close(segment.feed, contract["feed"], 0.75):
                raise EvaluationError(f"T{tool} has wrong cutting feed")
            if segment.wcs != "G54" or not segment.length_comp or segment.h_offset != tool:
                raise EvaluationError(f"T{tool} must cut in G54 with G43 H{tool}")
            if tool in (1, 2) and segment.comp != 40:
                raise EvaluationError("pocket and drill paths must not use unresolved cutter compensation")
    safe_horizontal_rapid = False
    for segment in program.segments:
        if segment.motion != 0 or segment.machine_coordinates:
            continue
        xy_distance = math.hypot(segment.end.x - segment.start.x, segment.end.y - segment.start.y)
        if xy_distance > 0.2:
            if min(segment.start.z, segment.end.z) < 1.0:
                raise EvaluationError("horizontal rapid below safe clearance")
            if min(segment.start.z, segment.end.z) >= 2.5:
                safe_horizontal_rapid = True
        if segment.end.z < segment.start.z and segment.end.z < -0.75:
            raise EvaluationError("downward rapid enters unverified material")
    if not safe_horizontal_rapid:
        raise EvaluationError("missing safe rapid positioning")


def grid_covered(points: list[Point], xs: list[float], ys: list[float], radius: float) -> bool:
    return all(any(math.hypot(point.x - x, point.y - y) <= radius for point in points) for x in xs for y in ys)


def validate_pocket(program: Program) -> None:
    segs = material_segments(program, 1)
    material_points = [point for segment in segs for point in segment.samples if point.z <= 0.1]
    if not material_points or min(point.z for point in material_points) > -2.9:
        raise EvaluationError("pocket does not reach Z=-3")
    if any(point.z < -3.35 for point in material_points):
        raise EvaluationError("pocket is too deep")
    if any(abs(point.x) > 20.65 or abs(point.y) > 8.65 for point in material_points):
        raise EvaluationError("pocket tool center leaves the D8-safe pocket domain")
    bottom = [point for point in material_points if -3.25 <= point.z <= -2.85]
    if len(bottom) < 150:
        raise EvaluationError("insufficient pocket floor motion")
    targets = []
    for x in range(-24, 25, 2):
        for y in range(-12, 13, 2):
            # A D8 end mill leaves radius-4 internal corners.  Test every
            # reachable point in that rounded 48 x 24 pocket, including all
            # four straight walls, without demanding impossible sharp corners.
            corner_distance = math.hypot(max(abs(x) - 20.0, 0.0), max(abs(y) - 8.0, 0.0))
            if corner_distance <= 4.05:
                targets.append((float(x), float(y)))
    if not all(any(math.hypot(point.x - x, point.y - y) <= 4.15 for point in bottom) for x, y in targets):
        raise EvaluationError("D8 swept path does not cover the 48 x 24 pocket")


def nearest_hole(x: float, y: float) -> tuple[float, int]:
    distances = [math.hypot(x - hx, y - hy) for hx, hy in HOLES]
    index = min(range(len(distances)), key=distances.__getitem__)
    return distances[index], index


def validate_drill(program: Program) -> None:
    segs = material_segments(program, 2)
    depths = [math.inf, math.inf]
    seen = [False, False]
    for segment in segs:
        xy_motion = math.hypot(segment.end.x - segment.start.x, segment.end.y - segment.start.y)
        distance_to_hole, index = nearest_hole(segment.end.x, segment.end.y)
        if xy_motion > 0.25 or distance_to_hole > 0.75:
            raise EvaluationError("T2 may only feed vertically at the two hole centers")
        seen[index] = True
        depths[index] = min(depths[index], segment.start.z, segment.end.z)
    if not all(seen) or any(depth > -12.25 for depth in depths):
        raise EvaluationError("both holes must pass through the 12 mm stock")
    if any(depth < -15.0 for depth in depths):
        raise EvaluationError("drilling depth is unreasonable")


def signed_area(points: list[Point]) -> float:
    return 0.5 * sum(a.x * b.y - b.x * a.y for a, b in zip(points, points[1:]))


def connected_horizontal_runs(segments: list[Segment]) -> list[tuple[list[Point], list[Segment]]]:
    runs: list[tuple[list[Point], list[Segment]]] = []
    points: list[Point] = []
    members: list[Segment] = []
    for segment in segments:
        horizontal = abs(segment.start.z - segment.end.z) <= 0.3
        if horizontal:
            if not points or distance(points[-1], segment.start) <= 0.6:
                if not points:
                    points.append(segment.start)
                points.extend(segment.samples[1:])
                members.append(segment)
            else:
                runs.append((points, members))
                points = [segment.start, *segment.samples[1:]]
                members = [segment]
        elif points:
            runs.append((points, members))
            points, members = [], []
    if points:
        runs.append((points, members))
    return runs


def boundary_grid_covered(points: list[Point], xmin: float, xmax: float, ymin: float, ymax: float, tolerance: float) -> bool:
    targets = [
        *[(x, ymin) for x in (xmin, (xmin + xmax) / 2.0, xmax)],
        *[(x, ymax) for x in (xmin, (xmin + xmax) / 2.0, xmax)],
        *[(xmin, y) for y in (ymin, (ymin + ymax) / 2.0, ymax)],
        *[(xmax, y) for y in (ymin, (ymin + ymax) / 2.0, ymax)],
    ]
    return all(any(math.hypot(point.x - x, point.y - y) <= tolerance for point in points) for x, y in targets)


def validate_profile(program: Program) -> None:
    segs = material_segments(program, 3)
    material_points = [point for segment in segs for point in segment.samples if point.z <= 0.1]
    if any(point.z < -12.35 for point in material_points):
        raise EvaluationError("outside profile is too deep")
    for segment in segs:
        if abs(segment.start.z - segment.end.z) > 0.3:
            continue
        for point in segment.samples:
            metric = max(abs(point.x) - 36.0, abs(point.y) - 24.0)
            if metric < -0.6 or metric > 8.0:
                raise EvaluationError("profile contains an inside cut or unrelated far cut")

    full_depth = [
        segment for segment in segs
        if abs(segment.start.z - segment.end.z) <= 0.3
        and min(segment.start.z, segment.end.z) <= -11.7
        and max(segment.start.z, segment.end.z) >= -12.3
    ]
    for points, members in connected_horizontal_runs(full_depth):
        if len(members) < 4 or len(points) < 50 or distance(points[0], points[-1]) > 0.8:
            continue
        xs = [point.x for point in points]
        ys = [point.y for point in points]
        offset_geometry = (
            close(min(xs), -39.0, 0.8)
            and close(max(xs), 39.0, 0.8)
            and close(min(ys), -27.0, 0.8)
            and close(max(ys), 27.0, 0.8)
            and boundary_grid_covered(points, -39.0, 39.0, -27.0, 27.0, 1.25)
            and all(2.15 <= max(abs(point.x) - 36.0, abs(point.y) - 24.0) <= 3.85 for point in points)
            and all(segment.comp == 40 for segment in members)
        )
        if offset_geometry:
            return
        nominal_geometry = (
            close(min(xs), -36.0, 0.8)
            and close(max(xs), 36.0, 0.8)
            and close(min(ys), -24.0, 0.8)
            and close(max(ys), 24.0, 0.8)
            and boundary_grid_covered(points, -36.0, 36.0, -24.0, 24.0, 1.25)
        )
        if nominal_geometry:
            required_comp = 41 if signed_area(points) < 0 else 42
            if all(segment.comp == required_comp and segment.d_offset == 3 for segment in members):
                return
    raise EvaluationError("missing closed, correctly offset outside profile at Z=-12")


def evaluate_text(src: str) -> bool:
    try:
        program = parse_program(src)
        validate_common(program)
        validate_pocket(program)
        validate_drill(program)
        validate_profile(program)
        return True
    except (EvaluationError, OverflowError, ValueError):
        return False


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> bool:
    for name, expected in INPUT_HASHES.items():
        path = TARGET / name
        if not path.is_file() or path.stat().st_size == 0 or sha256(path) != expected:
            return False
    path = TARGET / NC_NAME
    if not path.is_file() or path.stat().st_size == 0 or path.stat().st_size > MAX_FILE_BYTES:
        return False
    return evaluate_text(path.read_text(encoding="utf-8", errors="strict"))


if __name__ == "__main__":
    try:
        result = main()
    except Exception:
        result = False
    print("True" if result else "False")
    raise SystemExit(0)
