from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from pathlib import Path


TARGET = Path(os.environ.get("EVAL_TARGET_DIR", r"C:\Users\User\Desktop"))
NC_NAME = "task-02.nc"

TOOL_DIAMETER_MM = 6.0
TOOL_RADIUS_MM = TOOL_DIAMETER_MM / 2.0
REQUIRED_TOOL_NUMBER = 1
SPINDLE_RPM = 8500.0
FEED_MM_MIN = 500.0

# Model-space contract extracted from slot_plate.step. The slot is a capsule:
# a segment from (-16, 0) to (16, 0), dilated by a 4 mm radius.
SLOT_HALF_STRAIGHT_MM = 16.0
SLOT_RADIUS_MM = 4.0
CENTER_RADIUS_MM = SLOT_RADIUS_MM - TOOL_RADIUS_MM

GEOM_TOL_MM = 0.35
DEPTH_TOL_MM = 0.35
OVERTRAVEL_TOL_MM = 0.75
SAFE_CLEARANCE_MM = 1.0

WORD_RE = re.compile(r"([A-Z])([-+]?(?:\d+(?:\.\d*)?|\.\d+))")


@dataclass
class Record:
    index: int
    motion: int
    start: tuple[float | None, float | None, float | None]
    end: tuple[float | None, float | None, float | None]
    i: float | None
    j: float | None
    r: float | None
    tool: int | None
    spindle_on: bool
    spindle: float | None
    feed: float | None
    wcs: int | None
    points: list[tuple[float, float, float]]


@dataclass
class Program:
    records: list[Record]
    saw_units: bool
    saw_distance_mode: bool
    saw_m30: bool
    executable_after_m30: bool
    parse_error: bool


def strip_comments(line: str) -> str:
    out: list[str] = []
    depth = 0
    for char in line:
        if char == ";" and depth == 0:
            break
        if char == "(":
            depth += 1
        elif char == ")" and depth:
            depth -= 1
        elif depth == 0:
            out.append(char)
    return "".join(out).upper()


def words(code: str) -> list[tuple[str, float]]:
    return [(letter, float(value)) for letter, value in WORD_RE.findall(code)]


def close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def point_segment_distance(
    p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]
) -> float:
    px, py = p
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    denom = dx * dx + dy * dy
    if denom <= 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / denom))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def capsule_axis_distance(x: float, y: float) -> float:
    return point_segment_distance(
        (x, y), (-SLOT_HALF_STRAIGHT_MM, 0.0), (SLOT_HALF_STRAIGHT_MM, 0.0)
    )


def line_points(
    start: tuple[float, float, float], end: tuple[float, float, float]
) -> list[tuple[float, float, float]]:
    length = math.dist(start, end)
    count = max(1, int(math.ceil(length / 0.25)))
    return [
        tuple(start[k] + (end[k] - start[k]) * n / count for k in range(3))
        for n in range(count + 1)
    ]


def sweep_angle(start: float, end: float, clockwise: bool) -> float:
    delta = end - start
    if clockwise:
        while delta >= 0:
            delta -= 2 * math.pi
    else:
        while delta <= 0:
            delta += 2 * math.pi
    return delta


def center_from_radius(
    start: tuple[float, float],
    end: tuple[float, float],
    radius_word: float,
    clockwise: bool,
) -> tuple[float, float] | None:
    sx, sy = start
    ex, ey = end
    dx, dy = ex - sx, ey - sy
    chord = math.hypot(dx, dy)
    radius = abs(radius_word)
    if chord <= 1e-9 or chord > 2 * radius + 1e-6:
        return None
    mx, my = (sx + ex) / 2, (sy + ey) / 2
    h = math.sqrt(max(0.0, radius * radius - (chord / 2) ** 2))
    nx, ny = -dy / chord, dx / chord
    candidates = [(mx + h * nx, my + h * ny), (mx - h * nx, my - h * ny)]
    wanted_major = radius_word < 0
    for cx, cy in candidates:
        a0 = math.atan2(sy - cy, sx - cx)
        a1 = math.atan2(ey - cy, ex - cx)
        delta = sweep_angle(a0, a1, clockwise)
        if (abs(delta) > math.pi + 1e-7) == wanted_major:
            return cx, cy
    return candidates[0]


