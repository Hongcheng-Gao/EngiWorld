from __future__ import annotations

import math
import os
import re
import statistics
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_TARGET = r"C:\Users\User\Desktop"
TARGET = Path(os.environ.get("EVAL_TARGET_DIR", os.environ.get("OUTPUT_ROOT", DEFAULT_TARGET)))
OUTPUT_NAME = "task-17.nc"

FORBIDDEN_EXTENSIONS = {
    ".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".ps1", ".vbs", ".js", ".mjs", ".ts", ".rb", ".lua", ".tcl", ".ahk", ".scr",
}
FIXTURES = (
    (69.0, 39.0, 87.0, 57.0),
    (-87.0, 39.0, -69.0, 57.0),
    (69.0, -57.0, 87.0, -39.0),
    (-87.0, -57.0, -69.0, -39.0),
)
MODEL_TOP_Z = 18.0
FIXTURE_CHECK_MODEL_Z = 20.0
FIXTURE_CHECK_LOCAL_Z = FIXTURE_CHECK_MODEL_Z - MODEL_TOP_Z
EPS = 1e-7


@dataclass
class Motion:
    line: int
    code: int
    start: tuple[float | None, float | None, float | None]
    end: tuple[float | None, float | None, float | None]
    tool: int | None
    wcs: str | None
    feed: float | None
    speed: float | None
    spindle: int | None
    length_comp: bool
    h: int | None
    home_safe: bool
    center: tuple[float, float] | None = None
    sweep: float | None = None


@dataclass
class Parsed:
    motions: list[Motion] = field(default_factory=list)
    tool_changes: list[int] = field(default_factory=list)
    tool_diameter_hints: dict[int, list[float]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    m30_line: int | None = None


@dataclass
class Loop:
    tool: int
    z: float
    motions: list[Motion]
    points: list[tuple[float, float]]
    closed: bool
    bounds: tuple[float, float, float, float]


@dataclass
class Frame:
    cx: float
    cy: float
    swap: bool
    top_z: float
    profile_tool: int
    profile_radius: float
    pocket_tool: int | None = None
    pocket_radius: float | None = None

    def xy(self, point: tuple[float, float]) -> tuple[float, float]:
        x, y = point[0] - self.cx, point[1] - self.cy
        return (y, x) if self.swap else (x, y)


def _close(a: float, b: float, tolerance: float) -> bool:
    return abs(a - b) <= tolerance


def _strip_comments(line: str) -> str:
    line = re.sub(r"\([^)]*\)", " ", line)
    return line.split(";", 1)[0].upper()


def _comment_text(line: str) -> str:
    parts = re.findall(r"\(([^)]*)\)", line)
    if ";" in line:
        parts.append(line.split(";", 1)[1])
    return " ".join(parts).upper()


def _diameter_hint(comment: str, unit_scale: float) -> float | None:
    match = re.search(r"(?<!\d)(\d+)\s*/\s*(\d+)\s*(?:IN(?:CH)?|EM\b|END\s*MILL)", comment)
    if match and int(match.group(2)):
        return 25.4 * int(match.group(1)) / int(match.group(2))
    match = re.search(r"(?<![\d.])(\d+(?:\.\d+)?)\s*MM\b", comment)
    if match:
        value = float(match.group(1))
        return value if 0.5 <= value <= 40.0 else None
    match = re.search(r"(?<![\d.])(0?\.\d+|\d+\.\d+)\s*(?:IN(?:CH)?|EM\b)", comment)
    if match:
        value = float(match.group(1)) * 25.4
        return value if 0.5 <= value <= 40.0 else None
    return None


def _words(code: str) -> list[tuple[str, float]]:
    return [
        (letter, float(value))
        for letter, value in re.findall(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))", code)
    ]


