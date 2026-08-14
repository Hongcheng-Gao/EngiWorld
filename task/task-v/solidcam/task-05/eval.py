from __future__ import annotations

import math
import os
import re
import statistics
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_TARGET = r"C:\Users\User\Desktop"
TARGET = Path(os.environ.get("EVAL_TARGET_DIR", os.environ.get("OUTPUT_ROOT", DEFAULT_TARGET)))
NC_NAME = "task-5.nc"

CENTER_TOL_MM = 0.80
SAFE_CLEARANCE_MM = 0.75
HOLE_CENTERS_MM = ((25.0, 15.0), (25.0, -15.0), (-25.0, -15.0), (-25.0, 15.0))
FORBIDDEN_EXTENSIONS = {
    ".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".ps1", ".psm1", ".vbs", ".js", ".mjs", ".ts", ".rb", ".lua",
    ".tcl", ".ahk", ".scr", ".macro", ".bas", ".vba",
}
WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))", re.IGNORECASE)
PAREN_COMMENT_RE = re.compile(r"\(([^()]*)\)")


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
    absolute: bool


@dataclass
class Program:
    code_lines: list[str] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)
    records: list[Record] = field(default_factory=list)
    tools: list[int] = field(default_factory=list)
    units_seen: set[int] = field(default_factory=set)
    distance_modes_seen: set[int] = field(default_factory=set)
    axes_seen: set[str] = field(default_factory=set)
    m30_lines: list[int] = field(default_factory=list)
    plane_xy_seen: bool = False
    length_comp_seen: bool = False


def close(a: float, b: float, tolerance: float) -> bool:
    return abs(float(a) - float(b)) <= tolerance


def split_line(raw: str) -> tuple[str, list[str]]:
    upper = raw.upper()
    comments = [item.strip() for item in PAREN_COMMENT_RE.findall(upper) if item.strip()]
    code = PAREN_COMMENT_RE.sub(" ", upper)
    if ";" in code:
        code, semicolon = code.split(";", 1)
        if semicolon.strip():
            comments.append(semicolon.strip())
    return code, comments


def parse_program(source: str) -> Program:
    program = Program()
    position: dict[str, float | None] = {"x": None, "y": None, "z": None}
    unit_scale: float | None = None
    absolute = True
    wcs: str | None = None
    pending_tool: int | None = None
    current_tool: int | None = None
    spindle_on = False
    spindle_speed: float | None = None
    feed: float | None = None
    modal_motion: int | None = None

    for line_number, raw in enumerate(source.splitlines()):
        code, comments = split_line(raw)
        program.code_lines.append(code)
        program.comments.extend(comments)
        words = [(letter.upper(), float(number)) for letter, number in WORD_RE.findall(code)]
        if not words:
            continue
        g_codes = [int(round(value)) for letter, value in words if letter == "G"]
        m_codes = [int(round(value)) for letter, value in words if letter == "M"]
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
        if 17 in g_codes:
            program.plane_xy_seen = True
        for value in g_codes:
            if 54 <= value <= 59:
                wcs = f"G{value}"
        for letter, value in words:
            if letter == "T":
                pending_tool = int(round(value))
            elif letter == "S":
                spindle_speed = value
            elif letter in {"X", "Y", "Z", "A", "B", "C", "U", "V", "W"}:
                program.axes_seen.add(letter)
        if 6 in m_codes:
            if pending_tool is None or pending_tool <= 0:
                raise ValueError("M6 without a positive tool")
            current_tool = pending_tool
            program.tools.append(current_tool)
            spindle_on = False
        if 3 in m_codes or 4 in m_codes:
            if spindle_speed is None or spindle_speed <= 0:
                raise ValueError("spindle start without a positive S value")
            spindle_on = True
        if 5 in m_codes:
            spindle_on = False
        if 30 in m_codes:
            program.m30_lines.append(line_number)
        if 43 in g_codes and any(letter == "H" and value > 0 for letter, value in words):
            program.length_comp_seen = True
        if 80 in g_codes:
            modal_motion = None
        explicit_motion = next((value for value in g_codes if value in {0, 1, 2, 3}), None)
        if explicit_motion is not None:
            modal_motion = explicit_motion
        if unit_scale is None:
            continue
        converted = {
            letter.lower(): value * unit_scale
            for letter, value in words
            if letter in {"X", "Y", "Z", "I", "J", "K", "R", "F"}
        }
        if "f" in converted:
            if converted["f"] <= 0:
                raise ValueError("non-positive feed")
            feed = converted["f"]
        machine_reference_return = 28 in g_codes
        start = dict(position)
        if not machine_reference_return:
            for axis in ("x", "y", "z"):
                if axis not in converted:
                    continue
                if absolute:
                    position[axis] = converted[axis]
                elif position[axis] is not None:
                    position[axis] += converted[axis]
        arc_with_geometry = modal_motion in {2, 3} and any(key in converted for key in ("i", "j", "r"))
        has_axis_motion = any(key in converted for key in ("x", "y", "z"))
        if machine_reference_return or current_tool is None or modal_motion is None or not (has_axis_motion or arc_with_geometry):
            continue
        program.records.append(Record(
            line=line_number,
            motion=modal_motion,
            start=start,
            end=dict(position),
            explicit=converted,
            tool=current_tool,
            wcs=wcs,
            spindle_on=spindle_on,
            feed=feed,
            absolute=absolute,
        ))
    return program


