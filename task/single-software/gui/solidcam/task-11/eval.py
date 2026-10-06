from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_TARGET = r"C:\Users\User\Desktop"
TARGET = Path(os.environ.get("EVAL_TARGET_DIR", os.environ.get("OUTPUT_ROOT", DEFAULT_TARGET)))
OUTPUT_NAME = "task-11.nc"

DEPTH_MM = 8.0
DEPTH_TOL_MM = 0.5
GEOMETRY_TOL_MM = 1.0
WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))", re.IGNORECASE)
COMMENT_RE = re.compile(r"\([^()]*\)")


@dataclass
class Record:
    line: int
    motion: int
    start: dict[str, float | None]
    end: dict[str, float | None]
    explicit: dict[str, float]
    tool: int | None
    wcs: str | None
    spindle_on: bool
    feed: float | None


@dataclass
class Program:
    code_lines: list[str] = field(default_factory=list)
    records: list[Record] = field(default_factory=list)
    tools: list[int] = field(default_factory=list)
    units_seen: set[int] = field(default_factory=set)
    distance_modes_seen: set[int] = field(default_factory=set)
    axes_seen: set[str] = field(default_factory=set)
    m_codes_seen: set[int] = field(default_factory=set)
    m30_lines: list[int] = field(default_factory=list)
    has_tool_length_comp: bool = False


@dataclass(frozen=True)
class Pocket:
    bounds: tuple[float, float, float, float]
    center: tuple[float, float]
    long_span: float
    short_span: float
    floor: float


def close(left: float, right: float, tolerance: float = GEOMETRY_TOL_MM) -> bool:
    return abs(float(left) - float(right)) <= tolerance


def code_only(raw: str) -> str:
    return COMMENT_RE.sub(" ", raw.upper()).split(";", 1)[0]


def parse_program(source: str) -> Program:
    program = Program()
    position: dict[str, float | None] = {"x": None, "y": None, "z": None}
    unit_scale: float | None = None
    absolute = True
    wcs: str | None = None
    pending_tool: int | None = None
    current_tool: int | None = None
    modal_motion: int | None = None
    spindle_on = False
    modal_feed: float | None = None

    for line_number, raw in enumerate(source.splitlines()):
        code = code_only(raw)
        program.code_lines.append(code)
        words = [(letter.upper(), float(value)) for letter, value in WORD_RE.findall(code)]
        if not words:
            continue
        g_codes = [int(round(value)) for letter, value in words if letter == "G"]
        m_codes = [int(round(value)) for letter, value in words if letter == "M"]
        program.m_codes_seen.update(m_codes)
        if 20 in g_codes:
            unit_scale = 25.4
            program.units_seen.add(20)
        if 21 in g_codes:
            unit_scale = 1.0
            program.units_seen.add(21)
        if 90 in g_codes:
            absolute = True
            program.distance_modes_seen.add(90)
        if 91 in g_codes:
            absolute = False
            program.distance_modes_seen.add(91)
        for value in g_codes:
            if 54 <= value <= 59:
                wcs = f"G{value}"
        if 43 in g_codes:
            program.has_tool_length_comp = True
        for letter, value in words:
            if letter == "T":
                pending_tool = int(round(value))
            if letter in {"X", "Y", "Z", "A", "B", "C", "U", "V", "W"}:
                program.axes_seen.add(letter)
        if 6 in m_codes:
            if pending_tool is None or pending_tool <= 0:
                raise ValueError("M6 without a valid tool")
            current_tool = pending_tool
            if current_tool not in program.tools:
                program.tools.append(current_tool)
            spindle_on = False
        if 3 in m_codes or 4 in m_codes:
            spindle_on = True
        if 5 in m_codes:
            spindle_on = False
        if 30 in m_codes:
            program.m30_lines.append(line_number)
        if 80 in g_codes:
            modal_motion = None
        explicit_motion = next((value for value in g_codes if value in {0, 1, 2, 3}), None)
        if explicit_motion is not None:
            modal_motion = explicit_motion

        converted: dict[str, float] = {}
        if unit_scale is not None:
            converted = {
                letter.lower(): value * unit_scale
                for letter, value in words
                if letter in {"X", "Y", "Z", "I", "J", "K", "R"}
            }
            feeds = [value * unit_scale for letter, value in words if letter == "F"]
            if feeds:
                modal_feed = feeds[-1]
        machine_return = 28 in g_codes or 30 in g_codes
        start = dict(position)
        if not machine_return and unit_scale is not None:
            for axis in ("x", "y", "z"):
                if axis not in converted:
                    continue
                if absolute:
                    position[axis] = converted[axis]
                elif position[axis] is not None:
                    position[axis] += converted[axis]
                else:
                    raise ValueError("incremental motion before an absolute work position")
        if machine_return or current_tool is None or modal_motion is None:
            continue
        if not any(axis in converted for axis in ("x", "y", "z")) and not (
            modal_motion in {2, 3} and any(axis in converted for axis in ("i", "j", "r"))
        ):
            continue
        program.records.append(
            Record(
                line_number,
                modal_motion,
                start,
                dict(position),
                converted,
                current_tool,
                wcs,
                spindle_on,
                modal_feed,
            )
        )
    return program