def arc_points(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    clockwise: bool,
    i: float | None,
    j: float | None,
    radius_word: float | None,
) -> list[tuple[float, float, float]] | None:
    sx, sy, sz = start
    ex, ey, ez = end
    if i is not None or j is not None:
        cx, cy = sx + (i or 0.0), sy + (j or 0.0)
    elif radius_word is not None:
        center = center_from_radius((sx, sy), (ex, ey), radius_word, clockwise)
        if center is None:
            return None
        cx, cy = center
    else:
        return None
    radius = math.hypot(sx - cx, sy - cy)
    if radius <= 1e-9 or not close(math.hypot(ex - cx, ey - cy), radius, 0.05):
        return None
    a0 = math.atan2(sy - cy, sx - cx)
    a1 = math.atan2(ey - cy, ex - cx)
    if close(sx, ex, 1e-8) and close(sy, ey, 1e-8):
        delta = -2 * math.pi if clockwise else 2 * math.pi
    else:
        delta = sweep_angle(a0, a1, clockwise)
    count = max(8, int(math.ceil(abs(delta) * radius / 0.25)))
    return [
        (
            cx + radius * math.cos(a0 + delta * n / count),
            cy + radius * math.sin(a0 + delta * n / count),
            sz + (ez - sz) * n / count,
        )
        for n in range(count + 1)
    ]


def parse_nc(src: str) -> Program:
    records: list[Record] = []
    x = y = z = None
    unit_scale: float | None = None
    absolute: bool | None = None
    motion: int | None = None
    pending_tool: int | None = None
    active_tool: int | None = None
    spindle_on = False
    spindle: float | None = None
    feed: float | None = None
    wcs: int | None = None
    saw_units = saw_distance = saw_m30 = after_m30 = parse_error = False

    for index, raw in enumerate(src.splitlines()):
        code = strip_comments(raw)
        line_words = words(code)
        if not line_words:
            continue
        if saw_m30:
            if any(letter not in {"N", "O"} for letter, _ in line_words):
                after_m30 = True
            continue

        g_values = [value for letter, value in line_words if letter == "G"]
        m_values = [value for letter, value in line_words if letter == "M"]
        line_has_m30 = any(close(value, 30, 1e-9) for value in m_values)
        for value in g_values:
            if close(value, 20, 1e-9):
                unit_scale = 25.4
                saw_units = True
            elif close(value, 21, 1e-9):
                unit_scale = 1.0
                saw_units = True
            elif close(value, 90, 1e-9):
                absolute = True
                saw_distance = True
            elif close(value, 91, 1e-9):
                absolute = False
                saw_distance = True
            elif any(close(value, candidate, 1e-9) for candidate in (0, 1, 2, 3)):
                motion = int(round(value))
            elif any(close(value, candidate, 1e-9) for candidate in range(54, 60)):
                wcs = int(round(value))

        for letter, value in line_words:
            if letter == "T" and value >= 0 and close(value, round(value), 1e-9):
                pending_tool = int(round(value))
            elif letter == "S":
                spindle = value
            elif letter == "F":
                if unit_scale is None:
                    parse_error = True
                else:
                    feed = value * unit_scale

        for value in m_values:
            if close(value, 6, 1e-9):
                active_tool = pending_tool
            elif close(value, 3, 1e-9) or close(value, 4, 1e-9):
                spindle_on = True
            elif close(value, 5, 1e-9):
                spindle_on = False

        axis_words = {
            letter: value
            for letter, value in line_words
            if letter in {"X", "Y", "Z", "I", "J", "R"}
        }
        if line_has_m30 and (
            any(axis in axis_words for axis in ("X", "Y", "Z"))
            or any(any(close(value, candidate, 1e-9) for candidate in (0, 1, 2, 3)) for value in g_values)
        ):
            parse_error = True
        if motion is not None and any(axis in axis_words for axis in ("X", "Y", "Z")):
            if unit_scale is None or absolute is None:
                parse_error = True
            else:
                start = (x, y, z)
                values = {axis: value * unit_scale for axis, value in axis_words.items()}
                old = {"X": x, "Y": y, "Z": z}
                new: dict[str, float | None] = {}
                for axis in ("X", "Y", "Z"):
                    if axis not in values:
                        new[axis] = old[axis]
                    elif absolute:
                        new[axis] = values[axis]
                    elif old[axis] is None:
                        parse_error = True
                        new[axis] = None
                    else:
                        new[axis] = old[axis] + values[axis]
                x, y, z = new["X"], new["Y"], new["Z"]
                end = (x, y, z)
                points: list[tuple[float, float, float]] = []
                if all(value is not None for value in start + end):
                    full_start = (float(start[0]), float(start[1]), float(start[2]))
                    full_end = (float(end[0]), float(end[1]), float(end[2]))
                    if motion in {0, 1}:
                        points = line_points(full_start, full_end)
                    elif motion in {2, 3}:
                        arc = arc_points(
                            full_start,
                            full_end,
                            motion == 2,
                            values.get("I"),
                            values.get("J"),
                            values.get("R"),
                        )
                        if arc is None:
                            parse_error = True
                        else:
                            points = arc
                records.append(
                    Record(
                        index=index,
                        motion=motion,
                        start=start,
                        end=end,
                        i=values.get("I"),
                        j=values.get("J"),
                        r=values.get("R"),
                        tool=active_tool,
                        spindle_on=spindle_on,
                        spindle=spindle,
                        feed=feed,
                        wcs=wcs,
                        points=points,
                    )
                )

        if line_has_m30:
            saw_m30 = True

    return Program(records, saw_units, saw_distance, saw_m30, after_m30, parse_error)