def _arc_from_r(
    start: tuple[float, float], end: tuple[float, float], radius_word: float, clockwise: bool
) -> tuple[tuple[float, float], float] | None:
    sx, sy = start
    ex, ey = end
    dx, dy = ex - sx, ey - sy
    chord = math.hypot(dx, dy)
    radius = abs(radius_word)
    if chord <= EPS or chord > 2.0 * radius + 1e-5:
        return None
    mx, my = (sx + ex) / 2.0, (sy + ey) / 2.0
    height = math.sqrt(max(0.0, radius * radius - (chord / 2.0) ** 2))
    ux, uy = -dy / chord, dx / chord
    candidates = ((mx + ux * height, my + uy * height), (mx - ux * height, my - uy * height))
    choices = []
    for center in candidates:
        a0 = math.atan2(sy - center[1], sx - center[0])
        a1 = math.atan2(ey - center[1], ex - center[0])
        sweep = _directed_sweep(a0, a1, clockwise, full=False)
        choices.append((center, sweep))
    want_major = radius_word < 0
    for center, sweep in choices:
        if (abs(sweep) > math.pi + 1e-6) == want_major:
            return center, sweep
    return choices[0]


def _directed_sweep(a0: float, a1: float, clockwise: bool, full: bool) -> float:
    if full:
        return -2.0 * math.pi if clockwise else 2.0 * math.pi
    delta = (a1 - a0) % (2.0 * math.pi)
    if clockwise:
        return delta - 2.0 * math.pi if delta > EPS else 0.0
    return delta


def parse_nc(src: str) -> Parsed:
    parsed = Parsed()
    state = {
        "x": None, "y": None, "z": None, "motion": None, "unit": 1.0, "absolute": True,
        "tool_pending": None, "tool": None, "wcs": None, "feed": None, "speed": None,
        "spindle": None, "length_comp": False, "h": None, "home_safe": False,
    }
    pending_diameters: list[float] = []
    m30_seen = False
    for index, raw in enumerate(src.splitlines(), 1):
        comment = _comment_text(raw)
        hint = _diameter_hint(comment, float(state["unit"]))
        if hint is not None:
            pending_diameters.append(hint)
        code = _strip_comments(raw)
        words = _words(code)
        if not words:
            continue
        stripped = re.sub(r"\bN\s*[+-]?(?:\d+(?:\.\d*)?|\.\d+)", " ", code)
        stripped = stripped.replace("%", " ").strip()
        if m30_seen:
            if stripped:
                parsed.errors.append(f"executable content after M30 on line {index}")
            continue
        if "#" in code or re.search(r"\bM0?(?:98|99)\b", code):
            parsed.errors.append(f"unsupported macro/subprogram on line {index}")
        g_values = [int(round(value)) for letter, value in words if letter == "G"]
        m_values = [int(round(value)) for letter, value in words if letter == "M"]
        values: dict[str, float] = {}
        for letter, value in words:
            values[letter] = value
        if 20 in g_values:
            state["unit"] = 25.4
        if 21 in g_values:
            state["unit"] = 1.0
        if 90 in g_values:
            state["absolute"] = True
        if 91 in g_values:
            state["absolute"] = False
        if any(g in g_values for g in (52, 53, 68, 69, 92)) or 10 in g_values:
            parsed.errors.append(f"unsupported coordinate override on line {index}")
        for g in g_values:
            if 54 <= g <= 59:
                state["wcs"] = f"G{g}"
        if "T" in values:
            state["tool_pending"] = int(round(values["T"]))
        if 6 in m_values:
            tool = state["tool_pending"]
            if tool is None or tool <= 0:
                parsed.errors.append(f"M6 without a positive T word on line {index}")
            else:
                state["tool"] = tool
                parsed.tool_changes.append(tool)
                if pending_diameters:
                    parsed.tool_diameter_hints.setdefault(tool, []).append(pending_diameters[-1])
                pending_diameters.clear()
            state["length_comp"], state["h"] = False, None
        if "S" in values:
            state["speed"] = values["S"]
        if "F" in values:
            state["feed"] = values["F"] * float(state["unit"])
        if 3 in m_values:
            state["spindle"] = 3
        if 4 in m_values:
            state["spindle"] = 4
        if 5 in m_values:
            state["spindle"] = None
        if 43 in g_values:
            state["length_comp"] = True
            state["h"] = int(round(values["H"])) if "H" in values else None
        if 49 in g_values:
            state["length_comp"], state["h"] = False, None
        if 80 in g_values:
            state["motion"] = None
        explicit_motion = next((g for g in g_values if g in (0, 1, 2, 3)), None)
        if explicit_motion is not None:
            state["motion"] = explicit_motion
        if 28 in g_values:
            if "Z" in values:
                state["home_safe"] = True
            for axis in "XYZ":
                if axis in values:
                    state[axis.lower()] = None
            if 30 in m_values:
                parsed.errors.append(f"G28 and M30 share line {index}")
            continue
        axes = {axis: values[axis] * float(state["unit"]) for axis in "XYZ" if axis in values}
        if state["motion"] is not None and axes:
            start = (state["x"], state["y"], state["z"])
            end_values = []
            for axis in "XYZ":
                current = state[axis.lower()]
                if axis not in axes:
                    end_values.append(current)
                elif bool(state["absolute"]):
                    end_values.append(axes[axis])
                else:
                    end_values.append((0.0 if current is None else float(current)) + axes[axis])
            end = tuple(end_values)
            center = None
            sweep = None
            if state["motion"] in (2, 3):
                if None in start[:2] or None in end[:2]:
                    parsed.errors.append(f"arc lacks XY start/end on line {index}")
                else:
                    clockwise = state["motion"] == 2
                    if "I" in values or "J" in values:
                        center = (
                            float(start[0]) + values.get("I", 0.0) * float(state["unit"]),
                            float(start[1]) + values.get("J", 0.0) * float(state["unit"]),
                        )
                        a0 = math.atan2(float(start[1]) - center[1], float(start[0]) - center[0])
                        a1 = math.atan2(float(end[1]) - center[1], float(end[0]) - center[0])
                        full = math.hypot(float(start[0]) - float(end[0]), float(start[1]) - float(end[1])) <= 1e-6
                        sweep = _directed_sweep(a0, a1, clockwise, full)
                    elif "R" in values:
                        result = _arc_from_r(
                            (float(start[0]), float(start[1])),
                            (float(end[0]), float(end[1])),
                            values["R"] * float(state["unit"]), clockwise,
                        )
                        if result is not None:
                            center, sweep = result
                    if center is None or sweep is None:
                        parsed.errors.append(f"unsupported or invalid arc on line {index}")
            motion = Motion(
                line=index, code=int(state["motion"]), start=start, end=end,
                tool=state["tool"], wcs=state["wcs"], feed=state["feed"], speed=state["speed"],
                spindle=state["spindle"], length_comp=bool(state["length_comp"]), h=state["h"],
                home_safe=bool(state["home_safe"]), center=center, sweep=sweep,
            )
            parsed.motions.append(motion)
            state["x"], state["y"], state["z"] = end
            if "Z" in axes:
                state["home_safe"] = False
        if 30 in m_values:
            parsed.m30_line = index
            m30_seen = True
    if parsed.m30_line is None:
        parsed.errors.append("missing M30")
    return parsed