def xy(record: Record, which: str) -> tuple[float, float] | None:
    state = record.start if which == "start" else record.end
    if state["x"] is None or state["y"] is None:
        return None
    return float(state["x"]), float(state["y"])


def xy_changed(record: Record) -> bool:
    start, end = xy(record, "start"), xy(record, "end")
    return start is not None and end is not None and math.dist(start, end) > 1.0e-6


def is_cut(record: Record) -> bool:
    return record.motion in {1, 2, 3} and (
        xy_changed(record) or (record.motion in {2, 3} and any(axis in record.explicit for axis in ("i", "j", "r")))
    )


def points(records: list[Record]) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for record in records:
        for which in ("start", "end"):
            point = xy(record, which)
            if point is not None:
                out.append(point)
    return out


def bounds(records: list[Record]) -> tuple[float, float, float, float] | None:
    pts = points(records)
    if not pts:
        return None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), max(xs), min(ys), max(ys)


def floor_groups(program: Program, floor: float) -> list[list[Record]]:
    groups: list[list[Record]] = []
    current: list[Record] = []
    for record in program.records:
        qualifies = is_cut(record) and record.end["z"] is not None and close(record.end["z"], floor, DEPTH_TOL_MM)
        if not qualifies:
            if current:
                groups.append(current)
                current = []
            continue
        current.append(record)
    if current:
        groups.append(current)
    return groups


def pocket_from_group(group: list[Record], floor: float) -> Pocket | None:
    if len(group) < 4:
        return None
    box = bounds(group)
    if box is None:
        return None
    width, height = box[1] - box[0], box[3] - box[2]
    long_span, short_span = max(width, height), min(width, height)
    # For a 30 x 22 mm pocket, subtracting the same cutter diameter and
    # ordinary wall allowance from both axes preserves the 8 mm span delta.
    implied_long = 30.0 - long_span
    implied_short = 22.0 - short_span
    if not (2.0 <= implied_long <= 18.0 and close(implied_long, implied_short, 1.4)):
        return None
    first, last = xy(group[0], "start"), xy(group[-1], "end")
    closed = first is not None and last is not None and math.dist(first, last) <= 1.0
    horizontal = sum(
        xy_changed(record)
        and xy(record, "start") is not None
        and xy(record, "end") is not None
        and close(xy(record, "start")[1], xy(record, "end")[1], 0.15)
        and abs(xy(record, "end")[0] - xy(record, "start")[0]) >= 0.55 * width
        for record in group
    )
    vertical = sum(
        xy_changed(record)
        and xy(record, "start") is not None
        and xy(record, "end") is not None
        and close(xy(record, "start")[0], xy(record, "end")[0], 0.15)
        and abs(xy(record, "end")[1] - xy(record, "start")[1]) >= 0.55 * height
        for record in group
    )
    if not closed or horizontal < 2 or vertical < 2:
        return None
    return Pocket(box, ((box[0] + box[1]) / 2.0, (box[2] + box[3]) / 2.0), long_span, short_span, floor)


