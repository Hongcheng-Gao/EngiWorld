from __future__ import annotations

import hashlib
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path


TARGET = Path(os.environ.get("EVAL_TARGET_DIR", r"C:\Users\User\Desktop"))
NC_NAME = "task-16_B.nc"
FORMAL_INPUT_SHA256 = {
    "revision_A.step": "DAECF5831BDF01B09ED6A70451FECD392DF71E713BFBFCCA394AB38DE8FFBFCF",
    "revision_B.step": "311AE1C5C1DCDC072F6FFE14A156538CD6437BA83D8C9993991C965998F64F96",
    "tools.csv": "9D72E8222EC38E3D7CBC5CB1DF6DCCB9DB3E847B8040BC5B4C83D17116CE0D96",
}
TOOLS = {
    1: {"diameter": 8.0, "spindle": 8000.0, "feed": 500.0},
    2: {"diameter": 5.0, "spindle": 5000.0, "feed": 180.0},
}
B_HOLES = ((-30.0, -15.0), (30.0, 15.0))
WORD_RE = re.compile(r"([A-Z])\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))")
ALLOWED_G = {0.0, 1.0, 2.0, 3.0, 17.0, 20.0, 21.0, 28.0, 40.0, 43.0, 49.0, 53.0, 54.0, 54.1, 55.0, 56.0, 57.0, 58.0, 59.0, 80.0, 81.0, 82.0, 83.0, 90.0, 91.0, 94.0, 98.0, 99.0}
ALLOWED_M = {0, 1, 2, 3, 4, 5, 6, 8, 9, 30}
STATE_TOL = 1.0
DEPTH_TOL = 0.35
MAX_BYTES = 1_000_000
MAX_LINES = 12_000
MAX_WORDS_PER_LINE = 40
MAX_SEGMENTS = 20_000
MAX_SAMPLES = 250_000


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
    spindle: float | None
    feed: float | None
    wcs: str | None
    length_comp: bool
    h_offset: int | None
    line: int


@dataclass
class DrillEvent:
    x: float
    y: float
    bottom_z: float
    approach_z: float | None
    retract_z: float | None
    tool: int | None
    spindle_on: bool
    spindle: float | None
    feed: float | None
    wcs: str | None
    length_comp: bool
    h_offset: int | None
    line: int


@dataclass
class Program:
    segments: list[Segment]
    cycles: list[DrillEvent]
    tool_changes: list[int]
    saw_m30: bool


def close(actual: float, expected: float, tolerance: float) -> bool:
    return abs(actual - expected) <= tolerance


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def comments(source: str) -> list[str]:
    result: list[str] = []
    depth = 0
    buffer: list[str] = []
    for line_number, raw in enumerate(source.upper().splitlines(), 1):
        index = 0
        while index < len(raw):
            char = raw[index]
            if char == ";" and depth == 0:
                result.append(raw[index + 1 :])
                break
            if char == "(":
                if depth == 0:
                    buffer = []
                depth += 1
                if depth > 8:
                    raise EvaluationError("excessive nested comment")
            elif char == ")":
                if depth == 0:
                    raise EvaluationError(f"unmatched comment close on line {line_number}")
                depth -= 1
                if depth == 0:
                    result.append("".join(buffer))
                    buffer = []
            elif depth:
                buffer.append(char)
            index += 1
    if depth:
        raise EvaluationError("unterminated parenthesized comment")
    return result


def executable_lines(source: str) -> list[tuple[int, str]]:
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


def words(code: str, line: int) -> list[tuple[str, float]]:
    if not code or code == "%":
        return []
    if code.startswith("/"):
        raise EvaluationError(f"block-delete code is not deterministic on line {line}")
    matches = list(WORD_RE.finditer(code))
    if len(matches) > MAX_WORDS_PER_LINE:
        raise EvaluationError(f"too many words on line {line}")
    residue = WORD_RE.sub(" ", code)
    if residue.strip():
        raise EvaluationError(f"unknown executable text on line {line}: {residue.strip()!r}")
    result = [(match.group(1), float(match.group(2))) for match in matches]
    if any(not math.isfinite(value) or abs(value) > 10_000_000 for _, value in result):
        raise EvaluationError(f"non-finite or excessive numeric word on line {line}")
    return result


def exact_int(value: float, label: str, line: int) -> int:
    rounded = round(value)
    if not close(value, rounded, 1e-8):
        raise EvaluationError(f"fractional {label} on line {line}")
    return int(rounded)


