from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from pathlib import Path


TARGET = Path(os.environ.get("EVAL_TARGET_DIR", r"C:\Users\User\Desktop"))
CONTRACTS = {
    "variant_01.nc": {"size": (34.0, 16.0), "bottom": -10.5, "diameter": 7.0, "program": 2701},
    "variant_02.nc": {"size": (38.0, 18.0), "bottom": -11.0, "diameter": 8.0, "program": 2702},
    "variant_03.nc": {"size": (42.0, 20.0), "bottom": -11.5, "diameter": 9.0, "program": 2703},
    "variant_04.nc": {"size": (46.0, 22.0), "bottom": -12.0, "diameter": 10.0, "program": 2704},
    "variant_05.nc": {"size": (50.0, 24.0), "bottom": -12.5, "diameter": 11.0, "program": 2705},
}

MAX_FILE_BYTES = 2_000_000
MAX_BLOCKS = 50_000
MAX_PATH_SEGMENTS = 200_000
SURFACE_TOL = 0.01
DEPTH_TOL = 0.08
FLOOR_TOL = 0.08
WALL_TOL = 0.15
COVERAGE_TOL = 0.20
WORD_RE = re.compile(r"([A-Z])([+-]?(?:\d+(?:\.\d*)?|\.\d+))")
ALLOWED_ADDRESSES = set("GMNOXYZIJRFSTH")
ALLOWED_G_CODES = {0, 1, 2, 3, 17, 20, 21, 28, 40, 43, 49, 53, 54, 80, 90, 91, 94}
ALLOWED_M_CODES = {3, 4, 5, 6, 8, 9, 30}


class EvaluationError(ValueError):
    pass


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class Segment:
    points: tuple[Point, ...]
    motion: int
    tool: int | None
    spindle: float | None
    spindle_on: bool
    feed: float | None
    wcs: int | None
    length_comp: bool
    h_offset: int | None


@dataclass(frozen=True)
class Program:
    program_number: int
    tool_changes: tuple[int, ...]
    segments: tuple[Segment, ...]
    terminated: bool


def integer_code(value: float, label: str) -> int:
    if not math.isfinite(value) or abs(value - round(value)) > 1e-9:
        raise EvaluationError(f"non-integer {label}")
    return int(round(value))


def distance_3d(a: Point, b: Point) -> float:
    return math.dist((a.x, a.y, a.z), (b.x, b.y, b.z))


def strip_comments(source: str) -> list[str]:
    lines: list[str] = []
    depth = 0
    for raw in source.upper().splitlines():
        clean: list[str] = []
        for char in raw:
            if char == ";" and depth == 0:
                break
            if char == "(":
                if depth:
                    raise EvaluationError("nested parenthesis comment")
                depth = 1
            elif char == ")":
                if not depth:
                    raise EvaluationError("unmatched parenthesis comment")
                depth = 0
            elif depth == 0:
                clean.append(char)
        lines.append("".join(clean).strip())
    if depth:
        raise EvaluationError("unterminated parenthesis comment")
    return lines


def parse_words(line: str) -> dict[str, list[float]] | None:
    compact = re.sub(r"\s+", "", line)
    if not compact:
        return None
    if compact == "%":
        return {}
    if "%" in compact or any(char in compact for char in "#[]=/"):
        raise EvaluationError("unsupported executable syntax")
    matches = list(WORD_RE.finditer(compact))
    if not matches or "".join(match.group(0) for match in matches) != compact:
        raise EvaluationError("unknown executable text")
    grouped: dict[str, list[float]] = {}
    for match in matches:
        address = match.group(1)
        if address not in ALLOWED_ADDRESSES:
            raise EvaluationError(f"unknown address {address}")
        value = float(match.group(2))
        if not math.isfinite(value):
            raise EvaluationError("non-finite word")
        grouped.setdefault(address, []).append(value)
    for address, values in grouped.items():
        if address not in {"G", "M"} and len(values) != 1:
            raise EvaluationError(f"duplicate {address} address")
    return grouped