def unique_pockets(items: list[Pocket]) -> list[Pocket]:
    result: list[Pocket] = []
    for item in items:
        if any(math.dist(item.center, other.center) <= 1.0 for other in result):
            continue
        result.append(item)
    return result


def pocket_frame(pockets: list[Pocket]) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]] | None:
    if len(pockets) != 2:
        return None
    p1, p2 = sorted(pockets, key=lambda item: item.center)
    delta = (p2.center[0] - p1.center[0], p2.center[1] - p1.center[1])
    distance = math.hypot(*delta)
    if not close(distance, 50.0, 1.1):
        return None
    axis = (delta[0] / distance, delta[1] / distance)
    normal = (-axis[1], axis[0])
    origin = ((p1.center[0] + p2.center[0]) / 2.0, (p1.center[1] + p2.center[1]) / 2.0)
    for pocket in pockets:
        if not close(pocket.long_span, pockets[0].long_span, 0.8) or not close(pocket.short_span, pockets[0].short_span, 0.8):
            return None
        width, height = pocket.bounds[1] - pocket.bounds[0], pocket.bounds[3] - pocket.bounds[2]
        if abs(axis[0]) >= abs(axis[1]):
            if width < height:
                return None
        elif height < width:
            return None
    return origin, axis, normal


def local(point: tuple[float, float], frame) -> tuple[float, float]:
    origin, axis, normal = frame
    delta = (point[0] - origin[0], point[1] - origin[1])
    return delta[0] * axis[0] + delta[1] * axis[1], delta[0] * normal[0] + delta[1] * normal[1]


def point_rect_distance(point: tuple[float, float], rect: tuple[float, float, float, float]) -> float:
    x, y = point
    x1, y1, x2, y2 = rect
    return math.hypot(max(x1 - x, 0.0, x - x2), max(y1 - y, 0.0, y - y2))


def sampled_xy(record: Record) -> list[tuple[float, float]]:
    start, end = xy(record, "start"), xy(record, "end")
    if start is None or end is None:
        return []
    if record.motion not in {2, 3} or "i" not in record.explicit or "j" not in record.explicit:
        return [
            (start[0] + (end[0] - start[0]) * index / 40.0, start[1] + (end[1] - start[1]) * index / 40.0)
            for index in range(41)
        ]
    center = (start[0] + record.explicit["i"], start[1] + record.explicit["j"])
    radius = math.dist(start, center)
    if radius <= 1.0e-6:
        return [start, end]
    a0 = math.atan2(start[1] - center[1], start[0] - center[0])
    a1 = math.atan2(end[1] - center[1], end[0] - center[0])
    if math.dist(start, end) <= 0.05:
        sweep = -2.0 * math.pi if record.motion == 2 else 2.0 * math.pi
    elif record.motion == 2:
        sweep = -((a0 - a1) % (2.0 * math.pi))
    else:
        sweep = (a1 - a0) % (2.0 * math.pi)
    return [(center[0] + radius * math.cos(a0 + sweep * i / 72.0), center[1] + radius * math.sin(a0 + sweep * i / 72.0)) for i in range(73)]


def fixture_clear(program: Program, frame, floor: float) -> bool:
    jaws = ((-70.0, -54.0, 70.0, -46.0), (-70.0, 46.0, 70.0, 54.0))
    low_limit = floor + 15.0  # fixture top plus 3 mm, relative to the 8 mm pocket floor
    for record in program.records:
        z_values = [value for value in (record.start["z"], record.end["z"]) if value is not None]
        if not z_values or min(z_values) > low_limit:
            continue
        for point in sampled_xy(record):
            local_point = local(point, frame)
            if any(point_rect_distance(local_point, rect) < 3.0 - 1.0e-6 for rect in jaws):
                return False
    return True