def line_samples(start: Point, end: Point, spacing: float = 0.5) -> list[Point]:
    length = math.dist((start.x, start.y, start.z), (end.x, end.y, end.z))
    if not math.isfinite(length) or length > 1000.0:
        raise EvaluationError("invalid or excessive line length")
    count = max(1, int(math.ceil(length / spacing)))
    return [Point(start.x + (end.x - start.x) * i / count, start.y + (end.y - start.y) * i / count, start.z + (end.z - start.z) * i / count) for i in range(count + 1)]


def directed_sweep(start: float, end: float, clockwise: bool) -> float:
    sweep = (start - end) % (2 * math.pi) if clockwise else (end - start) % (2 * math.pi)
    return sweep if sweep > 1e-9 else 2 * math.pi


def arc_samples(start: Point, end: Point, grouped: dict[str, list[float]], scale: float, clockwise: bool) -> list[Point]:
    if "I" in grouped or "J" in grouped:
        cx = start.x + grouped.get("I", [0.0])[-1] * scale
        cy = start.y + grouped.get("J", [0.0])[-1] * scale
        radius = math.hypot(start.x - cx, start.y - cy)
        if radius <= 1e-6 or radius > 500.0 or not close(math.hypot(end.x - cx, end.y - cy), radius, 0.2):
            raise EvaluationError("invalid I/J arc")
        a0 = math.atan2(start.y - cy, start.x - cx)
        a1 = math.atan2(end.y - cy, end.x - cx)
        sweep = directed_sweep(a0, a1, clockwise)
    elif "R" in grouped:
        dx, dy = end.x - start.x, end.y - start.y
        chord = math.hypot(dx, dy)
        signed_radius = grouped["R"][-1] * scale
        radius = abs(signed_radius)
        if chord <= 1e-9 or radius > 500.0 or chord > 2 * radius + 0.2:
            raise EvaluationError("invalid R arc")
        mx, my = (start.x + end.x) / 2, (start.y + end.y) / 2
        height = math.sqrt(max(radius * radius - (chord / 2) ** 2, 0.0))
        nx, ny = -dy / chord, dx / chord
        candidates = []
        for cx0, cy0 in ((mx + nx * height, my + ny * height), (mx - nx * height, my - ny * height)):
            aa0 = math.atan2(start.y - cy0, start.x - cx0)
            aa1 = math.atan2(end.y - cy0, end.x - cx0)
            candidates.append((directed_sweep(aa0, aa1, clockwise), cx0, cy0, aa0))
        sweep, cx, cy, a0 = (min if signed_radius >= 0 else max)(candidates, key=lambda item: item[0])
    else:
        raise EvaluationError("G2/G3 requires I/J or R")
    count = max(8, int(math.ceil(radius * sweep / 0.35)))
    sign = -1.0 if clockwise else 1.0
    return [Point(cx + radius * math.cos(a0 + sign * sweep * i / count), cy + radius * math.sin(a0 + sign * sweep * i / count), start.z + (end.z - start.z) * i / count) for i in range(count + 1)]