def directional_sweep(start_angle: float, end_angle: float, clockwise: bool, full_circle: bool) -> float:
    if full_circle:
        return -2.0 * math.pi if clockwise else 2.0 * math.pi
    if clockwise:
        magnitude = (start_angle - end_angle) % (2.0 * math.pi)
        return -magnitude
    return (end_angle - start_angle) % (2.0 * math.pi)


def center_from_radius(start: Point, end: Point, radius_word: float, clockwise: bool) -> tuple[float, float, float]:
    dx, dy = end.x - start.x, end.y - start.y
    chord = math.hypot(dx, dy)
    radius = abs(radius_word)
    if chord <= 1e-9 or radius < chord / 2.0 - 0.02:
        raise EvaluationError("invalid R arc")
    half = chord / 2.0
    height = math.sqrt(max(radius * radius - half * half, 0.0))
    mid_x, mid_y = (start.x + end.x) / 2.0, (start.y + end.y) / 2.0
    perp_x, perp_y = -dy / chord, dx / chord
    candidates = [
        (mid_x + height * perp_x, mid_y + height * perp_y),
        (mid_x - height * perp_x, mid_y - height * perp_y),
    ]
    choices: list[tuple[float, float, float]] = []
    for center_x, center_y in candidates:
        a0 = math.atan2(start.y - center_y, start.x - center_x)
        a1 = math.atan2(end.y - center_y, end.x - center_x)
        sweep = directional_sweep(a0, a1, clockwise, False)
        magnitude = abs(sweep)
        wants_minor = radius_word >= 0
        if (wants_minor and magnitude <= math.pi + 1e-7) or (not wants_minor and magnitude >= math.pi - 1e-7):
            choices.append((center_x, center_y, sweep))
    if not choices:
        raise EvaluationError("ambiguous R arc")
    return choices[0]


def arc_points(
    start: Point,
    end: Point,
    clockwise: bool,
    i_word: float | None,
    j_word: float | None,
    radius_word: float | None,
) -> tuple[Point, ...]:
    if radius_word is not None and (i_word is not None or j_word is not None):
        raise EvaluationError("arc mixes I/J and R")
    if radius_word is not None:
        center_x, center_y, sweep = center_from_radius(start, end, radius_word, clockwise)
        radius = abs(radius_word)
        start_angle = math.atan2(start.y - center_y, start.x - center_x)
    else:
        if i_word is None and j_word is None:
            raise EvaluationError("arc lacks I/J or R")
        center_x = start.x + (i_word or 0.0)
        center_y = start.y + (j_word or 0.0)
        radius = math.hypot(start.x - center_x, start.y - center_y)
        end_radius = math.hypot(end.x - center_x, end.y - center_y)
        if radius <= 1e-6 or abs(radius - end_radius) > max(0.05, radius * 0.002):
            raise EvaluationError("invalid I/J arc")
        start_angle = math.atan2(start.y - center_y, start.x - center_x)
        end_angle = math.atan2(end.y - center_y, end.x - center_x)
        full_circle = math.hypot(end.x - start.x, end.y - start.y) <= 1e-7
        sweep = directional_sweep(start_angle, end_angle, clockwise, full_circle)
    if abs(sweep) <= 1e-9:
        raise EvaluationError("zero-length arc")
    count = max(8, int(math.ceil(radius * abs(sweep) / 0.35)))
    if count > MAX_PATH_SEGMENTS:
        raise EvaluationError("arc is too large")
    points = []
    for index in range(count + 1):
        fraction = index / count
        angle = start_angle + sweep * fraction
        points.append(
            Point(
                center_x + radius * math.cos(angle),
                center_y + radius * math.sin(angle),
                start.z + (end.z - start.z) * fraction,
            )
        )
    points[0] = start
    points[-1] = end
    return tuple(points)