def safe_cross_pocket_rapids(program: Program, frame) -> bool:
    def pocket_side(point: tuple[float, float]) -> int:
        u, v = local(point, frame)
        if -41.0 <= u <= -9.0 and -12.0 <= v <= 12.0:
            return -1
        if 9.0 <= u <= 41.0 and -12.0 <= v <= 12.0:
            return 1
        return 0

    for record in program.records:
        if record.motion != 0 or not xy_changed(record):
            continue
        start, end = xy(record, "start"), xy(record, "end")
        if start is None or end is None:
            continue
        if pocket_side(start) == pocket_side(end) != 0:
            continue
        z_values = [value for value in (record.start["z"], record.end["z"]) if value is not None]
        if z_values and min(z_values) < 3.0 - 1.0e-6:
            return False
    return True


def depth_levels(program: Program, pocket: Pocket) -> int:
    width = pocket.bounds[1] - pocket.bounds[0]
    height = pocket.bounds[3] - pocket.bounds[2]
    levels = set()
    for record in program.records:
        if not is_cut(record) or record.end["z"] is None:
            continue
        point = xy(record, "end")
        if point is None:
            continue
        if abs(point[0] - pocket.center[0]) <= width / 2.0 + 1.0 and abs(point[1] - pocket.center[1]) <= height / 2.0 + 1.0:
            levels.add(round(float(record.end["z"]), 2))
    return len(levels)


def read_nc(path: Path) -> str | None:
    try:
        if not path.is_file() or not 500 <= path.stat().st_size <= 2_000_000:
            return None
        data = path.read_bytes()
        if b"\x00" in data:
            return None
        source = data.decode("latin-1")
        printable = sum(ch in "\t\r\n" or 32 <= ord(ch) <= 126 for ch in source)
        return source if printable / max(1, len(source)) >= 0.98 else None
    except Exception:
        return None


def validate_nc(path: Path) -> bool:
    source = read_nc(path)
    if source is None:
        return False
    try:
        program = parse_program(source)
    except Exception:
        return False
    if len(program.units_seen) != 1 or 90 not in program.distance_modes_seen:
        return False
    if not 1 <= len(program.tools) <= 3 or not ({0, 1} <= {record.motion for record in program.records}):
        return False
    if program.axes_seen & {"A", "B", "C", "U", "V", "W"}:
        return False
    if not {6, 30} <= program.m_codes_seen or not ({3, 4} & program.m_codes_seen) or not program.has_tool_length_comp:
        return False
    if len(program.m30_lines) != 1:
        return False
    if any(WORD_RE.search(line) for line in program.code_lines[program.m30_lines[0] + 1 :]):
        return False
    cuts = [record for record in program.records if is_cut(record)]
    if len(cuts) < 24 or any(
        not record.spindle_on or record.wcs is None or record.feed is None or record.feed <= 0
        for record in cuts
    ):
        return False
    z_values = [float(record.end["z"]) for record in cuts if record.end["z"] is not None]
    if not z_values:
        return False
    floor = min(z_values)
    if not close(floor, -DEPTH_MM, DEPTH_TOL_MM):
        return False
    pockets = unique_pockets(
        [item for group in floor_groups(program, floor) if (item := pocket_from_group(group, floor)) is not None]
    )
    frame = pocket_frame(pockets)
    if frame is None:
        return False
    if any(depth_levels(program, pocket) < 2 for pocket in pockets):
        return False
    # Every cutting point must stay inside one of the two nominal pocket boxes.
    for record in cuts:
        for point in sampled_xy(record):
            u, v = local(point, frame)
            if not ((-40.5 <= u <= -9.5 or 9.5 <= u <= 40.5) and -11.5 <= v <= 11.5):
                return False
    if not fixture_clear(program, frame, floor):
        return False
    if not safe_cross_pocket_rapids(program, frame):
        return False
    return True


def evaluate() -> bool:
    return validate_nc(TARGET / OUTPUT_NAME)


if __name__ == "__main__":
    try:
        result = evaluate()
    except Exception:
        result = False
    print("True" if result else "False")
