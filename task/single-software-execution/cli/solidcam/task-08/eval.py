from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path


DEFAULT_TARGET = Path(os.environ.get("EVAL_TARGET_DIR", r"C:\Users\User\Desktop"))
NC_NAME = "task-08.nc"
FORMAL_INPUT_SHA256 = {
    "rest_shape.step": "0BD5C588F430C2F75B53114C86D19CA771DB82CE19235394957C80519A3217B1",
    "tools.csv": "D0C13724660B07CE0BA088BEEFD9983D9DD96B85DC139729A8D269E9F4BF58DA",
}
TOOLS = {
    1: {"diameter_mm": 12.0, "radius_mm": 6.0, "spindle_rpm": 7000.0, "feed_mm_min": 500.0},
    2: {"diameter_mm": 4.0, "radius_mm": 2.0, "spindle_rpm": 10000.0, "feed_mm_min": 300.0},
}

WORD_RE = re.compile(r"([A-Z])\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))")
RUN_ID_RE = re.compile(r"[A-Za-z0-9._:-]{8,128}")
DEPTH_TOL_MM = 0.25
STATE_TOL = 1.0
SAFE_CLEARANCE_MM = 1.0
GEOMETRY_TOL_MM = 0.25
SAMPLE_SPACING_MM = 0.5


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
    spindle_on: bool
    spindle_rpm: float | None
    feed_mm_min: float | None
    wcs: str | None
    length_comp: bool
    h_offset: int | None
    machine_coordinates: bool
    line: int


@dataclass
class Program:
    segments: list[Segment]
    tool_changes: list[int]
    saw_m30: bool


def close(a: float, b: float, tolerance: float) -> bool:
    return abs(a - b) <= tolerance


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def strip_comments(source: str) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
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
                    raise EvaluationError(f"unmatched comment close on line {line_number}")
                depth -= 1
            elif depth == 0:
                clean.append(char)
        result.append((line_number, "".join(clean).strip()))
    if depth:
        raise EvaluationError("unterminated parenthesized comment")
    return result


def parse_words(code: str, line_number: int) -> list[tuple[str, float]]:
    if code == "%":
        return []
    if code.startswith("/"):
        code = code[1:].lstrip()
    matches = list(WORD_RE.finditer(code))
    residue = WORD_RE.sub(" ", code)
    if residue.strip():
        raise EvaluationError(f"unknown executable text on line {line_number}: {residue.strip()!r}")
    return [(match.group(1), float(match.group(2))) for match in matches]


def exact_int(value: float, label: str, line: int) -> int:
    rounded = round(value)
    if not close(value, rounded, 1e-8):
        raise EvaluationError(f"fractional {label} code on line {line}")
    return int(rounded)


def dense_line(start: Point, end: Point) -> list[Point]:
    length = math.dist((start.x, start.y, start.z), (end.x, end.y, end.z))
    count = max(1, int(math.ceil(length / SAMPLE_SPACING_MM)))
    return [
        Point(
            start.x + (end.x - start.x) * index / count,
            start.y + (end.y - start.y) * index / count,
            start.z + (end.z - start.z) * index / count,
        )
        for index in range(count + 1)
    ]


def directed_sweep(start_angle: float, end_angle: float, clockwise: bool) -> float:
    sweep = (start_angle - end_angle) % (2 * math.pi) if clockwise else (end_angle - start_angle) % (2 * math.pi)
    return sweep if sweep > 1e-9 else 2 * math.pi


def arc_from_ij(start: Point, end: Point, i: float, j: float, clockwise: bool) -> list[Point]:
    cx, cy = start.x + i, start.y + j
    radius = math.hypot(start.x - cx, start.y - cy)
    if radius <= 1e-6 or not close(math.hypot(end.x - cx, end.y - cy), radius, 0.2):
        raise EvaluationError("invalid I/J arc")
    a0, a1 = math.atan2(start.y - cy, start.x - cx), math.atan2(end.y - cy, end.x - cx)
    sweep = directed_sweep(a0, a1, clockwise)
    count = max(8, int(math.ceil(radius * sweep / SAMPLE_SPACING_MM)))
    sign = -1.0 if clockwise else 1.0
    return [
        Point(
            cx + radius * math.cos(a0 + sign * sweep * index / count),
            cy + radius * math.sin(a0 + sign * sweep * index / count),
            start.z + (end.z - start.z) * index / count,
        )
        for index in range(count + 1)
    ]