def _xy_changed(motion: Motion) -> bool:
    if None in motion.start[:2] or None in motion.end[:2]:
        return False
    if motion.code in (2, 3) and motion.sweep is not None and abs(motion.sweep) > 1e-6:
        return True
    return math.hypot(float(motion.end[0]) - float(motion.start[0]), float(motion.end[1]) - float(motion.start[1])) > 1e-6


def _point_at(motion: Motion, t: float) -> tuple[float, float, float | None]:
    if motion.code in (2, 3) and motion.center is not None and motion.sweep is not None:
        sx, sy = float(motion.start[0]), float(motion.start[1])
        a0 = math.atan2(sy - motion.center[1], sx - motion.center[0])
        radius = math.hypot(sx - motion.center[0], sy - motion.center[1])
        angle = a0 + motion.sweep * t
        x, y = motion.center[0] + radius * math.cos(angle), motion.center[1] + radius * math.sin(angle)
    else:
        x = float(motion.start[0]) + (float(motion.end[0]) - float(motion.start[0])) * t
        y = float(motion.start[1]) + (float(motion.end[1]) - float(motion.start[1])) * t
    z = None
    if motion.start[2] is not None and motion.end[2] is not None:
        z = float(motion.start[2]) + (float(motion.end[2]) - float(motion.start[2])) * t
    return x, y, z


def _motion_points(motion: Motion, max_angle_deg: float = 4.0) -> list[tuple[float, float]]:
    if None in motion.start[:2] or None in motion.end[:2]:
        return []
    steps = 1
    if motion.code in (2, 3) and motion.sweep is not None:
        steps = max(2, int(math.ceil(abs(motion.sweep) / math.radians(max_angle_deg))))
    return [(_point_at(motion, i / steps)[0], _point_at(motion, i / steps)[1]) for i in range(steps + 1)]