def xy_known(record: Record) -> bool:
    return None not in (record.start["x"], record.start["y"], record.end["x"], record.end["y"])


def xy_changed(record: Record, tolerance: float = 1.0e-6) -> bool:
    return xy_known(record) and (
        not close(record.start["x"], record.end["x"], tolerance)
        or not close(record.start["y"], record.end["y"], tolerance)
    )


def geometric_cut(record: Record) -> bool:
    return record.motion in {1, 2, 3} and (
        xy_changed(record) or (record.motion in {2, 3} and any(key in record.explicit for key in ("i", "j", "r")))
    )


def cutting_groups(program: Program) -> list[list[Record]]:
    groups: list[list[Record]] = []
    current: list[Record] = []
    for record in program.records:
        if geometric_cut(record):
            current.append(record)
        elif record.motion == 0 and current:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def group_level(group: list[Record]) -> float | None:
    values = [record.end["z"] for record in group if record.end["z"] is not None]
    return statistics.median(values) if values else None


def cluster_weighted(values: list[tuple[float, float]], tolerance: float = 1.25) -> list[tuple[float, float]]:
    clusters: list[list[tuple[float, float]]] = []
    for coordinate, weight in values:
        target = next((cluster for cluster in clusters if abs(coordinate - statistics.mean(item[0] for item in cluster)) <= tolerance), None)
        if target is None:
            clusters.append([(coordinate, weight)])
        else:
            target.append((coordinate, weight))
    return [
        (sum(coordinate * weight for coordinate, weight in cluster) / sum(weight for _, weight in cluster), sum(weight for _, weight in cluster))
        for cluster in clusters if sum(weight for _, weight in cluster) > 0
    ]


def rectangle_geometry(group: list[Record]) -> tuple[float, float, float, float] | None:
    horizontal: list[tuple[float, float]] = []
    vertical: list[tuple[float, float]] = []
    for record in group:
        if record.motion != 1 or not xy_known(record):
            continue
        x1, y1 = record.start["x"], record.start["y"]
        x2, y2 = record.end["x"], record.end["y"]
        dx, dy = x2 - x1, y2 - y1
        if abs(dy) <= 0.8 and abs(dx) >= 1.0:
            horizontal.append(((y1 + y2) / 2.0, abs(dx)))
        if abs(dx) <= 0.8 and abs(dy) >= 1.0:
            vertical.append(((x1 + x2) / 2.0, abs(dy)))
    horizontal_clusters = cluster_weighted(horizontal)
    vertical_clusters = cluster_weighted(vertical)
    for low_y, low_length in horizontal_clusters:
        for high_y, high_length in horizontal_clusters:
            if high_y <= low_y:
                continue
            for left_x, left_length in vertical_clusters:
                for right_x, right_length in vertical_clusters:
                    if right_x <= left_x:
                        continue
                    xspan, yspan = right_x - left_x, high_y - low_y
                    normal = 110.0 <= xspan <= 134.0 and 72.0 <= yspan <= 94.0
                    rotated = 72.0 <= xspan <= 94.0 and 110.0 <= yspan <= 134.0
                    if not (normal or rotated):
                        continue
                    cx, cy = (left_x + right_x) / 2.0, (low_y + high_y) / 2.0
                    long_lines = min(low_length, high_length)
                    short_lines = min(left_length, right_length)
                    if normal and (long_lines < 95.0 or short_lines < 60.0):
                        continue
                    if rotated and (long_lines < 60.0 or short_lines < 95.0):
                        continue
                    first, last = group[0].start, group[-1].end
                    if None in (first["x"], first["y"], last["x"], last["y"]):
                        continue
                    if math.hypot(first["x"] - last["x"], first["y"] - last["y"]) <= 10.0:
                        return cx, cy, xspan, yspan
    return None