def arc_from_r(start: Point, end: Point, signed_radius: float, clockwise: bool) -> list[Point]:
    dx, dy = end.x - start.x, end.y - start.y
    chord = math.hypot(dx, dy)
    radius = abs(signed_radius)
    if chord <= 1e-9 or chord > 2 * radius + 0.2:
        raise EvaluationError("invalid R arc")
    mx, my = (start.x + end.x) / 2, (start.y + end.y) / 2
    height = math.sqrt(max(radius * radius - (chord / 2) ** 2, 0.0))
    nx, ny = -dy / chord, dx / chord
    choices = []
    for cx, cy in ((mx + nx * height, my + ny * height), (mx - nx * height, my - ny * height)):
        a0, a1 = math.atan2(start.y - cy, start.x - cx), math.atan2(end.y - cy, end.x - cx)
        choices.append((directed_sweep(a0, a1, clockwise), cx, cy))
    sweep, cx, cy = (min if signed_radius >= 0 else max)(choices, key=lambda item: item[0])
    a0 = math.atan2(start.y - cy, start.x - cx)
    count = max(8, int(math.ceil(radius * sweep / SAMPLE_SPACING_MM)))
    sign = -1.0 if clockwise else 1.0
    return [
        Point(
            cx + radius * math.cos(a0 + sign * sweep * index / count),
            cy + radius * math.sin(a0 + sign * sweep * index / count),
            start.z + (end.z - start.z) * index / count,
        )
        for index in range(count + 1)
    ]