def parse_program(source: str) -> Program:
    units: float | None = None
    absolute: bool | None = None
    motion: int | None = None
    current = Point(0.0, 0.0, 0.0)
    position_known = True
    pending_tool: int | None = None
    active_tool: int | None = None
    spindle_on = False
    spindle: float | None = None
    feed: float | None = None
    wcs: str | None = None
    length_comp = False
    h_offset: int | None = None
    cycle: int | None = None
    cycle_z: float | None = None
    cycle_r: float | None = None
    cycle_q: float | None = None
    retract_mode = 98
    terminated = False
    segments: list[Segment] = []
    cycles: list[DrillEvent] = []
    tool_changes: list[int] = []
    sample_count = 0

    for line_number, code in executable_lines(source):
        parsed = words(code, line_number)
        if not parsed:
            continue
        if terminated:
            raise EvaluationError(f"executable code after M30 on line {line_number}")
        grouped: dict[str, list[float]] = {}
        for letter, value in parsed:
            grouped.setdefault(letter, []).append(value)
        if any(letter not in "NGMTSFXYZIJRQHDPO" for letter in grouped):
            raise EvaluationError(f"unsupported word on line {line_number}")
        for letter in "NXYZIJRQHDSTPO":
            if len(grouped.get(letter, [])) > 1:
                raise EvaluationError(f"duplicate {letter} on line {line_number}")
        if "N" in grouped:
            exact_int(grouped["N"][0], "N", line_number)
        if "O" in grouped and exact_int(grouped["O"][0], "O", line_number) <= 0:
            raise EvaluationError(f"invalid O number on line {line_number}")
        gcodes = grouped.get("G", [])
        mcodes = [exact_int(value, "M", line_number) for value in grouped.get("M", [])]
        if any(not any(close(code_value, allowed, 1e-7) for allowed in ALLOWED_G) for code_value in gcodes):
            raise EvaluationError(f"unsupported G code on line {line_number}")
        if any(code_value not in ALLOWED_M for code_value in mcodes):
            raise EvaluationError(f"unsupported M code on line {line_number}")
        if sum(any(close(code_value, mode, 1e-7) for code_value in gcodes) for mode in (20.0, 21.0)) > 1:
            raise EvaluationError("conflicting unit modes")
        if sum(any(close(code_value, mode, 1e-7) for code_value in gcodes) for mode in (90.0, 91.0)) > 1:
            raise EvaluationError("conflicting distance modes")
        if sum(any(close(code_value, mode, 1e-7) for code_value in gcodes) for mode in (0.0, 1.0, 2.0, 3.0)) > 1:
            raise EvaluationError("conflicting motion modes")
        if sum(any(close(code_value, mode, 1e-7) for code_value in gcodes) for mode in (80.0, 81.0, 82.0, 83.0)) > 1:
            raise EvaluationError("conflicting canned-cycle modes")
        if sum(any(close(code_value, mode, 1e-7) for code_value in gcodes) for mode in (98.0, 99.0)) > 1:
            raise EvaluationError("conflicting retract modes")
        if 30 in mcodes:
            if set(grouped) - {"N", "M"} or mcodes != [30]:
                raise EvaluationError("M30 block contains hidden executable words")
            terminated = True
            continue

        g28 = any(close(code_value, 28.0, 1e-7) for code_value in gcodes)
        g53 = any(close(code_value, 53.0, 1e-7) for code_value in gcodes)
        if g28:
            if any(any(close(code_value, mode, 1e-7) for mode in (0, 1, 2, 3, 81, 82, 83)) for code_value in gcodes):
                raise EvaluationError("G28 cannot hide cutting motion")
            if any(abs(value) > 1e-8 for letter in "XYZ" for value in grouped.get(letter, [])):
                raise EvaluationError("only zero-intermediate G28 is accepted")

        for code_value in gcodes:
            if close(code_value, 20.0, 1e-7): units = 25.4
            elif close(code_value, 21.0, 1e-7): units = 1.0
            elif close(code_value, 90.0, 1e-7): absolute = True
            elif close(code_value, 91.0, 1e-7): absolute = False
            elif any(close(code_value, mode, 1e-7) for mode in (0, 1, 2, 3)):
                motion = int(round(code_value)); cycle = None
            elif any(close(code_value, mode, 1e-7) for mode in (81, 82, 83)):
                cycle = int(round(code_value))
            elif close(code_value, 80.0, 1e-7): cycle = None
            elif close(code_value, 98.0, 1e-7): retract_mode = 98
            elif close(code_value, 99.0, 1e-7): retract_mode = 99
            elif close(code_value, 43.0, 1e-7): length_comp = True
            elif close(code_value, 49.0, 1e-7): length_comp = False; h_offset = None
            elif any(close(code_value, value, 1e-7) for value in (54, 55, 56, 57, 58, 59)): wcs = f"G{int(round(code_value))}"
            elif close(code_value, 54.1, 1e-7):
                p_value = grouped.get("P", [None])[-1]
                if p_value is None or exact_int(p_value, "P", line_number) <= 0:
                    raise EvaluationError("G54.1 requires positive P")
                wcs = f"G54.1 P{exact_int(p_value, 'P', line_number)}"

        if g28 and absolute is not False:
            raise EvaluationError("G28 requires G91 zero-intermediate return")
        arc_mode = cycle is None and motion in (2, 3)
        if ("I" in grouped or "J" in grouped) and not arc_mode:
            raise EvaluationError("I/J is valid only for G2/G3")
        if "R" in grouped and cycle is None and not arc_mode:
            raise EvaluationError("R is valid only for G2/G3 or a canned cycle")
        if "Q" in grouped and cycle != 83:
            raise EvaluationError("Q is valid only for G83")
        if "P" in grouped and not any(close(code_value, 54.1, 1e-7) for code_value in gcodes):
            raise EvaluationError("P is valid only with G54.1")
        if "D" in grouped:
            raise EvaluationError("D offset is unsupported without cutter compensation")

        if "T" in grouped:
            pending_tool = exact_int(grouped["T"][-1], "T", line_number)
            if pending_tool not in TOOLS:
                raise EvaluationError(f"unexpected tool T{pending_tool}")
        if 6 in mcodes:
            if pending_tool is None:
                raise EvaluationError("M6 without T")
            active_tool = pending_tool
            tool_changes.append(active_tool)
            spindle_on = False
            length_comp = False
            h_offset = None
        if "S" in grouped:
            spindle = grouped["S"][-1]
            if spindle <= 0:
                raise EvaluationError("spindle speed must be positive")
        if 3 in mcodes or 4 in mcodes:
            spindle_on = True
        if 5 in mcodes:
            spindle_on = False
        if "F" in grouped:
            if units is None:
                raise EvaluationError("feed before units")
            feed = grouped["F"][-1] * units
            if feed <= 0:
                raise EvaluationError("feed must be positive")
        if "H" in grouped:
            h_offset = exact_int(grouped["H"][-1], "H", line_number)
            if h_offset <= 0:
                raise EvaluationError("H must be positive")

        axes = any(letter in grouped for letter in "XYZ")
        if not axes:
            continue
        if units is None or absolute is None:
            raise EvaluationError("axis motion before units and distance mode")
        if g28:
            if "Z" in grouped:
                position_known = False
            continue
        if g53:
            if motion not in (0, None) or cycle is not None:
                raise EvaluationError("G53 is allowed only for non-cutting machine motion")
            if "Z" in grouped:
                position_known = False
            continue

        scale = units
        if cycle is not None:
            if not absolute:
                raise EvaluationError("canned cycles require G90")
            if "Z" in grouped: cycle_z = grouped["Z"][-1] * scale
            if "R" in grouped: cycle_r = grouped["R"][-1] * scale
            if "Q" in grouped: cycle_q = grouped["Q"][-1] * scale
            x_value = grouped.get("X", [current.x / scale])[-1] * scale
            y_value = grouped.get("Y", [current.y / scale])[-1] * scale
            launches = any(any(close(code_value, mode, 1e-7) for mode in (81, 82, 83)) for code_value in gcodes) or "X" in grouped or "Y" in grouped
            if launches:
                if cycle_z is None or cycle_r is None:
                    raise EvaluationError("incomplete canned cycle")
                if cycle == 83 and (cycle_q is None or cycle_q <= 0):
                    raise EvaluationError("G83 requires positive Q")
                retract_z = max(current.z, cycle_r) if retract_mode == 98 else cycle_r
                cycles.append(DrillEvent(x_value, y_value, cycle_z, current.z, retract_z, active_tool, spindle_on, spindle, feed, wcs, length_comp, h_offset, line_number))
                if len(cycles) > MAX_SEGMENTS:
                    raise EvaluationError("canned-cycle event limit exceeded")
                current = Point(x_value, y_value, retract_z)
                position_known = True
            continue
        if motion is None:
            raise EvaluationError("axis words before explicit motion mode")

        def axis(letter: str, old: float) -> float:
            if letter not in grouped:
                return old
            value = grouped[letter][-1] * scale
            return value if absolute else old + value

        end = Point(axis("X", current.x), axis("Y", current.y), axis("Z", current.z))
        if not position_known:
            current = end
            if "Z" in grouped:
                position_known = True
            continue
        samples = line_samples(current, end) if motion in (0, 1) else arc_samples(current, end, grouped, scale, motion == 2)
        segments.append(Segment(current, end, samples, motion, active_tool, spindle_on, spindle, feed, wcs, length_comp, h_offset, line_number))
        sample_count += len(samples)
        if len(segments) > MAX_SEGMENTS or sample_count > MAX_SAMPLES:
            raise EvaluationError("toolpath sampling resource limit exceeded")
        current = end

    if not terminated:
        raise EvaluationError("M30 is required")
    return Program(segments, cycles, tool_changes, True)