def parse_program(source: str) -> Program:
    units: str | None = None
    absolute: bool | None = None
    motion: int | None = None
    plane: int | None = None
    current: dict[str, float | None] = {"X": None, "Y": None, "Z": None}
    pending_tool: int | None = None
    active_tool: int | None = None
    spindle: float | None = None
    spindle_on = False
    feed: float | None = None
    wcs: int | None = None
    length_comp = False
    h_offset: int | None = None
    program_number: int | None = None
    tool_changes: list[int] = []
    segments: list[Segment] = []
    terminated = False
    block_count = 0

    for line in strip_comments(source):
        grouped = parse_words(line)
        if grouped is None or grouped == {}:
            continue
        block_count += 1
        if block_count > MAX_BLOCKS:
            raise EvaluationError("too many blocks")
        if terminated:
            raise EvaluationError("executable code after M30")

        if "O" in grouped:
            if program_number is not None or block_count != 1 or set(grouped) - {"N", "O"}:
                raise EvaluationError("invalid program-number block")
            program_number = integer_code(grouped["O"][0], "O number")
            continue
        if program_number is None:
            raise EvaluationError("executable code before O number")

        g_codes = [integer_code(value, "G code") for value in grouped.get("G", [])]
        m_codes = [integer_code(value, "M code") for value in grouped.get("M", [])]
        if any(code not in ALLOWED_G_CODES for code in g_codes):
            raise EvaluationError("unsupported G code")
        if any(code not in ALLOWED_M_CODES for code in m_codes):
            raise EvaluationError("unsupported M code")
        for family in ({0, 1, 2, 3}, {20, 21}, {90, 91}):
            if len(family.intersection(g_codes)) > 1:
                raise EvaluationError("conflicting modal G codes")
        if len(m_codes) != len(set(m_codes)):
            raise EvaluationError("duplicate M code")

        if 30 in m_codes:
            if m_codes[-1] != 30 or set(grouped) - {"N", "M"} or any(code not in {5, 9, 30} for code in m_codes):
                raise EvaluationError("unsafe M30 block")
            if 5 in m_codes:
                spindle_on = False
            terminated = True
            continue

        if 20 in g_codes:
            units = "inch"
        elif 21 in g_codes:
            units = "mm"
        if 90 in g_codes:
            absolute = True
        elif 91 in g_codes:
            absolute = False
        for code in (0, 1, 2, 3):
            if code in g_codes:
                motion = code
        if 17 in g_codes:
            plane = 17
        if 54 in g_codes:
            wcs = 54
        if "H" in grouped:
            if integer_code(grouped["H"][0], "H offset") != 1 or 43 not in g_codes:
                raise EvaluationError("only G43 H1 is allowed")
        if 43 in g_codes:
            if "H" not in grouped:
                raise EvaluationError("G43 lacks H1")
            length_comp = True
            h_offset = 1
        if 49 in g_codes:
            length_comp = False
            h_offset = None

        factor = 25.4 if units == "inch" else 1.0
        if "T" in grouped:
            pending_tool = integer_code(grouped["T"][0], "tool")
            if pending_tool != 1:
                raise EvaluationError("extra tool")
        if "S" in grouped:
            spindle = grouped["S"][0]
            if spindle <= 0:
                raise EvaluationError("non-positive spindle speed")
        if "F" in grouped:
            if units is None:
                raise EvaluationError("feed before units")
            feed = grouped["F"][0] * factor
            if feed <= 0:
                raise EvaluationError("non-positive feed")
        if 6 in m_codes:
            if pending_tool != 1:
                raise EvaluationError("M6 without T1")
            active_tool = 1
            tool_changes.append(1)
            spindle_on = False
            length_comp = False
            h_offset = None
        if 3 in m_codes or 4 in m_codes:
            if spindle is None or spindle <= 0:
                raise EvaluationError("spindle start lacks positive S")
            spindle_on = True
        if 5 in m_codes:
            spindle_on = False

        axes = {axis for axis in ("X", "Y", "Z") if axis in grouped}
        arc_addresses = {axis for axis in ("I", "J", "R") if axis in grouped}
        if (axes or arc_addresses) and units is None:
            raise EvaluationError("coordinates before units")

        if 28 in g_codes:
            if not axes or arc_addresses or "F" in grouped or {0, 1, 2, 3, 53}.intersection(g_codes):
                raise EvaluationError("invalid G28 reference return")
            for axis in axes:
                current[axis] = None
            continue

        if 53 in g_codes:
            if not axes or arc_addresses or "F" in grouped or 0 not in g_codes:
                raise EvaluationError("G53 cutting or modal motion is forbidden")
            for axis in axes:
                current[axis] = None
            continue

        if not axes and not arc_addresses:
            continue
        if absolute is None:
            raise EvaluationError("motion before G90/G91")
        if motion is None:
            raise EvaluationError("coordinates without motion mode")
        if motion in {0, 1} and arc_addresses:
            raise EvaluationError("arc address on linear motion")
        if motion in {2, 3} and plane != 17:
            raise EvaluationError("arc is not in G17 plane")

        old = dict(current)
        new = dict(current)
        for axis in ("X", "Y", "Z"):
            if axis not in grouped:
                continue
            value = grouped[axis][0] * factor
            if absolute:
                new[axis] = value
            else:
                if old[axis] is None:
                    raise EvaluationError("incremental move from unknown position")
                new[axis] = float(old[axis]) + value
        current = new
        if any(old[axis] is None or new[axis] is None for axis in ("X", "Y", "Z")):
            if motion != 0:
                raise EvaluationError("feed move from unknown position")
            continue

        start = Point(float(old["X"]), float(old["Y"]), float(old["Z"]))
        end = Point(float(new["X"]), float(new["Y"]), float(new["Z"]))
        if motion in {2, 3}:
            i_word = grouped.get("I", [None])[0]
            j_word = grouped.get("J", [None])[0]
            r_word = grouped.get("R", [None])[0]
            points = arc_points(
                start,
                end,
                motion == 2,
                None if i_word is None else i_word * factor,
                None if j_word is None else j_word * factor,
                None if r_word is None else r_word * factor,
            )
        else:
            points = (start, end)
        if len(segments) + len(points) > MAX_PATH_SEGMENTS:
            raise EvaluationError("too many path segments")
        segments.append(
            Segment(
                points=points,
                motion=motion,
                tool=active_tool,
                spindle=spindle,
                spindle_on=spindle_on,
                feed=feed,
                wcs=wcs,
                length_comp=length_comp,
                h_offset=h_offset,
            )
        )

    if program_number is None:
        raise EvaluationError("missing O number")
    return Program(program_number, tuple(tool_changes), tuple(segments), terminated)