def parse_program(source: str) -> Program:
    units: float | None = None
    absolute: bool | None = None
    motion: int | None = None
    current = Point(0.0, 0.0, 0.0)
    pending_tool: int | None = None
    active_tool: int | None = None
    spindle_on = False
    spindle_rpm: float | None = None
    feed_mm_min: float | None = None
    wcs: str | None = None
    length_comp = False
    h_offset: int | None = None
    terminated = False
    saw_m30 = False
    segments: list[Segment] = []
    tool_changes: list[int] = []

    allowed_g = {0.0, 1.0, 2.0, 3.0, 17.0, 20.0, 21.0, 28.0, 40.0, 43.0, 49.0, 53.0, 54.0, 54.1, 55.0, 56.0, 57.0, 58.0, 59.0, 80.0, 90.0, 91.0, 94.0}
    allowed_m = {0, 1, 2, 3, 4, 5, 6, 8, 9, 30}

    for line_number, code in strip_comments(source):
        if not code or code == "%":
            continue
        words = parse_words(code, line_number)
        if not words:
            continue
        if terminated:
            raise EvaluationError(f"executable code after M30 on line {line_number}")
        grouped: dict[str, list[float]] = {}
        for letter, value in words:
            grouped.setdefault(letter, []).append(value)
        for letter in grouped:
            if letter not in "NGMTSFXYZIJRHDPO":
                raise EvaluationError(f"unsupported word {letter} on line {line_number}")
        for letter in "XYZIJRHDSTP":
            if len(grouped.get(letter, [])) > 1:
                raise EvaluationError(f"duplicate {letter} on line {line_number}")

        gcodes = grouped.get("G", [])
        mcodes = [exact_int(value, "M", line_number) for value in grouped.get("M", [])]
        for gcode in gcodes:
            if not any(close(gcode, allowed, 1e-7) for allowed in allowed_g):
                raise EvaluationError(f"unsupported G code G{gcode:g} on line {line_number}")
        for mcode in mcodes:
            if mcode not in allowed_m:
                raise EvaluationError(f"unsupported M code M{mcode} on line {line_number}")

        axis_present = any(letter in grouped for letter in "XYZ")
        block_motion = any(any(close(g, candidate, 1e-7) for candidate in (0, 1, 2, 3)) for g in gcodes)
        if 30 in mcodes:
            if axis_present or block_motion:
                raise EvaluationError(f"motion in M30 block on line {line_number}")
            terminated = True
            saw_m30 = True
            continue

        g28_return = any(close(g, 28, 1e-7) for g in gcodes)
        machine_coordinates = g28_return or any(close(g, 53, 1e-7) for g in gcodes)
        for gcode in gcodes:
            if close(gcode, 20, 1e-7):
                units = 25.4
            elif close(gcode, 21, 1e-7):
                units = 1.0
            elif close(gcode, 90, 1e-7):
                absolute = True
            elif close(gcode, 91, 1e-7):
                absolute = False
            elif any(close(gcode, candidate, 1e-7) for candidate in (0, 1, 2, 3)):
                motion = int(round(gcode))
            elif close(gcode, 43, 1e-7):
                length_comp = True
            elif close(gcode, 49, 1e-7):
                length_comp = False
                h_offset = None
            elif any(close(gcode, candidate, 1e-7) for candidate in (54, 55, 56, 57, 58, 59)):
                wcs = f"G{int(round(gcode))}"
            elif close(gcode, 54.1, 1e-7):
                p_value = grouped.get("P", [None])[-1]
                if p_value is None or exact_int(p_value, "P", line_number) <= 0:
                    raise EvaluationError("G54.1 requires positive P")
                wcs = f"G54.1 P{exact_int(p_value, 'P', line_number)}"

        if "T" in grouped:
            pending_tool = exact_int(grouped["T"][-1], "T", line_number)
            if pending_tool not in TOOLS:
                raise EvaluationError(f"unexpected tool T{pending_tool}")
        if 6 in mcodes:
            if pending_tool is None:
                raise EvaluationError(f"M6 without T word on line {line_number}")
            active_tool = pending_tool
            tool_changes.append(active_tool)
            length_comp = False
            h_offset = None
        if "S" in grouped:
            spindle_rpm = grouped["S"][-1]
            if spindle_rpm <= 0:
                raise EvaluationError("spindle speed must be positive")
        if 3 in mcodes or 4 in mcodes:
            spindle_on = True
        if 5 in mcodes:
            spindle_on = False
        if "F" in grouped:
            if units is None:
                raise EvaluationError("feed appears before units")
            feed_mm_min = grouped["F"][-1] * units
            if feed_mm_min <= 0:
                raise EvaluationError("feed must be positive")
        if "H" in grouped:
            h_offset = exact_int(grouped["H"][-1], "H", line_number)
            if h_offset <= 0:
                raise EvaluationError("H offset must be positive")

        if not axis_present:
            continue
        if units is None or absolute is None:
            raise EvaluationError(f"axis motion before explicit units, distance, and motion modes on line {line_number}")
        # G28 is itself a reference-return command and does not require a
        # previously selected G0/G1 modal motion.  Native CAMWorks posts use
        # the legal startup form ``G91 G28 X0 Y0 Z0`` before the first G0.
        if g28_return:
            continue
        if motion is None:
            raise EvaluationError(f"axis motion before explicit motion mode on line {line_number}")
        scale = units

        def target_axis(letter: str, old: float) -> float:
            if letter not in grouped:
                return old
            value = grouped[letter][-1] * scale
            return value if absolute else old + value

        end = Point(target_axis("X", current.x), target_axis("Y", current.y), target_axis("Z", current.z))
        if machine_coordinates:
            continue
        if motion in (0, 1):
            samples = dense_line(current, end)
        elif "I" in grouped or "J" in grouped:
            samples = arc_from_ij(current, end, grouped.get("I", [0.0])[-1] * scale, grouped.get("J", [0.0])[-1] * scale, motion == 2)
        elif "R" in grouped:
            samples = arc_from_r(current, end, grouped["R"][-1] * scale, motion == 2)
        else:
            raise EvaluationError("G2/G3 requires I/J or R")
        segments.append(Segment(current, end, samples, motion, active_tool, spindle_on, spindle_rpm, feed_mm_min, wcs, length_comp, h_offset, False, line_number))
        current = end

    if not saw_m30:
        raise EvaluationError("M30 is required")
    if not segments:
        raise EvaluationError("program has no motion")
    return Program(segments, tool_changes, saw_m30)