def ij_arc(record: Record) -> tuple[float, float, float, float] | None:
    if record.motion not in {2, 3} or not xy_known(record):
        return None
    if "i" not in record.explicit or "j" not in record.explicit:
        return None
    cx = record.start["x"] + record.explicit["i"]
    cy = record.start["y"] + record.explicit["j"]
    radius = math.hypot(record.explicit["i"], record.explicit["j"])
    if radius <= 0.25:
        return None
    sx, sy = record.start["x"] - cx, record.start["y"] - cy
    ex, ey = record.end["x"] - cx, record.end["y"] - cy
    if abs(math.hypot(ex, ey) - radius) > max(0.35, 0.08 * radius):
        return None
    if math.hypot(record.start["x"] - record.end["x"], record.start["y"] - record.end["y"]) <= 1.0e-6:
        sweep = 2.0 * math.pi
    else:
        start_angle, end_angle = math.atan2(sy, sx), math.atan2(ey, ex)
        sweep = (start_angle - end_angle) % (2.0 * math.pi) if record.motion == 2 else (end_angle - start_angle) % (2.0 * math.pi)
    return cx, cy, radius, sweep


def radius_arcs(record: Record) -> list[tuple[float, float, float, float]]:
    if record.motion not in {2, 3} or not xy_known(record) or "r" not in record.explicit:
        return []
    x1, y1 = record.start["x"], record.start["y"]
    x2, y2 = record.end["x"], record.end["y"]
    signed_radius = record.explicit["r"]
    radius = abs(signed_radius)
    chord = math.hypot(x2 - x1, y2 - y1)
    if radius <= 0.25 or chord <= 1.0e-6 or chord > 2.0 * radius + 0.05:
        return []
    mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    height = math.sqrt(max(0.0, radius * radius - (chord / 2.0) ** 2))
    nx, ny = -(y2 - y1) / chord, (x2 - x1) / chord
    result = []
    for sign in (-1.0, 1.0):
        cx, cy = mx + sign * nx * height, my + sign * ny * height
        start_angle = math.atan2(y1 - cy, x1 - cx)
        end_angle = math.atan2(y2 - cy, x2 - cx)
        sweep = (start_angle - end_angle) % (2.0 * math.pi) if record.motion == 2 else (end_angle - start_angle) % (2.0 * math.pi)
        wants_major = signed_radius < 0
        if (wants_major and sweep >= math.pi - 1.0e-6) or (not wants_major and sweep <= math.pi + 1.0e-6):
            result.append((cx, cy, radius, sweep))
    return result


def arc_candidates(record: Record) -> list[tuple[float, float, float, float]]:
    ij = ij_arc(record)
    return ([ij] if ij is not None else []) + radius_arcs(record)


def arc_circle_for(group: list[Record], target: tuple[float, float]) -> bool:
    candidates = []
    for record in group:
        for cx, cy, radius, sweep in arc_candidates(record):
            if close(cx, target[0], CENTER_TOL_MM) and close(cy, target[1], CENTER_TOL_MM) and 1.5 <= radius <= 6.5:
                candidates.append((radius, sweep))
    for radius, _ in candidates:
        total = sum(sweep for other_radius, sweep in candidates if abs(other_radius - radius) <= 0.40)
        if total >= math.radians(330.0):
            return True
    return False


def segmented_circle_for(group: list[Record], target: tuple[float, float]) -> bool:
    points: list[tuple[float, float]] = []
    for record in group:
        if record.motion != 1 or not xy_known(record):
            continue
        if not points:
            points.append((record.start["x"], record.start["y"]))
        points.append((record.end["x"], record.end["y"]))
    for start_index in range(len(points)):
        for end_index in range(start_index + 8, len(points)):
            window = points[start_index:end_index + 1]
            if math.dist(window[0], window[-1]) > 0.65:
                continue
            unique = window[:-1]
            cx = statistics.mean(point[0] for point in unique)
            cy = statistics.mean(point[1] for point in unique)
            radii = [math.hypot(x - cx, y - cy) for x, y in unique]
            average = statistics.mean(radii)
            if not (1.5 <= average <= 6.5) or max(radii) - min(radii) > max(0.55, 0.18 * average):
                continue
            if not (close(cx, target[0], CENTER_TOL_MM) and close(cy, target[1], CENTER_TOL_MM)):
                continue
            angles = sorted((math.atan2(y - cy, x - cx) % (2.0 * math.pi)) for x, y in unique)
            gaps = [angles[index + 1] - angles[index] for index in range(len(angles) - 1)] + [angles[0] + 2.0 * math.pi - angles[-1]]
            if max(gaps) <= math.radians(70.0):
                return True
    return False