def _cut_loops(parsed: Parsed) -> list[Loop]:
    loops: list[Loop] = []
    current: list[Motion] = []
    current_tool = None
    current_z = None

    def flush() -> None:
        nonlocal current, current_tool, current_z
        if current and current_tool is not None and current_z is not None:
            points = [(float(current[0].start[0]), float(current[0].start[1]))]
            for motion in current:
                points.extend(_motion_points(motion)[1:])
            xs, ys = [p[0] for p in points], [p[1] for p in points]
            closed = math.hypot(points[0][0] - points[-1][0], points[0][1] - points[-1][1]) <= 1.0
            loops.append(Loop(current_tool, current_z, list(current), points, closed, (min(xs), min(ys), max(xs), max(ys))))
        current, current_tool, current_z = [], None, None

    for motion in parsed.motions:
        qualifies = motion.code in (1, 2, 3) and _xy_changed(motion) and motion.end[2] is not None
        z = float(motion.end[2]) if motion.end[2] is not None else None
        if not qualifies or (current and (motion.tool != current_tool or abs(z - float(current_z)) > 0.3)):
            flush()
        if qualifies:
            if not current:
                current_tool, current_z = motion.tool, z
            current.append(motion)
    flush()
    return loops


def _median(values: list[float]) -> float:
    return float(statistics.median(values))


def _profile_edges_complete(loop: Loop, radius: float) -> bool:
    cx = (loop.bounds[0] + loop.bounds[2]) / 2.0
    cy = (loop.bounds[1] + loop.bounds[3]) / 2.0
    swap = (loop.bounds[2] - loop.bounds[0]) < (loop.bounds[3] - loop.bounds[1])
    local = Frame(cx, cy, swap, 0.0, loop.tool, radius)
    tx, ty = 60.0 + radius, 40.0 + radius
    probes = []
    for fraction in (-0.75, -0.25, 0.25, 0.75):
        probes.extend(((fraction * 60.0, -ty), (fraction * 60.0, ty)))
        probes.extend(((-tx, fraction * 40.0), (tx, fraction * 40.0)))
    return all(_distance_to_motions(point, loop.motions, local) <= 1.5 for point in probes)


def _identify_frame(parsed: Parsed, reasons: list[str]) -> tuple[Frame | None, list[Loop]]:
    loops = _cut_loops(parsed)
    candidates = []
    for loop in loops:
        if not loop.closed or loop.tool is None:
            continue
        xmin, ymin, xmax, ymax = loop.bounds
        width, height = xmax - xmin, ymax - ymin
        long_side, short_side = max(width, height), min(width, height)
        if 118.0 <= long_side <= 145.0 and 78.0 <= short_side <= 105.0:
            radius_long, radius_short = (long_side - 120.0) / 2.0, (short_side - 80.0) / 2.0
            if 0.4 <= radius_long <= 12.0 and abs(radius_long - radius_short) <= 1.5:
                radius = (radius_long + radius_short) / 2.0
                if _profile_edges_complete(loop, radius):
                    candidates.append((loop, radius, width < height))
    by_tool: dict[int, list[tuple[Loop, float, bool]]] = {}
    for item in candidates:
        by_tool.setdefault(item[0].tool, []).append(item)
    if not by_tool:
        reasons.append("no multi-layer 120 x 80 outside-profile loops")
        return None, loops
    profile_tool, rows = max(by_tool.items(), key=lambda item: len(item[1]))
    if len(rows) < 4:
        reasons.append("outside profile has fewer than four closed layers")
        return None, loops
    swaps = [row[2] for row in rows]
    swap = sum(swaps) > len(swaps) / 2
    selected = [row for row in rows if row[2] == swap]
    centers_x = [(row[0].bounds[0] + row[0].bounds[2]) / 2.0 for row in selected]
    centers_y = [(row[0].bounds[1] + row[0].bounds[3]) / 2.0 for row in selected]
    radii = [row[1] for row in selected]
    depths = sorted({round(row[0].z, 3) for row in selected})
    if len(depths) < 4:
        reasons.append("outside profile lacks four distinct depth levels")
        return None, loops
    if depths[-1] - depths[0] < 14.0:
        reasons.append("outside profile does not span the 18 mm workpiece depth")
        return None, loops
    if any(b - a > 4.5 for a, b in zip(depths, depths[1:])):
        reasons.append("outside-profile layer step exceeds 4.5 mm")
        return None, loops
    radius = _median(radii)
    top_z = depths[0] + 18.0
    if not (-4.5 <= depths[-1] - top_z <= 0.5):
        reasons.append("outside profile does not begin near the workpiece top")
        return None, loops
    frame = Frame(_median(centers_x), _median(centers_y), swap, top_z, profile_tool, radius)
    return frame, loops