def in_pocket(x: float, y: float, tolerance: float = 0.0) -> bool:
    return (
        abs(x) <= 35.0 + tolerance and abs(y) <= 10.0 + tolerance
    ) or (
        abs(x) <= 10.0 + tolerance and abs(y) <= 27.5 + tolerance
    )


def center_valid(x: float, y: float, radius: float) -> bool:
    numeric_slack = 1e-4
    if not in_pocket(x, y, GEOMETRY_TOL_MM + numeric_slack):
        return False
    for index in range(48):
        angle = 2 * math.pi * index / 48
        if not in_pocket(
            x + radius * math.cos(angle),
            y + radius * math.sin(angle),
            GEOMETRY_TOL_MM + numeric_slack,
        ):
            return False
    return True


TARGET_POINTS = [
    (x / 2.0, y / 2.0)
    for x in range(-70, 71)
    for y in range(-55, 56)
    if in_pocket(x / 2.0, y / 2.0)
]


def spatial_index(points: list[Point], cell_size: float = 1.0) -> dict[tuple[int, int], list[Point]]:
    index: dict[tuple[int, int], list[Point]] = {}
    for point in points:
        key = (math.floor(point.x / cell_size), math.floor(point.y / cell_size))
        index.setdefault(key, []).append(point)
    return index


def swept_by(
    x: float,
    y: float,
    indexes: dict[int, dict[tuple[int, int], list[Point]]],
    tool: int,
    cell_size: float = 1.0,
) -> bool:
    radius = float(TOOLS[tool]["radius_mm"]) + 0.35
    bx, by = math.floor(x / cell_size), math.floor(y / cell_size)
    reach = math.ceil(radius / cell_size)
    for ix in range(bx - reach, bx + reach + 1):
        for iy in range(by - reach, by + reach + 1):
            if any(math.hypot(point.x - x, point.y - y) <= radius for point in indexes[tool].get((ix, iy), ())):
                return True
    return False


def covered_ratio(
    targets: list[tuple[float, float]],
    indexes: dict[int, dict[tuple[int, int], list[Point]]],
    tools: tuple[int, ...],
) -> float:
    covered = 0
    for x, y in targets:
        covered += int(any(swept_by(x, y, indexes, tool) for tool in tools))
    return covered / len(targets)


def choose_frame(program: Program) -> tuple[float, float, list[Segment]]:
    candidates = []
    for top_z, floor_z in ((18.0, 6.0), (0.0, -12.0)):
        cutting = [
            segment for segment in program.segments
            if segment.motion in (1, 2, 3) and min(segment.start.z, segment.end.z) < top_z - 0.1
        ]
        if not cutting:
            continue
        if any(point.z < floor_z - DEPTH_TOL_MM for segment in cutting for point in segment.samples):
            continue
        floor = [
            segment for segment in cutting
            if abs(segment.start.z - floor_z) <= DEPTH_TOL_MM
            and abs(segment.end.z - floor_z) <= DEPTH_TOL_MM
            and math.hypot(segment.end.x - segment.start.x, segment.end.y - segment.start.y) > 0.1
        ]
        if {segment.tool for segment in floor} == {1, 2}:
            candidates.append((top_z, floor_z, cutting))
    if len(candidates) != 1:
        raise EvaluationError("toolpaths do not match exactly one supported Z frame")
    return candidates[0]