def interpolate_at_z(a: Point, b: Point, z_value: float) -> Point:
    if abs(b.z - a.z) <= 1e-12:
        return a
    fraction = (z_value - a.z) / (b.z - a.z)
    return Point(a.x + (b.x - a.x) * fraction, a.y + (b.y - a.y) * fraction, z_value)


def below_surface_portion(a: Point, b: Point) -> tuple[Point, Point] | None:
    threshold = -SURFACE_TOL
    a_below, b_below = a.z <= threshold, b.z <= threshold
    if not a_below and not b_below:
        return None
    if a_below and b_below:
        return a, b
    crossing = interpolate_at_z(a, b, threshold)
    return (a, crossing) if a_below else (crossing, b)


def point_segment_distance_xy(x: float, y: float, a: Point, b: Point) -> float:
    dx, dy = b.x - a.x, b.y - a.y
    length_squared = dx * dx + dy * dy
    if length_squared <= 1e-16:
        return math.hypot(x - a.x, y - a.y)
    fraction = max(0.0, min(1.0, ((x - a.x) * dx + (y - a.y) * dy) / length_squared))
    return math.hypot(x - (a.x + fraction * dx), y - (a.y + fraction * dy))


def rectangle_distance(x: float, y: float, xmin: float, xmax: float, ymin: float, ymax: float) -> float:
    return math.hypot(max(xmin - x, 0.0, x - xmax), max(ymin - y, 0.0, y - ymax))


def grid_values(low: float, high: float, spacing: float) -> list[float]:
    if high < low:
        return []
    count = max(1, int(math.ceil((high - low) / spacing)))
    return [low + (high - low) * index / count for index in range(count + 1)]