def explicit_drills(program: Program) -> list[DrillEvent]:
    events: list[DrillEvent] = []
    plunge: Segment | None = None
    approach: float | None = None

    def finish(retract: float | None) -> None:
        nonlocal plunge
        if plunge is None:
            return
        events.append(DrillEvent(plunge.end.x, plunge.end.y, plunge.end.z, approach if approach is not None else plunge.start.z, retract, plunge.tool, plunge.spindle_on, plunge.spindle, plunge.feed, plunge.wcs, plunge.length_comp, plunge.h_offset, plunge.line))
        plunge = None

    for segment in program.segments:
        if plunge is not None:
            same_axis = math.hypot(segment.end.x - plunge.end.x, segment.end.y - plunge.end.y) <= 0.05
            if segment.motion == 0 and same_axis and segment.end.z > plunge.end.z + 0.5:
                finish(segment.end.z)
                approach = segment.end.z
                continue
            if segment.motion == 1 and same_axis and segment.end.z < plunge.end.z - 0.05:
                plunge = segment
                continue
            if not same_axis:
                finish(None)
        if segment.motion == 0:
            approach = segment.end.z
        elif segment.motion == 1 and math.hypot(segment.end.x - segment.start.x, segment.end.y - segment.start.y) <= 0.05 and segment.end.z < segment.start.z - 0.05:
            plunge = segment
    finish(None)
    return events