def validate_program(program: Program) -> dict[str, object]:
    top_z, floor_z, cutting = choose_frame(program)
    if not all(tool in program.tool_changes for tool in (1, 2)):
        raise EvaluationError("both supplied tools must be changed in")

    seen_t2_cutting = False
    saw_t1_cutting = False
    for segment in cutting:
        if segment.tool not in TOOLS:
            raise EvaluationError("cutting without a supplied active tool")
        if segment.tool == 2:
            seen_t2_cutting = True
        elif seen_t2_cutting:
            raise EvaluationError("large-tool cutting occurs after Rest machining begins")
        else:
            saw_t1_cutting = True
        contract = TOOLS[segment.tool]
        if not segment.spindle_on or segment.spindle_rpm is None or not close(segment.spindle_rpm, float(contract["spindle_rpm"]), STATE_TOL):
            raise EvaluationError(f"T{segment.tool} cutting uses the wrong spindle state or speed")
        commanded_feed = float(contract["feed_mm_min"])
        if segment.feed_mm_min is None or segment.feed_mm_min <= 0:
            raise EvaluationError(f"T{segment.tool} cutting has no positive feed")
        xy_length = math.hypot(segment.end.x - segment.start.x, segment.end.y - segment.start.y)
        if xy_length > 0.1:
            if not close(segment.feed_mm_min, commanded_feed, STATE_TOL):
                raise EvaluationError(f"T{segment.tool} XY cutting uses the wrong feed")
        elif segment.feed_mm_min > commanded_feed + STATE_TOL:
            raise EvaluationError(f"T{segment.tool} plunge feed exceeds the supplied cutting feed")
        if segment.wcs is None or not segment.length_comp or segment.h_offset is None or segment.h_offset <= 0:
            raise EvaluationError("cutting requires WCS and G43 with a positive H offset")
        radius = float(contract["radius_mm"])
        for point in segment.samples:
            if point.z < top_z - 0.1 and not center_valid(point.x, point.y, radius):
                raise EvaluationError(f"T{segment.tool} cutting leaves the pocket boundary near line {segment.line}")
    if not saw_t1_cutting or not seen_t2_cutting:
        raise EvaluationError("both main clearing and Rest cutting must be present")

    floor_paths: dict[int, list[Point]] = {1: [], 2: []}
    for segment in cutting:
        if (
            segment.tool in (1, 2)
            and abs(segment.start.z - floor_z) <= DEPTH_TOL_MM
            and abs(segment.end.z - floor_z) <= DEPTH_TOL_MM
        ):
            radius = float(TOOLS[segment.tool]["radius_mm"])
            for point in segment.samples:
                if not center_valid(point.x, point.y, radius):
                    raise EvaluationError(f"T{segment.tool} cutter leaves the pocket boundary near line {segment.line}")
                floor_paths[segment.tool].append(point)
    if min(len(floor_paths[1]), len(floor_paths[2])) < 8:
        raise EvaluationError("both tools need substantive full-depth paths")

    indexes = {tool: spatial_index(points) for tool, points in floor_paths.items()}
    t1_ratio = covered_ratio(TARGET_POINTS, indexes, (1,))
    t2_ratio = covered_ratio(TARGET_POINTS, indexes, (2,))
    combined_ratio = covered_ratio(TARGET_POINTS, indexes, (1, 2))
    if t1_ratio < 0.88:
        raise EvaluationError("large tool does not clear enough of the main pocket")
    if combined_ratio < 0.985:
        raise EvaluationError("combined toolpaths do not cover the target pocket")
    if combined_ratio - t1_ratio < 0.004:
        raise EvaluationError("small tool does not add measurable residual-material coverage")
    if t2_ratio > 0.60:
        raise EvaluationError("small tool re-machines most of the pocket instead of Rest regions")

    corner_witnesses = [
        *[(sx * 34.0, sy * 9.0) for sx in (-1, 1) for sy in (-1, 1)],
        *[(sx * 9.0, sy * 26.5) for sx in (-1, 1) for sy in (-1, 1)],
    ]
    for x, y in corner_witnesses:
        if not swept_by(x, y, indexes, 2):
            raise EvaluationError("small tool does not reach all large-tool residual corner regions")
        if swept_by(x, y, indexes, 1):
            raise EvaluationError("large-tool path enters a geometrically unreachable corner")

    safe = top_z + SAFE_CLEARANCE_MM
    for tool in (1, 2):
        tool_cutting = [segment for segment in cutting if segment.tool == tool]
        first_cut = min(segment.line for segment in tool_cutting)
        last_cut = max(segment.line for segment in tool_cutting)
        tool_rapids = [segment for segment in program.segments if segment.tool == tool and segment.motion == 0]
        if not any(segment.line < first_cut and max(segment.start.z, segment.end.z) >= safe for segment in tool_rapids):
            raise EvaluationError(f"T{tool} is missing a safe rapid approach")
        if not any(segment.line > last_cut and max(segment.start.z, segment.end.z) >= safe for segment in tool_rapids):
            raise EvaluationError(f"T{tool} is missing a safe rapid retract")

    return {
        "top_z_mm": top_z,
        "floor_z_mm": floor_z,
        "t1_coverage": round(t1_ratio, 6),
        "t2_coverage": round(t2_ratio, 6),
        "combined_coverage": round(combined_ratio, 6),
        "t1_floor_samples": len(floor_paths[1]),
        "t2_floor_samples": len(floor_paths[2]),
    }


