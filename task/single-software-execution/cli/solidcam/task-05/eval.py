from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from pathlib import Path


TARGET = Path(os.environ.get("EVAL_TARGET_DIR", r"C:\Users\User\Desktop"))
NC_NAME = "task-05.nc"
TOOL_CONTRACT = {
    1: {"diameter": 16.0, "spindle": 7000.0, "feed": 500.0},
    2: {"diameter": 8.0, "spindle": 8000.0, "feed": 450.0},
    3: {"diameter": 5.0, "spindle": 5000.0, "feed": 180.0},
}
HOLES = [(-35.0, -20.0), (-35.0, 20.0), (35.0, -20.0), (35.0, 20.0)]
WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))")


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


def dense_line(start: Point, end: Point, spacing: float = 1.0) -> list[Point]:
    count = max(1, int(math.ceil(distance(start, end) / spacing)))
    return [
        Point(
            start.x + (end.x - start.x) * i / count,
            start.y + (end.y - start.y) * i / count,
            start.z + (end.z - start.z) * i / count,
        )
        for i in range(count + 1)
    ]


def strip_comments(src: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    depth = 0
    for line_number, raw in enumerate(src.upper().splitlines(), 1):
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
        out.append((line_number, "".join(clean).strip()))
    if depth:
        raise EvaluationError("unterminated comment")
    return out


def arc_points(start: Point, end: Point, i: float, j: float, clockwise: bool) -> list[Point]:
    cx, cy = start.x + i, start.y + j
    radius = math.hypot(start.x - cx, start.y - cy)
    if radius <= 1e-6 or not close(math.hypot(end.x - cx, end.y - cy), radius, 0.25):
        raise EvaluationError("invalid I/J arc")
    a0 = math.atan2(start.y - cy, start.x - cx)
    a1 = math.atan2(end.y - cy, end.x - cx)
    sweep = (a0 - a1) % (2 * math.pi) if clockwise else (a1 - a0) % (2 * math.pi)
    if sweep <= 1e-9:
        sweep = 2 * math.pi
    direction = -1.0 if clockwise else 1.0
    count = max(12, int(math.ceil(radius * sweep)))
    return [
        Point(
            cx + radius * math.cos(a0 + direction * sweep * k / count),
            cy + radius * math.sin(a0 + direction * sweep * k / count),
            start.z + (end.z - start.z) * k / count,
        )
        for k in range(count + 1)
    ]


def parse_program(src: str) -> Program:
    units: str | None = None
    absolute: bool | None = None
    motion: int | None = None
    current = Point(0.0, 0.0, 0.0)
    pending_tool: int | None = None
    tool: int | None = None
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
    tool_changes: list[int] = []

    for line_number, line in strip_comments(src):
        if not line or line == "%":
            continue
        if any(ch in line for ch in "#[]="):
            raise EvaluationError("macros and expressions are unsupported")
        found = WORD_RE.findall(line)
        if not found:
            if re.fullmatch(r"O\d+", line):
                continue
            raise EvaluationError(f"unparsed text on line {line_number}")
        residue = WORD_RE.sub("", line)
        residue = re.sub(r"[\s/]+", "", residue)
        if residue:
            raise EvaluationError(f"unknown executable text on line {line_number}")
        if terminated:
            raise EvaluationError("executable code after M30")
        executable_lines += 1
        grouped: dict[str, list[float]] = {}
        for letter, value in found:
            grouped.setdefault(letter, []).append(float(value))
        gcodes = grouped.get("G", [])
        mcodes = [int(round(v)) for v in grouped.get("M", [])]
        machine_coordinates = any(close(g, 53.0, 1e-6) for g in gcodes)
        reference_return = any(close(g, 28.0, 1e-6) for g in gcodes)
        for g in gcodes:
            gi = int(round(g))
            if close(g, 20.0, 1e-6):
                units = "inch"
            elif close(g, 21.0, 1e-6):
                units = "mm"
            elif close(g, 90.0, 1e-6):
                absolute = True
            elif close(g, 91.0, 1e-6):
                absolute = False
            elif gi in (0, 1, 2, 3) and close(g, gi, 1e-6):
                motion = gi
            elif gi in (54, 55, 56, 57, 58, 59) and close(g, gi, 1e-6):
                wcs = f"G{gi}"
            elif close(g, 43.0, 1e-6):
                length_comp = True
            elif close(g, 49.0, 1e-6):
                length_comp = False
                h_offset = None
            elif gi in (40, 41, 42) and close(g, gi, 1e-6):
                comp = gi
                if gi == 40:
                    d_offset = None
            elif gi in (81, 82, 83) and close(g, gi, 1e-6):
                cycle = gi
            elif gi == 80 and close(g, 80.0, 1e-6):
                cycle = None
            elif close(g, 17.0, 1e-6) or close(g, 28.0, 1e-6) or close(g, 94.0, 1e-6) or close(g, 98.0, 1e-6) or close(g, 99.0, 1e-6) or close(g, 53.0, 1e-6):
                pass
            elif close(g, 54.1, 1e-6):
                p = int(round(grouped.get("P", [0])[-1]))
                if p <= 0:
                    raise EvaluationError("invalid G54.1 offset")
                wcs = f"G54.1P{p}"
            else:
                raise EvaluationError(f"unsupported G code G{g:g}")
        factor = 25.4 if units == "inch" else 1.0
        if "T" in grouped:
            pending_tool = int(round(grouped["T"][-1]))
        if "S" in grouped:
            spindle = grouped["S"][-1]
        if "F" in grouped:
            feed = grouped["F"][-1] * factor
        if "H" in grouped:
            h_offset = int(round(grouped["H"][-1]))
        if "D" in grouped:
            d_offset = int(round(grouped["D"][-1]))
        if 6 in mcodes:
            if pending_tool is None:
                raise EvaluationError("M6 without tool")
            tool = pending_tool
            tool_changes.append(tool)
        if 3 in mcodes or 4 in mcodes:
            spindle_on = True
        if 5 in mcodes:
            spindle_on = False
        if 30 in mcodes:
            terminated = True
        if absolute is None and any(k in grouped for k in ("X", "Y", "Z")):
            raise EvaluationError("motion before explicit G90/G91")
        if units is None and any(k in grouped for k in ("X", "Y", "Z", "F")):
            raise EvaluationError("motion before explicit G20/G21")

        def coord(axis: str, old: float) -> float:
            if axis not in grouped:
                return old
            value = grouped[axis][-1] * factor
            return value if absolute else old + value

        new = Point(coord("X", current.x), coord("Y", current.y), coord("Z", current.z))
        if reference_return:
            # G28 traverses from the programmed intermediate point to a
            # controller-defined machine reference point.  The second leg is
            # outside work coordinates and must not be invented as part
            # geometry.  Native M3Axis output uses G91 G28 with zero deltas,
            # so retaining the intermediate point is sufficient until the
            # following absolute G54 move.
            current = new
            continue
        if cycle is not None and any(k in grouped for k in ("X", "Y", "Z")):
            if "Z" in grouped:
                cycle_z = new.z
            if "R" in grouped:
                raw_r = grouped["R"][-1] * factor
                cycle_r = raw_r if absolute else current.z + raw_r
            if cycle_z is None or cycle_r is None:
                raise EvaluationError("incomplete drilling cycle")
            xy = Point(new.x, new.y, current.z)
            top = Point(new.x, new.y, cycle_r)
            bottom = Point(new.x, new.y, cycle_z)
            segments.append(Segment(xy, top, dense_line(xy, top), 0, tool, spindle, spindle_on, feed, wcs, length_comp, h_offset, comp, d_offset, False, line_number))
            segments.append(Segment(top, bottom, dense_line(top, bottom), 1, tool, spindle, spindle_on, feed, wcs, length_comp, h_offset, comp, d_offset, False, line_number))
            current = top
            continue
        if any(k in grouped for k in ("X", "Y", "Z")) and motion is not None:
            if motion in (2, 3):
                if "I" not in grouped or "J" not in grouped:
                    raise EvaluationError("arcs require I/J")
                samples = arc_points(current, new, grouped["I"][-1] * factor, grouped["J"][-1] * factor, motion == 2)
            else:
                samples = dense_line(current, new)
            segments.append(Segment(current, new, samples, motion, tool, spindle, spindle_on, feed, wcs, length_comp, h_offset, comp, d_offset, machine_coordinates, line_number))
            current = new
    return Program(segments, tool_changes, terminated, units is not None, absolute is not None, executable_lines)


def cutting_segments(program: Program, tool: int) -> list[Segment]:
    return [s for s in program.segments if s.tool == tool and s.motion in (1, 2, 3) and distance(s.start, s.end) > 1e-5]


def validate_common(program: Program) -> None:
    if not program.terminated or not program.explicit_units or not program.explicit_distance_mode or program.executable_lines < 15:
        raise EvaluationError("incomplete executable program")
    if set(program.tool_changes) != {1, 2, 3}:
        raise EvaluationError("tool set must be exactly T1/T2/T3")
    for tool, contract in TOOL_CONTRACT.items():
        segs = cutting_segments(program, tool)
        if not segs:
            raise EvaluationError(f"T{tool} has no cutting motion")
        valid = [
            s for s in segs
            if s.spindle_on
            and s.spindle is not None and close(s.spindle, contract["spindle"], 1.0)
            and s.feed is not None and close(s.feed, contract["feed"], 0.75)
            and s.wcs is not None and s.length_comp and s.h_offset is not None and s.h_offset > 0
        ]
        if not valid:
            raise EvaluationError(f"T{tool} lacks cutting under required S/F/WCS/G43/H")
        if any(s.tool not in TOOL_CONTRACT for s in program.segments if s.tool is not None):
            raise EvaluationError("unexpected tool")
    if not any(s.motion == 0 and max(s.start.z, s.end.z) >= 3.0 for s in program.segments):
        raise EvaluationError("missing safe rapid clearance")


def points_for(segs: list[Segment], zmin: float, zmax: float) -> list[Point]:
    return [p for s in segs for p in s.samples if zmin <= p.z <= zmax]


def grid_covered(points: list[Point], xs: list[float], ys: list[float], radius: float) -> bool:
    return all(any(math.hypot(p.x - x, p.y - y) <= radius for p in points) for x in xs for y in ys)


def validate_face(program: Program) -> None:
    pts = points_for(cutting_segments(program, 1), -2.0, 0.75)
    if len(pts) < 100:
        raise EvaluationError("insufficient face motion")
    if not grid_covered(pts, [-52, -26, 0, 26, 52], [-32, -16, 0, 16, 32], 9.0):
        raise EvaluationError("face does not cover the 120 x 80 top")


def validate_pocket(program: Program) -> None:
    pts = [p for p in points_for(cutting_segments(program, 2), -11.25, -9.25) if abs(p.x) <= 28.5 and abs(p.y) <= 18.5]
    if len(pts) < 50 or not grid_covered(pts, [-20, -10, 0, 10, 20], [-10, 0, 10], 4.8):
        raise EvaluationError("48 x 28 pocket is not cleared to depth 10")


def validate_drill(program: Program) -> None:
    vertical = []
    for s in cutting_segments(program, 3):
        if math.hypot(s.end.x - s.start.x, s.end.y - s.start.y) <= 0.25 and min(s.start.z, s.end.z) <= -18.0:
            vertical.append((s.end.x, s.end.y))
    for hx, hy in HOLES:
        if not any(math.hypot(x - hx, y - hy) <= 0.75 for x, y in vertical):
            raise EvaluationError("missing one or more through holes")
    if any(min(math.hypot(x - hx, y - hy) for hx, hy in HOLES) > 0.75 for x, y in vertical):
        raise EvaluationError("unexpected drilling location")


def signed_area(points: list[Point]) -> float:
    return 0.5 * sum(a.x * b.y - b.x * a.y for a, b in zip(points, points[1:]))


def near_closed_subloops(points: list[Point]) -> list[list[Point]]:
    loops: list[list[Point]] = []
    if len(points) >= 50 and distance(points[0], points[-1]) <= 2.0:
        loops.append(points)
    for start in range(len(points) - 50):
        for end in range(start + 50, len(points)):
            if distance(points[start], points[end]) <= 2.0:
                loops.append(points[start : end + 1])
    return loops


def validate_profile(program: Program) -> None:
    segs = cutting_segments(program, 2)
    candidates: list[tuple[list[Point], list[Segment]]] = []
    run: list[Point] = []
    run_segments: list[Segment] = []
    for s in segs:
        horizontal = abs(s.start.z - s.end.z) <= 0.3 and min(s.start.z, s.end.z) <= -17.25
        if horizontal:
            if not run or distance(run[-1], s.start) <= 0.5:
                if not run:
                    run.append(s.start)
                run.extend(s.samples[1:])
                run_segments.append(s)
            else:
                if run:
                    candidates.append((run, run_segments))
                run = [s.start, *s.samples[1:]]
                run_segments = [s]
        elif run:
            candidates.append((run, run_segments))
            run = []
            run_segments = []
    if run:
        candidates.append((run, run_segments))
    for pts, loop_segments in candidates:
        if len(pts) < 50:
            continue
        for loop in near_closed_subloops(pts):
            xs, ys = [p.x for p in loop], [p.y for p in loop]
            geometry_offset = close(min(xs), -64, 1.0) and close(max(xs), 64, 1.0) and close(min(ys), -44, 1.0) and close(max(ys), 44, 1.0)
            nominal_points = [p for p in loop if abs(p.x) <= 60.75 and abs(p.y) <= 40.75]
            nominal = (
                nominal_points
                and close(min(p.x for p in nominal_points), -60, 1.0)
                and close(max(p.x for p in nominal_points), 60, 1.0)
                and close(min(p.y for p in nominal_points), -40, 1.0)
                and close(max(p.y for p in nominal_points), 40, 1.0)
                and all(
                    any(abs(p.x - x) <= 0.75 and abs(p.y - y) <= 0.75 for p in nominal_points)
                    for x, y in ((-60, -40), (60, -40), (60, 40), (-60, 40))
                )
            )
            comps = {s.comp for s in loop_segments}
            if geometry_offset and all(max(abs(p.x) - 60, abs(p.y) - 40) >= 3.0 for p in loop):
                return
            if nominal:
                area = signed_area(loop)
                required = 42 if area > 0 else 41
                if required in comps and any(s.d_offset is not None and s.d_offset > 0 for s in loop_segments):
                    return
    raise EvaluationError("missing closed compensated outside profile at full depth")


def evaluate_text(src: str) -> bool:
    try:
        program = parse_program(src)
        validate_common(program)
        validate_face(program)
        validate_pocket(program)
        validate_drill(program)
        validate_profile(program)
        return True
    except (EvaluationError, OverflowError, ValueError):
        return False


def main() -> bool:
    path = TARGET / NC_NAME
    if not path.is_file() or path.stat().st_size == 0:
        return False
    return evaluate_text(path.read_text(encoding="utf-8", errors="strict"))


if __name__ == "__main__":
    try:
        result = main()
    except Exception:
        result = False
    print("True" if result else "False")
    raise SystemExit(0)