def _local_bounds(loop: Loop, frame: Frame) -> tuple[float, float, float, float]:
    points = [frame.xy(point) for point in loop.points]
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _tool_hint(parsed: Parsed, tool: int) -> float | None:
    values = parsed.tool_diameter_hints.get(tool, [])
    return _median(values) if values else None


def _distance_point_segment(point: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    px, py = point
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    denom = dx * dx + dy * dy
    if denom <= EPS:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / denom))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _distance_to_motions(point: tuple[float, float], motions: list[Motion], frame: Frame) -> float:
    best = float("inf")
    for motion in motions:
        points = [frame.xy(value) for value in _motion_points(motion, 1.0)]
        for a, b in zip(points, points[1:]):
            best = min(best, _distance_point_segment(point, a, b))
    return best


def _identify_pocket(parsed: Parsed, loops: list[Loop], frame: Frame, reasons: list[str]) -> bool:
    by_tool: dict[int, list[tuple[Loop, float]]] = {}
    for loop in loops:
        if loop.tool is None or loop.tool == frame.profile_tool:
            continue
        xmin, ymin, xmax, ymax = _local_bounds(loop, frame)
        width, height = xmax - xmin, ymax - ymin
        radius_x, radius_y = (44.0 - width) / 2.0, (28.0 - height) / 2.0
        center = ((xmin + xmax) / 2.0, (ymin + ymax) / 2.0)
        if 1.0 <= radius_x <= 10.0 and abs(radius_x - radius_y) <= 1.5 and math.hypot(*center) <= 2.0:
            by_tool.setdefault(loop.tool, []).append((loop, (radius_x + radius_y) / 2.0))
    if not by_tool:
        reasons.append("no centered 44 x 28 pocket-clearing loops")
        return False
    tool, rows = max(by_tool.items(), key=lambda item: len(item[1]))
    depths = sorted({round(row[0].z - frame.top_z, 3) for row in rows})
    if len(depths) < 2 or depths[-1] - depths[0] < 4.0:
        reasons.append("pocket lacks multiple meaningful depth levels")
        return False
    if not (-13.8 <= depths[0] <= -12.2):
        reasons.append("pocket does not reach the 13 mm floor")
        return False
    radius = _median([row[1] for row in rows])
    hint = _tool_hint(parsed, tool)
    if hint is not None and abs(hint / 2.0 - radius) > 1.5:
        reasons.append("pocket tool diameter comment conflicts with swept geometry")
        return False
    frame.pocket_tool = tool
    frame.pocket_radius = max(radius, hint / 2.0 if hint is not None else 0.0)
    bottom = [row[0] for row in rows if row[0].z - frame.top_z <= -12.2]
    bottom_motions = [motion for loop in bottom for motion in loop.motions]
    grid = [(x, y) for x in (-16.0, -8.0, 0.0, 8.0, 16.0) for y in (-8.0, 0.0, 8.0)]
    if any(_distance_to_motions(point, bottom_motions, frame) > frame.pocket_radius + 1.0 for point in grid):
        reasons.append("bottom-level pocket paths do not clear the central 44 x 28 area")
        return False
    return True


def _point_in_rect(point: tuple[float, float], rect: tuple[float, float, float, float]) -> bool:
    return rect[0] - EPS <= point[0] <= rect[2] + EPS and rect[1] - EPS <= point[1] <= rect[3] + EPS


def _line_rect_hit(a: tuple[float, float], b: tuple[float, float], rect: tuple[float, float, float, float]) -> bool:
    t0, t1 = 0.0, 1.0
    dx, dy = b[0] - a[0], b[1] - a[1]
    for p, q in ((-dx, a[0] - rect[0]), (dx, rect[2] - a[0]), (-dy, a[1] - rect[1]), (dy, rect[3] - a[1])):
        if abs(p) <= EPS:
            if q < 0:
                return False
            continue
        value = q / p
        if p < 0:
            t0 = max(t0, value)
        else:
            t1 = min(t1, value)
        if t0 > t1:
            return False
    return True