def validate_outputs(target: Path) -> tuple[Program, dict[str, object]]:
    path = target / NC_NAME
    if not path.is_file() or path.stat().st_size < 100:
        raise EvaluationError(f"missing or empty {NC_NAME}")
    program = parse_program(path.read_text(encoding="utf-8", errors="strict"))
    return program, validate_program(program)


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def load_trusted_provenance(target: Path, path: Path | None, expected_hash: str | None) -> dict[str, object]:
    if path is None or expected_hash is None:
        raise EvaluationError("trusted provenance must be injected by the evaluator host")
    resolved = path.resolve(strict=True)
    target_resolved = target.resolve()
    writable_root = target_resolved
    for candidate in (target_resolved, *target_resolved.parents):
        if candidate.name.casefold() == "desktop":
            writable_root = candidate
            break
    if is_relative_to(resolved, writable_root):
        raise EvaluationError("provenance may not be inside the agent-writable target tree")
    if not re.fullmatch(r"[0-9A-Fa-f]{64}", expected_hash) or sha256_file(resolved) != expected_hash.upper():
        raise EvaluationError("trusted provenance file is absent or not host-pinned")
    data = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise EvaluationError("trusted provenance must be a JSON object")
    return data


def validate_provenance(data: dict[str, object], target: Path, expected_run_id: str) -> None:
    if data.get("schema") != "engiworld.trusted-rest-cam-run.v1" or data.get("run_id") != expected_run_id:
        raise EvaluationError("wrong provenance schema or stale run id")
    if data.get("authority") != "evaluator-host-monitor" or data.get("immutable") is not True:
        raise EvaluationError("provenance is not trusted host evidence")
    product = data.get("product")
    if not isinstance(product, dict) or str(product.get("name", "")).upper() != "SOLIDWORKS CAM" or int(product.get("major", 0)) != 2025:
        raise EvaluationError("native product must be SOLIDWORKS CAM 2025")
    if product.get("progid") != "SWCAM.CWApp" or product.get("addin_loaded") is not True:
        raise EvaluationError("SOLIDWORKS CAM add-in identity was not captured")
    inputs = data.get("formal_inputs")
    if not isinstance(inputs, dict) or any(str(inputs.get(name, "")).upper() != expected for name, expected in FORMAL_INPUT_SHA256.items()):
        raise EvaluationError("formal input hash mismatch")
    output = data.get("output")
    if not isinstance(output, dict) or output.get("name") != NC_NAME or str(output.get("sha256", "")).upper() != sha256_file(target / NC_NAME):
        raise EvaluationError("posted output hash mismatch")
    if int(output.get("bytes", 0)) != (target / NC_NAME).stat().st_size:
        raise EvaluationError("posted output size mismatch")
    setup = data.get("setup")
    if not isinstance(setup, dict) or setup.get("cad_origin_mm") != [0.0, 0.0, 18.0] or setup.get("tool_axis") != "-Z" or setup.get("work_offset") != "G54":
        raise EvaluationError("wrong native setup transform")
    operations = data.get("operations")
    if not isinstance(operations, list) or len(operations) != 2:
        raise EvaluationError("exactly two native CAM operations are required")
    expected = (("main_clear", 1, 12.0, 7000.0, 500.0), ("rest", 2, 4.0, 10000.0, 300.0))
    for index, (kind, tool, diameter, spindle, feed) in enumerate(expected):
        item = operations[index]
        if not isinstance(item, dict) or item.get("kind") != kind or int(item.get("tool_station", 0)) != tool:
            raise EvaluationError("native operation order or tool mismatch")
        values = (item.get("tool_diameter_mm"), item.get("spindle_rpm"), item.get("feed_mm_min"), item.get("floor_z_mm"))
        targets = (diameter, spindle, feed, 6.0)
        if any(not isinstance(value, (int, float)) or not close(float(value), target_value, STATE_TOL) for value, target_value in zip(values, targets)):
            raise EvaluationError("native operation parameter mismatch")
        if item.get("toolpath_generated") is not True or int(item.get("segment_count", 0)) <= 0:
            raise EvaluationError("native operation lifecycle evidence is incomplete")
    main_id = operations[0].get("operation_id")
    if not main_id or operations[1].get("rest_source_operation_id") != main_id or operations[1].get("previous_stock_hash") in (None, ""):
        raise EvaluationError("Rest operation is not bound to previous-operation stock")
    post = data.get("postprocess")
    if not isinstance(post, dict) or post.get("return_code") != 0 or not str(post.get("postprocessor", "")).lower().endswith(".ctl"):
        raise EvaluationError("native .ctl postprocess did not succeed")
    simulation = data.get("simulation")
    if not isinstance(simulation, dict) or simulation.get("completed") is not True or simulation.get("collision_free") is not True:
        raise EvaluationError("native simulation was not completed successfully")
    if simulation.get("rest_regions_cleared") is not True or not close(float(simulation.get("floor_z_mm", math.nan)), 6.0, DEPTH_TOL_MM):
        raise EvaluationError("native simulation did not verify Rest clearing and floor")