def xy_length(points: list[tuple[float, float, float]]) -> float:
    return sum(
        math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:])
    )


def path_distance(point: tuple[float, float], paths: list[list[tuple[float, float, float]]]) -> float:
    best = math.inf
    for path in paths:
        for a, b in zip(path, path[1:]):
            best = min(best, point_segment_distance(point, (a[0], a[1]), (b[0], b[1])))
    return best


def target_samples(step: float = 0.5) -> list[tuple[float, float]]:
    out = []
    x = -20.0
    while x <= 20.0 + 1e-9:
        y = -4.0
        while y <= 4.0 + 1e-9:
            if capsule_axis_distance(x, y) <= SLOT_RADIUS_MM + 1e-9:
                out.append((x, y))
            y += step
        x += step
    return out


def validate_frame(program: Program, top_z: float, bottom_z: float) -> bool:
    records = program.records
    final_records = [
        record
        for record in records
        if record.motion in {1, 2, 3}
        and record.spindle_on
        and record.tool is not None
        and record.feed is not None
        and record.points
        and xy_length(record.points) > 0.02
        and all(abs(point[2] - bottom_z) <= DEPTH_TOL_MM for point in record.points)
    ]
    if len(final_records) < 3:
        return False
    if any(record.spindle is None or not close(record.spindle, SPINDLE_RPM, 5.0) for record in final_records):
        return False
    if any(record.feed is None or not close(record.feed, FEED_MM_MIN, 25.0) for record in final_records):
        return False
    tools = {record.tool for record in final_records}
    if tools != {REQUIRED_TOOL_NUMBER}:
        return False
    work_offsets = {record.wcs for record in final_records}
    if work_offsets != {54}:
        return False

    # No candidate-writable transform is trusted. XY must use the centered,
    # model-global slot frame stated by the task contract.
    final_paths = [record.points for record in final_records]
    if sum(xy_length(path) for path in final_paths) < 50.0:
        return False

    material_paths = []
    for record in records:
        if (
            record.motion not in {1, 2, 3}
            or not record.spindle_on
            or record.feed is None
            or not record.points
            or xy_length(record.points) <= 0.02
        ):
            continue
        if min(point[2] for point in record.points) < bottom_z - OVERTRAVEL_TOL_MM:
            return False
        if min(point[2] for point in record.points) <= top_z + DEPTH_TOL_MM:
            if (
                record.tool != REQUIRED_TOOL_NUMBER
                or record.spindle is None
                or not close(record.spindle, SPINDLE_RPM, 5.0)
                or not close(record.feed, FEED_MM_MIN, 25.0)
                or record.wcs != 54
            ):
                return False
            material_paths.append(record.points)
    if not material_paths:
        return False
    for path in material_paths:
        if any(capsule_axis_distance(x, y) > CENTER_RADIUS_MM + GEOM_TOL_MM for x, y, _ in path):
            return False

    for sample in target_samples():
        if path_distance(sample, final_paths) > TOOL_RADIUS_MM + GEOM_TOL_MM:
            return False

    final_indexes = [record.index for record in final_records]
    first_cut, last_cut = min(final_indexes), max(final_indexes)
    safe_z = top_z + SAFE_CLEARANCE_MM
    if not any(record.index < first_cut and record.motion == 0 and record.end[2] is not None and record.end[2] >= safe_z for record in records):
        return False
    if not any(record.index > last_cut and record.end[2] is not None and record.end[2] >= safe_z for record in records):
        return False
    if not any(
        record.index < first_cut
        and record.motion in {1, 2, 3}
        and record.spindle_on
        and record.feed is not None
        and record.start[2] is not None
        and record.end[2] is not None
        and record.end[2] < record.start[2] - 0.2
        for record in records
    ):
        return False
    return True


def validate_nc(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 40 or path.stat().st_size > 2_000_000:
        return False
    src = path.read_text(encoding="utf-8", errors="strict")
    program = parse_nc(src)
    if (
        program.parse_error
        or not program.saw_units
        or not program.saw_distance_mode
        or not program.saw_m30
        or program.executable_after_m30
    ):
        return False
    # The task contract fixes G54 at model [0, 0, 10] with tool axis -Z.
    # Posted XY stays centered and the slot bottom is therefore local Z=-10.
    return validate_frame(program, top_z=0.0, bottom_z=-10.0)


def evaluate() -> bool:
    # Deliberately ignore candidate-writable audit/manifest files. Trusted
    # SOLIDWORKS CAM provenance must be enforced by a host-side gate that binds
    # software execution, setup, postprocessor, input hash, and this NC hash.
    return validate_nc(TARGET / NC_NAME)


if __name__ == "__main__":
    try:
        result = evaluate()
    except Exception:
        result = False
    print("True" if result else "False")
