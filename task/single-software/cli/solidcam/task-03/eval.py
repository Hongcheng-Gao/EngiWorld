from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


TASK_ID = "c-solidcam-task-03-windows"
DEFAULT_TARGET = Path(os.environ.get("EVAL_TARGET_DIR", r"C:\Users\User\Desktop"))
FORMAL_INPUT_HASHES = {
    "p1.step": "94AC54C5CCDC099B3DC8B4A9388EA2569ABE00B1990F9ED4ABAB3C8B18668D89",
    "p2.step": "92B555DB82FA889FB50886DE6896E66163DA5B825C45DFCC22131287A88B5959",
    "p3.step": "CE7B81F3F900419091FDBC3544B625A426F9A40453641D703F73CC7B7AF9BC94",
    "tools.csv": "AAB1EAAB0D96FDB7EF50EDE31110250CAE818D7236E105570035B36349161CAC",
}
PARTS = {
    "p1.nc": {"source": "p1.step", "half_x": 40.0, "half_y": 25.0},
    "p2.nc": {"source": "p2.step", "half_x": 47.5, "half_y": 27.5},
    "p3.nc": {"source": "p3.step", "half_x": 55.0, "half_y": 32.5},
}
TOOL_NUMBER = 1
TOOL_DIAMETER_MM = 6.0
TOOL_RADIUS_MM = TOOL_DIAMETER_MM / 2.0
SPINDLE_RPM = 9000.0
CUT_FEED_MM_MIN = 650.0
FINAL_DEPTH_MIN = -12.5
FINAL_DEPTH_MAX = -9.5
XY_TOL = 0.75
DEPTH_TOL = 0.25
MAX_CLOSURE_GAP = TOOL_DIAMETER_MM


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
    motion: int
    samples: list[Point]
    comp: int
    d_offset: int | None
    tool: int | None
    spindle_rpm: float | None
    spindle_on: bool
    feed_mm_min: float | None
    wcs: str | None
    length_comp: bool
    h_offset: int | None
    machine_coordinates: bool
    line_number: int


@dataclass
class Program:
    segments: list[Segment]
    tool_changes: list[int]
    terminated: bool
    explicit_metric_or_inch: bool
    explicit_absolute: bool
    executable_lines: int


@dataclass(frozen=True)
class LoopCandidate:
    points: list[Point]
    comps: list[int]


WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def strip_comments(text: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    depth = 0
    for line_number, raw in enumerate(text.upper().splitlines(), 1):
        clean: list[str] = []
        for char in raw:
            if char == ";" and depth == 0:
                break
            if char == "(":
                depth += 1
                continue
            if char == ")":
                if depth == 0:
                    raise EvaluationError(f"unmatched comment close on line {line_number}")
                depth -= 1
                continue
            if depth == 0:
                clean.append(char)
        out.append((line_number, "".join(clean).strip()))
    if depth != 0:
        raise EvaluationError("unterminated parenthesized comment")
    return out


def words(line: str) -> list[tuple[str, float]]:
    return [(letter, float(value)) for letter, value in WORD_RE.findall(line)]


def close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def distance(a: Point, b: Point) -> float:
    return math.dist((a.x, a.y, a.z), (b.x, b.y, b.z))


def dense_line(start: Point, end: Point, spacing: float = 1.0) -> list[Point]:
    length = distance(start, end)
    count = max(1, int(math.ceil(length / spacing)))
    return [
        Point(
            start.x + (end.x - start.x) * i / count,
            start.y + (end.y - start.y) * i / count,
            start.z + (end.z - start.z) * i / count,
        )
        for i in range(count + 1)
    ]


def directed_sweep(start_angle: float, end_angle: float, clockwise: bool) -> float:
    if clockwise:
        sweep = (start_angle - end_angle) % (2 * math.pi)
    else:
        sweep = (end_angle - start_angle) % (2 * math.pi)
    return sweep if sweep > 1e-9 else 2 * math.pi


def arc_from_ij(start: Point, end: Point, i: float, j: float, clockwise: bool) -> list[Point]:
    cx, cy = start.x + i, start.y + j
    radius = math.hypot(start.x - cx, start.y - cy)
    if radius <= 1e-6:
        raise EvaluationError("zero-radius arc")
    if not close(math.hypot(end.x - cx, end.y - cy), radius, 0.2):
        raise EvaluationError("arc endpoint is inconsistent with I/J center")
    start_angle = math.atan2(start.y - cy, start.x - cx)
    end_angle = math.atan2(end.y - cy, end.x - cx)
    sweep = directed_sweep(start_angle, end_angle, clockwise)
    count = max(8, int(math.ceil(radius * sweep / 1.0)))
    direction = -1.0 if clockwise else 1.0
    return [
        Point(
            cx + radius * math.cos(start_angle + direction * sweep * k / count),
            cy + radius * math.sin(start_angle + direction * sweep * k / count),
            start.z + (end.z - start.z) * k / count,
        )
        for k in range(count + 1)
    ]


def arc_from_r(start: Point, end: Point, signed_radius: float, clockwise: bool) -> list[Point]:
    chord_x, chord_y = end.x - start.x, end.y - start.y
    chord = math.hypot(chord_x, chord_y)
    radius = abs(signed_radius)
    if chord <= 1e-9 or chord > 2 * radius + 0.2:
        raise EvaluationError("invalid R arc")
    mid_x, mid_y = (start.x + end.x) / 2, (start.y + end.y) / 2
    height = math.sqrt(max(radius * radius - (chord / 2) ** 2, 0.0))
    nx, ny = -chord_y / chord, chord_x / chord
    centers = [(mid_x + nx * height, mid_y + ny * height), (mid_x - nx * height, mid_y - ny * height)]
    choices: list[tuple[float, float, float]] = []
    for cx, cy in centers:
        a0 = math.atan2(start.y - cy, start.x - cx)
        a1 = math.atan2(end.y - cy, end.x - cx)
        choices.append((directed_sweep(a0, a1, clockwise), cx, cy))
    if signed_radius >= 0:
        sweep, cx, cy = min(choices, key=lambda item: item[0])
    else:
        sweep, cx, cy = max(choices, key=lambda item: item[0])
    start_angle = math.atan2(start.y - cy, start.x - cx)
    count = max(8, int(math.ceil(radius * sweep / 1.0)))
    direction = -1.0 if clockwise else 1.0
    return [
        Point(
            cx + radius * math.cos(start_angle + direction * sweep * k / count),
            cy + radius * math.sin(start_angle + direction * sweep * k / count),
            start.z + (end.z - start.z) * k / count,
        )
        for k in range(count + 1)
    ]


def parse_program(text: str) -> Program:
    units: str | None = None
    absolute: bool | None = None
    motion: int | None = None
    current = Point(0.0, 0.0, 0.0)
    position_initialized = False
    pending_tool: int | None = None
    active_tool: int | None = None
    spindle_rpm: float | None = None
    spindle_on = False
    feed_mm_min: float | None = None
    comp = 40
    d_offset: int | None = None
    wcs: str | None = None
    length_comp = False
    h_offset: int | None = None
    terminated = False
    segments: list[Segment] = []
    tool_changes: list[int] = []
    executable_lines = 0

    for line_number, line in strip_comments(text):
        if not line or line == "%":
            continue
        if any(token in line for token in ("#", "[", "]", "=")):
            raise EvaluationError(f"unsupported macro/expression on line {line_number}")
        line_words = words(line)
        if not line_words:
            if re.fullmatch(r"O\d+", line):
                continue
            raise EvaluationError(f"unparsed executable text on line {line_number}")
        if terminated:
            raise EvaluationError(f"executable code after M30 on line {line_number}")
        executable_lines += 1
        grouped: dict[str, list[float]] = {}
        for letter, value in line_words:
            grouped.setdefault(letter, []).append(value)

        gcodes = grouped.get("G", [])
        mcodes = [int(round(value)) for value in grouped.get("M", [])]
        machine_coordinates = any(close(code, 53.0, 1e-6) for code in gcodes) or 28 in [int(round(x)) for x in gcodes]
        for code in gcodes:
            if close(code, 20.0, 1e-6):
                units = "inch"
            elif close(code, 21.0, 1e-6):
                units = "mm"
            elif close(code, 90.0, 1e-6):
                absolute = True
            elif close(code, 91.0, 1e-6):
                absolute = False
            elif close(code, 17.0, 1e-6):
                pass
            elif close(code, 40.0, 1e-6):
                comp = 40
            elif close(code, 41.0, 1e-6):
                comp = 41
            elif close(code, 42.0, 1e-6):
                comp = 42
            elif close(code, 43.0, 1e-6):
                length_comp = True
            elif close(code, 49.0, 1e-6):
                length_comp = False
                h_offset = None
            elif any(close(code, candidate, 1e-6) for candidate in (54, 55, 56, 57, 58, 59)):
                wcs = f"G{int(round(code))}"
            elif close(code, 54.1, 1e-6):
                p_value = int(round(grouped.get("P", [0])[-1]))
                if p_value <= 0:
                    raise EvaluationError("G54.1 requires positive P")
                wcs = f"G54.1P{p_value}"
            elif any(close(code, candidate, 1e-6) for candidate in (0, 1, 2, 3)):
                motion = int(round(code))
            elif any(close(code, candidate, 1e-6) for candidate in (80, 94)):
                pass
            elif close(code, 28.0, 1e-6) or close(code, 53.0, 1e-6):
                pass
            else:
                raise EvaluationError(f"unsupported G code G{code:g} on line {line_number}")

        if "T" in grouped:
            pending_tool = int(round(grouped["T"][-1]))
            if pending_tool != TOOL_NUMBER:
                raise EvaluationError(f"unexpected tool T{pending_tool}")
        if "S" in grouped:
            spindle_rpm = grouped["S"][-1]
        if "F" in grouped:
            if units is None:
                raise EvaluationError("feed appears before G20/G21")
            raw_feed = grouped["F"][-1]
            feed_mm_min = raw_feed * 25.4 if units == "inch" else raw_feed
            if feed_mm_min <= 0:
                raise EvaluationError("feed must be positive")
        if "H" in grouped:
            h_offset = int(round(grouped["H"][-1]))
        if "D" in grouped:
            d_offset = int(round(grouped["D"][-1]))
        if 6 in mcodes:
            if pending_tool is None:
                raise EvaluationError("M6 without a selected T word")
            active_tool = pending_tool
            tool_changes.append(active_tool)
        if 3 in mcodes or 4 in mcodes:
            spindle_on = True
        if 5 in mcodes:
            spindle_on = False
        if 30 in mcodes:
            if any(letter in grouped for letter in ("X", "Y", "Z")):
                raise EvaluationError("motion and M30 may not share a block")
            terminated = True
            continue

        has_axis = any(letter in grouped for letter in ("X", "Y", "Z"))
        if not has_axis:
            continue
        if machine_coordinates:
            # G28/G53 positions are outside the G54 part frame. Do not let
            # machine returns affect work-coordinate cutting or safety proof.
            continue
        if units is None or absolute is None:
            raise EvaluationError("axis motion occurs before explicit units and distance mode")
        if motion is None:
            raise EvaluationError("axis words occur before an explicit motion mode")
        factor = 25.4 if units == "inch" else 1.0

        def target_axis(letter: str, old: float) -> float:
            if letter not in grouped:
                return old
            value = grouped[letter][-1] * factor
            return value if absolute else old + value

        end = Point(target_axis("X", current.x), target_axis("Y", current.y), target_axis("Z", current.z))
        if motion in (0, 1):
            samples = dense_line(current, end)
        else:
            if "I" in grouped or "J" in grouped:
                i = grouped.get("I", [0.0])[-1] * factor
                j = grouped.get("J", [0.0])[-1] * factor
                samples = arc_from_ij(current, end, i, j, clockwise=motion == 2)
            elif "R" in grouped:
                samples = arc_from_r(current, end, grouped["R"][-1] * factor, clockwise=motion == 2)
            else:
                raise EvaluationError("G2/G3 requires I/J or R")
        segments.append(
            Segment(
                start=current,
                end=end,
                motion=motion,
                samples=samples,
                comp=comp,
                d_offset=d_offset,
                tool=active_tool,
                spindle_rpm=spindle_rpm,
                spindle_on=spindle_on,
                feed_mm_min=feed_mm_min,
                wcs=wcs,
                length_comp=length_comp,
                h_offset=h_offset,
                machine_coordinates=machine_coordinates,
                line_number=line_number,
            )
        )
        current = end
        position_initialized = True

    if not position_initialized:
        raise EvaluationError("program has no motion")
    return Program(
        segments=segments,
        tool_changes=tool_changes,
        terminated=terminated,
        explicit_metric_or_inch=units is not None,
        explicit_absolute=absolute is not None,
        executable_lines=executable_lines,
    )


def profile_segments(program: Program) -> list[Segment]:
    return [
        segment
        for segment in program.segments
        if not segment.machine_coordinates
        and segment.motion in (1, 2, 3)
        and max(segment.start.z, segment.end.z) <= FINAL_DEPTH_MAX + DEPTH_TOL
        and abs(segment.start.z - segment.end.z) <= DEPTH_TOL
    ]


def build_runs(segments: list[Segment]) -> list[tuple[list[Point], list[int]]]:
    runs: list[tuple[list[Point], list[int]]] = []
    current_points: list[Point] = []
    current_comps: list[int] = []
    previous_line: int | None = None
    previous_end: Point | None = None
    for segment in segments:
        contiguous = previous_end is not None and distance(previous_end, segment.start) <= 0.25
        line_contiguous = previous_line is not None and segment.line_number >= previous_line
        if not contiguous or not line_contiguous:
            if len(current_points) >= 2:
                runs.append((current_points, current_comps))
            current_points, current_comps = [], []
        for index, point in enumerate(segment.samples):
            if current_points and index == 0 and distance(current_points[-1], point) <= 1e-6:
                continue
            current_points.append(point)
            current_comps.append(segment.comp)
        previous_end = segment.end
        previous_line = segment.line_number
    if len(current_points) >= 2:
        runs.append((current_points, current_comps))
    return runs


def path_length(points: list[Point]) -> float:
    return sum(math.hypot(b.x - a.x, b.y - a.y) for a, b in zip(points, points[1:]))


def closed_candidates(runs: list[tuple[list[Point], list[int]]], minimum_length: float) -> Iterable[LoopCandidate]:
    for points, comps in runs:
        cumulative = [0.0]
        for a, b in zip(points, points[1:]):
            cumulative.append(cumulative[-1] + math.hypot(b.x - a.x, b.y - a.y))
        for start_index in range(len(points) - 4):
            for end_index in range(start_index + 4, len(points)):
                if cumulative[end_index] - cumulative[start_index] < minimum_length:
                    continue
                if math.hypot(points[end_index].x - points[start_index].x, points[end_index].y - points[start_index].y) <= MAX_CLOSURE_GAP:
                    yield LoopCandidate(points[start_index : end_index + 1], comps[start_index : end_index + 1])
                    break


def rectangle_distance(x: float, y: float, hx: float, hy: float) -> float:
    return math.hypot(max(abs(x) - hx, 0.0), max(abs(y) - hy, 0.0))


def rectangle_boundary_distance(x: float, y: float, hx: float, hy: float) -> float:
    if abs(x) <= hx and abs(y) <= hy:
        return min(hx - abs(x), hy - abs(y))
    return rectangle_distance(x, y, hx, hy)


def covers_sides(points: list[Point], hx: float, hy: float, offset: float) -> bool:
    left = [p.y for p in points if abs(p.x - (-hx - offset)) <= XY_TOL]
    right = [p.y for p in points if abs(p.x - (hx + offset)) <= XY_TOL]
    bottom = [p.x for p in points if abs(p.y - (-hy - offset)) <= XY_TOL]
    top = [p.x for p in points if abs(p.y - (hy + offset)) <= XY_TOL]
    return (
        left and min(left) <= -hy + XY_TOL and max(left) >= hy - XY_TOL
        and right and min(right) <= -hy + XY_TOL and max(right) >= hy - XY_TOL
        and bottom and min(bottom) <= -hx + XY_TOL and max(bottom) >= hx - XY_TOL
        and top and min(top) <= -hx + XY_TOL and max(top) >= hx - XY_TOL
    )


def signed_area(points: list[Point]) -> float:
    return 0.5 * sum(a.x * b.y - b.x * a.y for a, b in zip(points, points[1:] + points[:1]))


def validate_geometry_offset(loop: LoopCandidate, hx: float, hy: float) -> bool:
    if any(comp != 40 for comp in loop.comps):
        return False
    xs, ys = [p.x for p in loop.points], [p.y for p in loop.points]
    expected = (-hx - TOOL_RADIUS_MM, hx + TOOL_RADIUS_MM, -hy - TOOL_RADIUS_MM, hy + TOOL_RADIUS_MM)
    actual = (min(xs), max(xs), min(ys), max(ys))
    if any(not close(value, target, XY_TOL) for value, target in zip(actual, expected)):
        return False
    if any(rectangle_distance(p.x, p.y, hx, hy) < TOOL_RADIUS_MM - 0.5 for p in loop.points):
        return False
    return covers_sides(loop.points, hx, hy, TOOL_RADIUS_MM)


def validate_controller_comp(loop: LoopCandidate, hx: float, hy: float) -> bool:
    active = [comp for comp in loop.comps if comp in (41, 42)]
    if len(active) < int(len(loop.comps) * 0.8) or len(set(active)) != 1:
        return False
    if any(rectangle_boundary_distance(p.x, p.y, hx, hy) > XY_TOL for p in loop.points):
        return False
    if not covers_sides(loop.points, hx, hy, 0.0):
        return False
    area = signed_area(loop.points)
    expected_comp = 42 if area > 0 else 41
    return abs(area) > hx * hy and active[0] == expected_comp


def validate_program(program: Program, hx: float, hy: float) -> None:
    if not program.terminated:
        raise EvaluationError("M30 is required")
    if not program.explicit_metric_or_inch or not program.explicit_absolute:
        raise EvaluationError("explicit units and distance mode are required")
    if not program.tool_changes or any(tool != TOOL_NUMBER for tool in program.tool_changes):
        raise EvaluationError("T1 must be changed in and no other tool is allowed")
    cutting = [segment for segment in program.segments if not segment.machine_coordinates and segment.motion in (1, 2, 3) and min(segment.start.z, segment.end.z) < -0.1]
    if not cutting:
        raise EvaluationError("no material-cutting motion")
    for segment in cutting:
        if segment.tool != TOOL_NUMBER:
            raise EvaluationError("cutting occurs without active T1")
        if not segment.spindle_on or segment.spindle_rpm is None or not close(segment.spindle_rpm, SPINDLE_RPM, 1.0):
            raise EvaluationError("cutting occurs without supplied spindle speed")
        if segment.feed_mm_min is None or segment.feed_mm_min <= 0:
            raise EvaluationError("cutting occurs without positive feed")
        if segment.wcs is None:
            raise EvaluationError("cutting occurs without an explicit work coordinate system")
        if not segment.length_comp or not segment.h_offset or segment.h_offset <= 0:
            raise EvaluationError("cutting occurs without G43 and a positive H offset")
        if segment.comp in (41, 42) and (segment.d_offset is None or segment.d_offset <= 0):
            raise EvaluationError("controller cutter compensation requires a positive D offset")
        for point in segment.samples:
            if abs(point.x) < hx - 1.0 and abs(point.y) < hy - 1.0 and point.z < -0.1:
                raise EvaluationError("cutting motion gouges the part interior")
    if min(point.z for segment in cutting for point in segment.samples) < FINAL_DEPTH_MIN:
        raise EvaluationError("cutting depth is implausibly below the part")
    profile = profile_segments(program)
    if not profile:
        raise EvaluationError("no level finishing contour near full depth")
    if not any(segment.feed_mm_min is not None and close(segment.feed_mm_min, CUT_FEED_MM_MIN, 1.0) for segment in profile):
        raise EvaluationError("full-depth contour does not use supplied cutting feed")
    expected_perimeter = 4 * (hx + hy)
    candidates = list(closed_candidates(build_runs(profile), minimum_length=expected_perimeter * 0.85))
    if not candidates:
        raise EvaluationError("no closed full-depth contour")
    if not any(validate_geometry_offset(loop, hx, hy) or validate_controller_comp(loop, hx, hy) for loop in candidates):
        raise EvaluationError("no correct outside-compensated contour")
    first_cut_index = program.segments.index(cutting[0])
    last_cut_index = program.segments.index(cutting[-1])
    if not any(segment.motion == 0 and segment.end.z >= 2.0 for segment in program.segments[:first_cut_index]):
        raise EvaluationError("no safe rapid approach above the top face")
    if not any(segment.motion == 0 and segment.end.z >= 2.0 for segment in program.segments[last_cut_index + 1 :]):
        raise EvaluationError("no safe rapid retract after cutting")


def load_trusted_provenance(target: Path, path: Path | None = None, expected_sha256: str | None = None) -> dict[str, Any]:
    if path is None:
        raw_path = os.environ.get("ENGIWORLD_TRUSTED_PROVENANCE")
        if not raw_path:
            raise EvaluationError("trusted provenance path was not injected by the evaluator host")
        path = Path(raw_path)
    if expected_sha256 is None:
        expected_sha256 = os.environ.get("ENGIWORLD_TRUSTED_PROVENANCE_SHA256")
    if not expected_sha256 or not re.fullmatch(r"[0-9A-Fa-f]{64}", expected_sha256):
        raise EvaluationError("trusted provenance SHA-256 was not injected by the evaluator host")
    resolved_path, resolved_target = path.resolve(), target.resolve()
    try:
        if resolved_path.is_relative_to(resolved_target):
            raise EvaluationError("provenance may not be read from the agent-writable target directory")
    except AttributeError:
        if str(resolved_path).lower().startswith(str(resolved_target).lower() + os.sep):
            raise EvaluationError("provenance may not be read from the agent-writable target directory")
    if not path.is_file() or sha256_file(path) != expected_sha256.upper():
        raise EvaluationError("trusted provenance file is absent or not host-pinned")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise EvaluationError("trusted provenance must be a JSON object")
    return data


def require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvaluationError(f"{label} must be an object")
    return value


def validate_provenance(data: dict[str, Any], target: Path, programs: dict[str, Program], expected_run_id: str) -> None:
    if data.get("schema") != "engiworld.native-cam-provenance/v1" or data.get("task_id") != TASK_ID:
        raise EvaluationError("wrong provenance schema or task id")
    capture = require_dict(data.get("capture"), "capture")
    if capture.get("authority") != "host-monitor" or capture.get("immutable") is not True:
        raise EvaluationError("provenance was not captured by the trusted host monitor")
    if capture.get("run_id") != expected_run_id:
        raise EvaluationError("provenance belongs to a stale or different evaluator run")
    if data.get("interaction_mode") != "native_automation" or data.get("gui_clicks") != 0:
        raise EvaluationError("task was not completed through native command automation")
    if data.get("generic_gcode_generator") is not False or data.get("manual_nc_edit") is not False:
        raise EvaluationError("generic/manual NC generation is forbidden")
    product = require_dict(data.get("product"), "product")
    if str(product.get("name", "")).upper() != "SOLIDWORKS CAM" or int(product.get("major", 0)) != 2025:
        raise EvaluationError("native product must be SOLIDWORKS CAM 2025")
    if product.get("licensed") is not True or product.get("demo") is not False:
        raise EvaluationError("licensed non-demo product evidence is required")
    automation = require_dict(data.get("automation"), "automation")
    if str(automation.get("progid", "")).upper() != "SWCAM.CWAPP":
        raise EvaluationError("unexpected native automation ProgID")
    if not automation.get("type_library_sha256"):
        raise EvaluationError("type library identity is required")
    inputs = require_dict(data.get("inputs"), "inputs")
    for name, expected_hash in FORMAL_INPUT_HASHES.items():
        item = require_dict(inputs.get(name), f"inputs.{name}")
        if str(item.get("sha256", "")).upper() != expected_hash:
            raise EvaluationError(f"wrong formal input hash for {name}")
    post = require_dict(data.get("postprocessor"), "postprocessor")
    for field in ("name", "controller", "sha256"):
        if not post.get(field):
            raise EvaluationError(f"postprocessor.{field} is required")
    required_events = {
        "open_model",
        "create_cam_part",
        "set_setup_origin",
        "select_tool",
        "generate_toolpath",
        "simulate_toolpath",
        "post_process",
    }
    events = data.get("events")
    if not isinstance(events, list):
        raise EvaluationError("events must be a list")
    for nc_name in PARTS:
        successful_events = {
            event.get("action")
            for event in events
            if isinstance(event, dict) and event.get("success") is True and event.get("output") == nc_name
        }
        if not required_events.issubset(successful_events):
            raise EvaluationError(f"native operation lifecycle evidence is incomplete for {nc_name}")
    outputs = require_dict(data.get("outputs"), "outputs")
    seen_cam_parts: set[str] = set()
    for nc_name, contract in PARTS.items():
        output = require_dict(outputs.get(nc_name), f"outputs.{nc_name}")
        nc_path = target / nc_name
        if str(output.get("sha256", "")).upper() != sha256_file(nc_path):
            raise EvaluationError(f"posted output hash mismatch for {nc_name}")
        if output.get("source_model") != contract["source"]:
            raise EvaluationError(f"wrong source model for {nc_name}")
        cam_part_hash = str(output.get("cam_part_sha256", "")).upper()
        if not re.fullmatch(r"[0-9A-F]{64}", cam_part_hash) or cam_part_hash in seen_cam_parts:
            raise EvaluationError("each output requires a distinct native CAM part hash")
        seen_cam_parts.add(cam_part_hash)
        setup = require_dict(output.get("setup"), f"outputs.{nc_name}.setup")
        origin = setup.get("cad_origin_mm")
        if not isinstance(origin, list) or len(origin) != 3 or any(not close(float(actual), expected, 0.01) for actual, expected in zip(origin, (0.0, 0.0, 10.0))):
            raise EvaluationError(f"wrong top-face-center CAD origin for {nc_name}")
        if setup.get("program_zero_mode") != "top_face_center":
            raise EvaluationError(f"wrong program zero mode for {nc_name}")
        if setup.get("work_offset") not in {segment.wcs for segment in programs[nc_name].segments if segment.wcs}:
            raise EvaluationError(f"work offset is inconsistent for {nc_name}")
        operation = require_dict(output.get("operation"), f"outputs.{nc_name}.operation")
        expected_operation = {
            "type": "outside_profile",
            "tool_number": TOOL_NUMBER,
            "tool_diameter_mm": TOOL_DIAMETER_MM,
            "spindle_rpm": SPINDLE_RPM,
            "feed_mm_min": CUT_FEED_MM_MIN,
            "toolpath_generated": True,
            "post_succeeded": True,
        }
        for key, expected in expected_operation.items():
            actual = operation.get(key)
            if isinstance(expected, float):
                if actual is None or not close(float(actual), expected, 0.01):
                    raise EvaluationError(f"wrong {key} in provenance for {nc_name}")
            elif actual != expected:
                raise EvaluationError(f"wrong {key} in provenance for {nc_name}")
        simulation = require_dict(output.get("simulation"), f"outputs.{nc_name}.simulation")
        if not all(simulation.get(field) is True for field in ("completed", "gouge_free", "target_profile_reached")):
            raise EvaluationError(f"simulation evidence failed for {nc_name}")


def validate_outputs(target: Path) -> dict[str, Program]:
    programs: dict[str, Program] = {}
    for nc_name, contract in PARTS.items():
        path = target / nc_name
        if not path.is_file() or path.stat().st_size < 50:
            raise EvaluationError(f"missing or empty {nc_name}")
        program = parse_program(path.read_text(encoding="utf-8", errors="strict"))
        validate_program(program, contract["half_x"], contract["half_y"])
        programs[nc_name] = program
    return programs


def evaluate(
    target: Path,
    provenance_path: Path | None = None,
    provenance_sha256: str | None = None,
    expected_run_id: str | None = None,
) -> bool:
    programs = validate_outputs(target)
    if expected_run_id is None:
        expected_run_id = os.environ.get("ENGIWORLD_TRUSTED_RUN_ID")
    if not expected_run_id or not re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", expected_run_id):
        raise EvaluationError("trusted run id was not injected by the evaluator host")
    provenance = load_trusted_provenance(target, provenance_path, provenance_sha256)
    validate_provenance(provenance, target, programs, expected_run_id)
    return True


def main() -> bool:
    try:
        programs = validate_outputs(DEFAULT_TARGET)
        provenance_path = os.environ.get("ENGIWORLD_TRUSTED_PROVENANCE")
        provenance_sha256 = os.environ.get("ENGIWORLD_TRUSTED_PROVENANCE_SHA256")
        expected_run_id = os.environ.get("ENGIWORLD_TRUSTED_RUN_ID")
        supplied = [provenance_path, provenance_sha256, expected_run_id]
        if any(supplied) and not all(supplied):
            raise EvaluationError("trusted provenance injection is incomplete")
        if all(supplied):
            provenance = load_trusted_provenance(
                DEFAULT_TARGET,
                Path(str(provenance_path)),
                str(provenance_sha256),
            )
            validate_provenance(provenance, DEFAULT_TARGET, programs, str(expected_run_id))
        # Current task JSON cannot inject host evidence. In that deployment, this
        # entry point validates NC semantics only and ignores all agent-writable
        # provenance claims under Desktop.
        return True
    except Exception:
        return False


if __name__ == "__main__":
    sys.stdout.buffer.write(b"True\n" if main() else b"False\n")
    raise SystemExit(0)