def evaluate(target: Path, provenance_path: Path | None = None, provenance_sha256: str | None = None, expected_run_id: str | None = None) -> bool:
    validate_outputs(target)
    run_id = expected_run_id or os.environ.get("ENGIWORLD_TRUSTED_RUN_ID")
    if not run_id or not RUN_ID_RE.fullmatch(run_id):
        raise EvaluationError("trusted run id was not injected by the evaluator host")
    provenance = load_trusted_provenance(target, provenance_path, provenance_sha256)
    validate_provenance(provenance, target, run_id)
    return True


def main() -> bool:
    try:
        validate_outputs(DEFAULT_TARGET)
        path = os.environ.get("ENGIWORLD_TRUSTED_PROVENANCE")
        pin = os.environ.get("ENGIWORLD_TRUSTED_PROVENANCE_SHA256")
        run_id = os.environ.get("ENGIWORLD_TRUSTED_RUN_ID")
        supplied = [path, pin, run_id]
        if any(supplied) and not all(supplied):
            raise EvaluationError("trusted provenance injection is incomplete")
        if all(supplied):
            if not RUN_ID_RE.fullmatch(str(run_id)):
                raise EvaluationError("trusted run id is malformed")
            provenance = load_trusted_provenance(DEFAULT_TARGET, Path(str(path)), str(pin))
            validate_provenance(provenance, DEFAULT_TARGET, str(run_id))
        return True
    except Exception:
        return False


if __name__ == "__main__":
    print("True" if main() else "False")
    raise SystemExit(0)