def hole_group_for(group: list[Record], target: tuple[float, float]) -> bool:
    return arc_circle_for(group, target) or segmented_circle_for(group, target)


def safe_separation(program: Program, ordered_groups: list[list[Record]], cut_level: float) -> bool:
    for previous, following in zip(ordered_groups, ordered_groups[1:]):
        between = [record for record in program.records if previous[-1].line < record.line < following[0].line]
        safe_xy = False
        for record in between:
            if record.motion != 0 or not xy_changed(record):
                continue
            start_z, end_z = record.start["z"], record.end["z"]
            if start_z is not None and end_z is not None and min(start_z, end_z) >= cut_level + SAFE_CLEARANCE_MM:
                safe_xy = True
        if not safe_xy:
            return False
    for record in program.records:
        if record.motion != 0 or not xy_changed(record):
            continue
        start_z, end_z = record.start["z"], record.end["z"]
        if start_z is not None and end_z is not None and min(start_z, end_z) < cut_level + SAFE_CLEARANCE_MM:
            return False
    return True


def check_no_bypass(root: Path) -> bool:
    try:
        if not root.is_dir():
            return False
        for path in root.rglob("*"):
            if path.is_file() and path.name.lower() != "eval.py" and path.suffix.lower() in FORBIDDEN_EXTENSIONS:
                return False
    except Exception:
        return False
    return True


def read_nc(path: Path) -> str | None:
    try:
        if not path.is_file() or not 500 <= path.stat().st_size <= 2_000_000:
            return None
        data = path.read_bytes()
        if b"\x00" in data:
            return None
        text = data.decode("latin-1")
        printable = sum(character in "\t\r\n" or 32 <= ord(character) <= 126 for character in text)
        return text if printable / max(1, len(text)) >= 0.98 else None
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
    if len(program.units_seen) != 1 or not program.distance_modes_seen:
        return False
    if not program.tools or not program.plane_xy_seen or not program.length_comp_seen:
        return False
    if program.axes_seen & {"A", "B", "C", "U", "V", "W"}:
        return False
    if not program.m30_lines or any(WORD_RE.search(line) for line in program.code_lines[program.m30_lines[-1] + 1:]):
        return False
    comments = " ".join(re.sub(r"[^A-Z0-9]+", " ", comment.upper()) for comment in program.comments)
    if not any(term in comments for term in ("CHAMFER", "DEBURR", "COUNTERSINK", "C SINK", "EDGE BREAK")):
        return False

    groups = cutting_groups(program)
    if len(groups) < 5:
        return False
    if any(record.wcs is None or not record.spindle_on or record.feed is None or record.feed <= 0 for group in groups for record in group):
        return False
    outer_group = next((group for group in groups if rectangle_geometry(group) is not None), None)
    if outer_group is None:
        return False
    outer_geometry = rectangle_geometry(outer_group)
    if outer_geometry is None:
        return False
    center_x, center_y, xspan, yspan = outer_geometry
    if xspan >= yspan:
        expected_holes = tuple((center_x + x, center_y + y) for x, y in HOLE_CENTERS_MM)
    else:
        expected_holes = tuple((center_x + y, center_y + x) for x, y in HOLE_CENTERS_MM)
    matched_holes: list[list[Record]] = []
    for target in expected_holes:
        matches = [group for group in groups if group is not outer_group and hole_group_for(group, target)]
        if len(matches) != 1 or matches[0] in matched_holes:
            return False
        matched_holes.append(matches[0])
    recognized = sorted([outer_group, *matched_holes], key=lambda group: group[0].line)
    levels = [group_level(group) for group in recognized]
    if any(level is None for level in levels) or max(levels) - min(levels) > 1.25:
        return False
    cut_level = statistics.median(levels)
    if not safe_separation(program, recognized, cut_level):
        return False
    return True


def evaluate() -> bool:
    return check_no_bypass(TARGET) and validate_nc(TARGET / NC_NAME)


if __name__ == "__main__":
    try:
        result = evaluate()
    except Exception:
        result = False
    print("True" if result else "False")