def cutting_state(segment: Segment, tool: int) -> None:
    contract = TOOLS[tool]
    if segment.tool != tool or not segment.spindle_on or segment.spindle is None or not close(segment.spindle, contract["spindle"], STATE_TOL):
        raise EvaluationError(f"T{tool} cutting has the wrong spindle state")
    if segment.feed is None or segment.feed <= 0 or segment.wcs is None or not segment.length_comp or segment.h_offset != tool:
        raise EvaluationError(f"T{tool} cutting lacks feed/WCS/matching H offset")
    xy_length = math.hypot(segment.end.x - segment.start.x, segment.end.y - segment.start.y)
    if xy_length > 0.1 and not close(segment.feed, contract["feed"], STATE_TOL):
        raise EvaluationError(f"T{tool} XY cutting uses the wrong feed")
    if xy_length <= 0.1 and segment.feed > contract["feed"] + STATE_TOL:
        raise EvaluationError(f"T{tool} plunge feed exceeds the supplied feed")


def drill_state(event: DrillEvent) -> None:
    contract = TOOLS[2]
    if event.tool != 2 or not event.spindle_on or event.spindle is None or not close(event.spindle, contract["spindle"], STATE_TOL):
        raise EvaluationError("T2 drill has the wrong spindle state")
    if event.feed is None or not close(event.feed, contract["feed"], STATE_TOL) or event.wcs is None or not event.length_comp or event.h_offset != 2:
        raise EvaluationError("T2 drill lacks the supplied feed/WCS/H2")