def _safe_segment_hit(motion: Motion, frame: Frame, rect: tuple[float, float, float, float]) -> bool:
    if None in motion.start[:2] or None in motion.end[:2]:
        return False
    z0 = None if motion.start[2] is None else float(motion.start[2]) - frame.top_z
    z1 = None if motion.end[2] is None else float(motion.end[2]) - frame.top_z
    if z0 is None or z1 is None:
        return not (motion.code == 0 and motion.home_safe)
    if min(z0, z1) >= FIXTURE_CHECK_LOCAL_Z - EPS:
        return False
    low_start, low_end = 0.0, 1.0
    if z0 >= FIXTURE_CHECK_LOCAL_Z and z1 < FIXTURE_CHECK_LOCAL_Z:
        low_start = (FIXTURE_CHECK_LOCAL_Z - z0) / (z1 - z0)
    elif z0 < FIXTURE_CHECK_LOCAL_Z and z1 >= FIXTURE_CHECK_LOCAL_Z:
        low_end = (FIXTURE_CHECK_LOCAL_Z - z0) / (z1 - z0)
    if motion.code in (0, 1):
        a = frame.xy(_point_at(motion, low_start)[:2])
        b = frame.xy(_point_at(motion, low_end)[:2])
        return _line_rect_hit(a, b, rect)
    if motion.center is None or motion.sweep is None:
        return True
    candidates = {low_start, low_end}
    steps = max(8, int(math.ceil(abs(motion.sweep) / math.radians(2.0))))
    for index in range(steps + 1):
        t = low_start + (low_end - low_start) * index / steps
        candidates.add(t)
    ordered = sorted(candidates)
    for left, right in zip(ordered, ordered[1:]):
        a = frame.xy(_point_at(motion, left)[:2])
        b = frame.xy(_point_at(motion, right)[:2])
        if _line_rect_hit(a, b, rect):
            return True
    return False


def _validate_execution(parsed: Parsed, frame: Frame, reasons: list[str]) -> bool:
    unique_tools = list(dict.fromkeys(parsed.tool_changes))
    if len(unique_tools) < 2 or frame.profile_tool not in unique_tools or frame.pocket_tool not in unique_tools:
        reasons.append("program must make M6 changes to at least two real semantic cutting tools")
        return False
    cut_tools = set()
    wcs = set()
    for motion in parsed.motions:
        if motion.code in (1, 2, 3):
            cut_tools.add(motion.tool)
            if motion.tool is None or motion.feed is None or motion.feed <= 0:
                reasons.append(f"cut lacks active tool or positive feed at line {motion.line}")
                return False
            if motion.speed is None or motion.speed <= 0 or motion.spindle not in (3, 4):
                reasons.append(f"cut lacks positive spindle state at line {motion.line}")
                return False
            if not motion.length_comp or motion.h is None or motion.h <= 0:
                reasons.append(f"cut lacks G43 with positive H at line {motion.line}")
                return False
            if motion.wcs not in {"G54", "G55", "G56", "G57", "G58", "G59"}:
                reasons.append(f"cut lacks a standard WCS at line {motion.line}")
                return False
            wcs.add(str(motion.wcs))
    if cut_tools != {frame.profile_tool, frame.pocket_tool}:
        reasons.append("unexpected cutting tool or one semantic tool has no cutting path")
        return False
    if len(wcs) != 1:
        reasons.append("program must use one standard WCS for both operations")
        return False
    return True


def _validate_tool_geometry(parsed: Parsed, frame: Frame, reasons: list[str]) -> bool:
    profile_hint = _tool_hint(parsed, frame.profile_tool)
    if profile_hint is not None and abs(profile_hint / 2.0 - frame.profile_radius) > 1.25:
        reasons.append("profile tool diameter comment conflicts with contour geometry")
        return False
    if profile_hint is not None:
        frame.profile_radius = max(frame.profile_radius, profile_hint / 2.0)
    radii = {frame.profile_tool: frame.profile_radius, frame.pocket_tool: float(frame.pocket_radius)}
    for motion in parsed.motions:
        if motion.code not in (0, 1, 2, 3) or not _xy_changed(motion):
            continue
        if motion.code == 0 and motion.home_safe and (motion.start[2] is None or motion.end[2] is None):
            continue
        if motion.tool not in radii:
            reasons.append(f"motion uses unclassified tool at line {motion.line}")
            return False
        margin = radii[motion.tool] + 4.0
        for base in FIXTURES:
            rect = (base[0] - margin, base[1] - margin, base[2] + margin, base[3] + margin)
            if _safe_segment_hit(motion, frame, rect):
                reasons.append(f"tool envelope violates fixture clearance at line {motion.line}")
                return False
    return True