def validate_program(program: Program, contract: dict[str, object]) -> None:
    if not program.terminated:
        raise EvaluationError("missing M30")
    if program.program_number != int(contract["program"]):
        raise EvaluationError("wrong exact O number")
    if program.tool_changes != (1,):
        raise EvaluationError("expected exactly one T1/M6")

    width, height = (float(value) for value in contract["size"])
    bottom = float(contract["bottom"])
    radius = float(contract["diameter"]) / 2.0
    x_limit = width / 2.0 - radius
    y_limit = height / 2.0 - radius
    floor_segments: list[tuple[Point, Point]] = []
    saw_cut = False
    saw_safe_rapid = False

    for segment in program.segments:
        if segment.motion == 0 and any(point.z >= 2.0 for point in segment.points):
            saw_safe_rapid = True
        for start, end in zip(segment.points, segment.points[1:]):
            portion = below_surface_portion(start, end)
            if portion is not None:
                for point in portion:
                    if point.z < bottom - DEPTH_TOL:
                        raise EvaluationError("toolpath cuts below the pocket floor")
                    if abs(point.x) > x_limit + WALL_TOL or abs(point.y) > y_limit + WALL_TOL:
                        raise EvaluationError("tool center overcuts a pocket wall")
                if segment.tool != 1 or segment.wcs != 54 or not segment.length_comp or segment.h_offset != 1:
                    raise EvaluationError("subsurface move lacks T1, G54, or G43 H1")
                if segment.motion in {1, 2, 3}:
                    if not segment.spindle_on or segment.spindle is None or segment.spindle <= 0:
                        raise EvaluationError("cut with spindle stopped")
                    if segment.feed is None or segment.feed <= 0:
                        raise EvaluationError("cut lacks positive feed")
                    if distance_3d(start, end) > 1e-6:
                        saw_cut = True
            if (
                segment.motion in {1, 2, 3}
                and abs(start.z - bottom) <= FLOOR_TOL
                and abs(end.z - bottom) <= FLOOR_TOL
                and math.hypot(end.x - start.x, end.y - start.y) > 1e-5
            ):
                floor_segments.append((start, end))

    if not saw_cut or not saw_safe_rapid or not floor_segments:
        raise EvaluationError("incomplete executable pocket program")

    floor_points = [point for pair in floor_segments for point in pair]
    if (
        min(point.x for point in floor_points) > -x_limit + WALL_TOL
        or max(point.x for point in floor_points) < x_limit - WALL_TOL
        or min(point.y for point in floor_points) > -y_limit + WALL_TOL
        or max(point.y for point in floor_points) < y_limit - WALL_TOL
    ):
        raise EvaluationError("floor toolpath does not reach all four walls")

    inset = 0.12
    spacing = min(0.75, max(0.45, radius / 6.0))
    for x in grid_values(-width / 2.0 + inset, width / 2.0 - inset, spacing):
        for y in grid_values(-height / 2.0 + inset, height / 2.0 - inset, spacing):
            if rectangle_distance(x, y, -x_limit, x_limit, -y_limit, y_limit) > radius - inset:
                continue
            if min(point_segment_distance_xy(x, y, start, end) for start, end in floor_segments) > radius + COVERAGE_TOL:
                raise EvaluationError("bottom swept area has uncleared material")


def evaluate_text(source: str, contract: dict[str, object]) -> bool:
    try:
        validate_program(parse_program(source), contract)
        return True
    except (EvaluationError, UnicodeError, ValueError, OverflowError):
        return False


def read_nc(path: Path) -> str:
    raw = path.read_bytes()
    if not raw or len(raw) > MAX_FILE_BYTES or b"\x00" in raw:
        raise EvaluationError("invalid NC file size or encoding")
    return raw.decode("utf-8-sig", errors="strict")


def evaluate_directory(target: Path) -> bool:
    for name, contract in CONTRACTS.items():
        path = target / name
        if not path.is_file() or not evaluate_text(read_nc(path), contract):
            return False
    return True


def main() -> bool:
    return evaluate_directory(TARGET)


if __name__ == "__main__":
    try:
        result = main()
    except Exception:
        result = False
    print("True" if result else "False")
    raise SystemExit(0)