def validate_frame(program: Program, top_z: float, floor_z: float, bottom_z: float) -> dict[str, float | int]:
    t1_cutting = [segment for segment in program.segments if segment.tool == 1 and segment.motion in (1, 2, 3) and min(segment.start.z, segment.end.z) < top_z - 0.1]
    if not t1_cutting:
        raise EvaluationError("missing revision_B pocket cutting")
    floor_points: list[Point] = []
    for segment in t1_cutting:
        cutting_state(segment, 1)
        for point in segment.samples:
            if point.z >= top_z - 0.1:
                continue
            if point.z < floor_z - DEPTH_TOL or abs(point.x) > 20.35 or abs(point.y) > 10.35:
                raise EvaluationError("T1 cuts outside or below the revision_B pocket")
            if abs(point.z - floor_z) <= DEPTH_TOL:
                floor_points.append(point)
    if len(floor_points) < 80:
        raise EvaluationError("revision_B pocket has too little full-depth cutting")
    targets = [(float(x), float(y)) for x in range(-24, 25) for y in range(-14, 15)]
    radius = TOOLS[1]["diameter"] / 2 + 0.4
    covered = sum(any(math.hypot(point.x - x, point.y - y) <= radius for point in floor_points) for x, y in targets)
    coverage = covered / len(targets)
    if coverage < 0.983:
        raise EvaluationError("revision_B pocket floor is undercovered")

    drill_events = [event for event in [*program.cycles, *explicit_drills(program)] if event.tool == 2]
    if len(drill_events) != 2:
        raise EvaluationError("revision_B requires exactly two T2 drilling events")
    for event in drill_events:
        drill_state(event)
        if not any(math.hypot(event.x - x, event.y - y) <= 0.35 for x, y in B_HOLES):
            raise EvaluationError("revision_A or unexpected hole was drilled")
        if not (bottom_z - 4.0 <= event.bottom_z <= bottom_z + DEPTH_TOL):
            raise EvaluationError("T2 drilling is not a bounded through cut")
        if event.approach_z is None or event.approach_z < top_z + 1.0 or event.retract_z is None or event.retract_z < top_z + 1.0:
            raise EvaluationError("unsafe T2 approach/retract")
    for hole in B_HOLES:
        if sum(math.hypot(event.x - hole[0], event.y - hole[1]) <= 0.35 for event in drill_events) != 1:
            raise EvaluationError("missing or duplicate revision_B hole")

    for segment in program.segments:
        xy_length = math.hypot(segment.end.x - segment.start.x, segment.end.y - segment.start.y)
        if segment.tool == 2 and segment.motion in (1, 2, 3) and min(segment.start.z, segment.end.z) < top_z - 0.1 and xy_length > 0.1:
            raise EvaluationError("T2 performs lateral subsurface cutting")
        if segment.tool in (1, 2) and segment.motion == 0:
            if xy_length > 0.1 and min(segment.start.z, segment.end.z) < top_z + 1.0:
                raise EvaluationError("unsafe low lateral rapid")
            if segment.end.z < segment.start.z and segment.end.z <= floor_z + DEPTH_TOL:
                raise EvaluationError("rapid plunge reaches the final pocket floor")

    first_t1 = min(segment.line for segment in t1_cutting)
    last_t1 = max(segment.line for segment in t1_cutting)
    if t1_cutting[0].start.z < top_z + 1.0:
        raise EvaluationError("T1 has no safe initial approach")
    if not any(segment.tool == 1 and segment.motion == 0 and segment.line > last_t1 and max(segment.start.z, segment.end.z) >= top_z + 1.0 for segment in program.segments):
        raise EvaluationError("T1 has no safe final retract")
    return {"top_z_mm": top_z, "floor_z_mm": floor_z, "bottom_z_mm": bottom_z, "pocket_coverage": round(coverage, 6), "floor_samples": len(floor_points), "first_t1_line": first_t1}


def validate_source(source: str) -> dict[str, float | int]:
    if len(source.encode("utf-8")) > MAX_BYTES or len(source.splitlines()) > MAX_LINES:
        raise EvaluationError("NC file exceeds evaluator resource limits")
    if not any(re.search(r"\bREVISION_B\b", value) for value in comments(source)):
        raise EvaluationError("REVISION_B must be present in a legal post comment")
    program = parse_program(source)
    if program.tool_changes != [1, 2]:
        raise EvaluationError("tool changes must be exactly T1 then T2")
    valid = []
    for frame in ((0.0, -9.0, -16.0), (16.0, 7.0, 0.0)):
        try:
            valid.append(validate_frame(program, *frame))
        except EvaluationError:
            pass
    if len(valid) != 1:
        raise EvaluationError("program does not match exactly one supported revision_B Z frame")
    return valid[0]


def evaluate_text(source: str) -> bool:
    try:
        validate_source(source)
        return True
    except (EvaluationError, ValueError, OverflowError, MemoryError):
        return False


def validate_outputs(target: Path) -> dict[str, float | int]:
    for name, expected in FORMAL_INPUT_SHA256.items():
        path = target / name
        if not path.is_file() or sha256(path) != expected:
            raise EvaluationError(f"formal input hash mismatch: {name}")
    nc_path = target / NC_NAME
    if not nc_path.is_file() or nc_path.stat().st_size < 200 or nc_path.stat().st_size > MAX_BYTES:
        raise EvaluationError(f"missing or empty {NC_NAME}")
    for path in target.iterdir():
        if path.is_file() and path.suffix.casefold() in {".nc", ".tap", ".gcode"} and re.search(r"(?:TASK[-_]?16|REVISION)[-_]?A(?:\.|[-_])", path.name, re.I):
            raise EvaluationError("revision_A posted output is forbidden")
    return validate_source(nc_path.read_text(encoding="utf-8", errors="strict"))


def main() -> bool:
    try:
        validate_outputs(TARGET)
        return True
    except Exception:
        return False


if __name__ == "__main__":
    print("True" if main() else "False")
    raise SystemExit(0)