def _validate_no_overcut(parsed: Parsed, frame: Frame, reasons: list[str]) -> bool:
    for motion in parsed.motions:
        if motion.code not in (1, 2, 3) or not _xy_changed(motion) or motion.tool is None:
            continue
        points = [frame.xy(point) for point in _motion_points(motion, 2.0)]
        z = float(motion.end[2]) - frame.top_z if motion.end[2] is not None else None
        if z is None:
            reasons.append(f"cut has unknown Z at line {motion.line}")
            return False
        if motion.tool == frame.pocket_tool:
            radius = float(frame.pocket_radius)
            if z < -13.8 or z > 0.5:
                reasons.append(f"pocket depth overcuts or lies above stock at line {motion.line}")
                return False
            limit_x, limit_y = 22.0 - radius + 1.0, 14.0 - radius + 1.0
            if any(abs(x) > limit_x or abs(y) > limit_y for x, y in points):
                reasons.append(f"pocket toolpath overcuts the pocket wall at line {motion.line}")
                return False
        elif motion.tool == frame.profile_tool:
            radius = frame.profile_radius
            if z < -18.8 or z > 0.5:
                reasons.append(f"profile depth overcuts or lies above stock at line {motion.line}")
                return False
            if any(not (abs(x) >= 59.0 or abs(y) >= 39.0) for x, y in points):
                reasons.append(f"profile path crosses the workpiece interior at line {motion.line}")
                return False
            if any(abs(x) > 60.0 + radius + 3.0 or abs(y) > 40.0 + radius + 3.0 for x, y in points):
                reasons.append(f"profile path is implausibly far outside the workpiece at line {motion.line}")
                return False
    return True


def validate_text_detailed(src: str) -> tuple[bool, list[str], dict[str, object]]:
    reasons: list[str] = []
    if not src.strip() or len(src.encode("utf-8", errors="ignore")) < 300:
        return False, ["empty or implausibly small NC program"], {}
    parsed = parse_nc(src)
    reasons.extend(parsed.errors)
    frame, loops = _identify_frame(parsed, reasons)
    if frame is not None:
        _identify_pocket(parsed, loops, frame, reasons)
    if frame is not None and frame.pocket_tool is not None:
        _validate_execution(parsed, frame, reasons)
        _validate_tool_geometry(parsed, frame, reasons)
        _validate_no_overcut(parsed, frame, reasons)
    metrics: dict[str, object] = {
        "motions": len(parsed.motions),
        "tool_changes": parsed.tool_changes,
        "m30_line": parsed.m30_line,
    }
    if frame is not None:
        metrics.update({
            "frame_center": [round(frame.cx, 6), round(frame.cy, 6)],
            "frame_swap": frame.swap,
            "top_z": round(frame.top_z, 6),
            "profile_tool": frame.profile_tool,
            "profile_radius": round(frame.profile_radius, 6),
            "pocket_tool": frame.pocket_tool,
            "pocket_radius": None if frame.pocket_radius is None else round(frame.pocket_radius, 6),
        })
    return not reasons, reasons, metrics


def validate_text(src: str) -> bool:
    return validate_text_detailed(src)[0]


def validate_file(path: Path) -> bool:
    try:
        return path.is_file() and validate_text(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return False


def check_no_gui_bypass(root: Path) -> bool:
    try:
        if not root.exists():
            return True
        return all(
            not (path.is_file() and path.name != "eval.py" and path.suffix.lower() in FORBIDDEN_EXTENSIONS)
            for path in root.rglob("*")
        )
    except Exception:
        return False


def evaluate() -> bool:
    return check_no_gui_bypass(TARGET) and validate_file(TARGET / OUTPUT_NAME)


if __name__ == "__main__":
    try:
        result = evaluate()
    except Exception:
        result = False
    print("True" if result else "False")
