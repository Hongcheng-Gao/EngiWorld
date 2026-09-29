from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path


TARGET = Path(os.environ.get("EVAL_TARGET_DIR", os.environ.get("OUTPUT_ROOT", r"C:\Users\User\Desktop")))
OUTPUT_NAME = "task-8.nc"
XY_TOL = 1.0
Z_TOL = 0.4

WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))", re.I)
COMMENT_RE = re.compile(r"\(([^()]*)\)")
OPERATION_RE = re.compile(
    r"^(?:CENTER\s+DRILL|DRILL|BORE|ROUGH\s+MILL|CONTOUR\s+MILL|POCKET|PROFILE)\s*\d+$",
    re.I,
)
STEPPED_OPERATION_RE = re.compile(r"^(?:BORE|ROUGH\s+MILL|CONTOUR\s+MILL|POCKET|PROFILE)\s*\d+$", re.I)


@dataclass
class Cycle:
    line: int
    code: int
    x: float
    y: float
    z: float
    r: float | None
    tool: int
    section: str


@dataclass
class Move:
    line: int
    code: int
    start: tuple[float, float, float]
    end: tuple[float, float, float]
    explicit: dict[str, float]
    tool: int
    section: str
    spindle: bool
    feed: float | None


@dataclass
class Program:
    cycles: list[Cycle] = field(default_factory=list)
    moves: list[Move] = field(default_factory=list)
    tools: list[int] = field(default_factory=list)
    sections: list[tuple[int, str]] = field(default_factory=list)
    tool_comments: dict[str, list[str]] = field(default_factory=dict)
    units: set[int] = field(default_factory=set)
    distance_modes: set[int] = field(default_factory=set)
    m_codes: set[int] = field(default_factory=set)
    axes: set[str] = field(default_factory=set)
    has_g43: bool = False
    m30_line: int | None = None
    last_word_line: int | None = None


def close(a: float, b: float, tol: float = XY_TOL) -> bool:
    return abs(float(a) - float(b)) <= tol


def point_close(a: tuple[float, float], b: tuple[float, float], tol: float = XY_TOL) -> bool:
    return math.hypot(a[0] - b[0], a[1] - b[1]) <= tol


def parse_program(source: str) -> Program:
    program = Program()
    position: dict[str, float | None] = {"x": None, "y": None, "z": None}
    unit_scale: float | None = None
    absolute = True
    current_tool: int | None = None
    pending_tool: int | None = None
    current_section = ""
    modal_motion: int | None = None
    cycle_z: float | None = None
    cycle_r: float | None = None
    spindle = False
    feed: float | None = None

    for line_number, raw in enumerate(source.splitlines()):
        comments = [comment.strip().upper() for comment in COMMENT_RE.findall(raw)]
        for comment in comments:
            if OPERATION_RE.fullmatch(comment):
                current_section = re.sub(r"\s+", " ", comment)
                program.sections.append((line_number, current_section))
                program.tool_comments.setdefault(current_section, [])
            elif current_section and comment:
                program.tool_comments.setdefault(current_section, []).append(comment)

        code = COMMENT_RE.sub(" ", raw.upper()).split(";", 1)[0]
        words = [(letter.upper(), float(number)) for letter, number in WORD_RE.findall(code)]
        if not words:
            continue
        program.last_word_line = line_number
        g_codes = [int(round(value)) for letter, value in words if letter == "G"]
        m_codes = [int(round(value)) for letter, value in words if letter == "M"]
        program.m_codes.update(m_codes)

        if 20 in g_codes:
            unit_scale = 25.4
            program.units.add(20)
        if 21 in g_codes:
            unit_scale = 1.0
            program.units.add(21)
        if 90 in g_codes:
            absolute = True
            program.distance_modes.add(90)
        if 91 in g_codes:
            absolute = False
            program.distance_modes.add(91)
        if 43 in g_codes:
            program.has_g43 = True
        if 80 in g_codes:
            modal_motion = None
            cycle_z = cycle_r = None

        for letter, value in words:
            if letter == "T":
                pending_tool = int(round(value))
            if letter in {"X", "Y", "Z", "A", "B", "C", "U", "V", "W"}:
                program.axes.add(letter)
        if 6 in m_codes:
            if pending_tool is None or pending_tool <= 0:
                raise ValueError("M6 without a positive T word")
            current_tool = pending_tool
            if current_tool not in program.tools:
                program.tools.append(current_tool)
            spindle = False
        if 3 in m_codes or 4 in m_codes:
            spindle = True
        if 5 in m_codes:
            spindle = False
        if 30 in m_codes:
            program.m30_line = line_number

        explicit_motion = next((value for value in g_codes if value in {0, 1, 2, 3, 81, 82, 83, 85, 86, 89}), None)
        if explicit_motion is not None:
            modal_motion = explicit_motion
        if unit_scale is None:
            continue
        explicit = {
            letter.lower(): value * unit_scale
            for letter, value in words
            if letter in {"X", "Y", "Z", "I", "J", "K", "R"}
        }
        feed_words = [value * unit_scale for letter, value in words if letter == "F"]
        if feed_words:
            feed = feed_words[-1]

        if modal_motion in {81, 82, 83, 85, 86, 89}:
            if "z" in explicit:
                cycle_z = explicit["z"] if absolute or position["z"] is None else position["z"] + explicit["z"]
            if "r" in explicit:
                cycle_r = explicit["r"]
            for axis in ("x", "y"):
                if axis in explicit:
                    position[axis] = explicit[axis] if absolute or position[axis] is None else position[axis] + explicit[axis]
            if current_tool is None or not current_section or None in (position["x"], position["y"], cycle_z):
                raise ValueError("incomplete canned-cycle state")
            program.cycles.append(Cycle(line_number, modal_motion, float(position["x"]), float(position["y"]), float(cycle_z), cycle_r, current_tool, current_section))
            continue

        if modal_motion not in {0, 1, 2, 3} or current_tool is None:
            continue
        if 28 in g_codes or 30 in g_codes:
            continue
        start = dict(position)
        for axis in ("x", "y", "z"):
            if axis in explicit:
                position[axis] = explicit[axis] if absolute or position[axis] is None else position[axis] + explicit[axis]
        is_arc = modal_motion in {2, 3} and ("i" in explicit or "j" in explicit)
        if not is_arc and not any(axis in explicit for axis in ("x", "y", "z")):
            continue
        if None in (start["x"], start["y"], start["z"], position["x"], position["y"], position["z"]):
            continue
        program.moves.append(
            Move(
                line_number,
                modal_motion,
                (float(start["x"]), float(start["y"]), float(start["z"])),
                (float(position["x"]), float(position["y"]), float(position["z"])),
                explicit,
                current_tool,
                current_section,
                spindle,
                feed,
            )
        )
    return program


def unique_points(points: list[tuple[float, float]], tol: float = XY_TOL) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for point in points:
        if not any(point_close(point, prior, tol) for prior in result):
            result.append(point)
    return result


def pair_distances(points: list[tuple[float, float]]) -> list[float]:
    return sorted(math.dist(a, b) for index, a in enumerate(points) for b in points[index + 1 :])


def rectangle_80_by_40(points: list[tuple[float, float]]) -> bool:
    if len(points) != 4:
        return False
    expected = [40.0, 40.0, 80.0, 80.0, math.hypot(80.0, 40.0), math.hypot(80.0, 40.0)]
    return all(close(actual, target, 1.25) for actual, target in zip(pair_distances(points), expected))


def centroid(points: list[tuple[float, float]]) -> tuple[float, float]:
    return sum(x for x, _ in points) / len(points), sum(y for _, y in points) / len(points)


def stepped_relation(through: list[tuple[float, float]], stepped: list[tuple[float, float]]) -> bool:
    if len(stepped) != 2 or not close(math.dist(*stepped), 40.0, 1.25):
        return False
    if not point_close(centroid(through), centroid(stepped), 1.25):
        return False
    expected = [40.0, 40.0, math.hypot(40.0, 40.0), math.hypot(40.0, 40.0)]
    return all(
        all(close(actual, target, 1.25) for actual, target in zip(sorted(math.dist(point, corner) for corner in through), expected))
        for point in stepped
    )


def section_cycles(program: Program, pattern: re.Pattern[str]) -> dict[str, list[Cycle]]:
    result: dict[str, list[Cycle]] = {}
    for cycle in program.cycles:
        if pattern.fullmatch(cycle.section):
            result.setdefault(cycle.section, []).append(cycle)
    return result


def arc_centers(program: Program, section: str, z: float) -> list[tuple[tuple[float, float], float]]:
    centers: list[tuple[tuple[float, float], float]] = []
    for move in program.moves:
        if move.section != section or move.code not in {2, 3} or not close(move.end[2], z, Z_TOL):
            continue
        if "i" not in move.explicit and "j" not in move.explicit:
            continue
        center = (move.start[0] + move.explicit.get("i", 0.0), move.start[1] + move.explicit.get("j", 0.0))
        radius = math.dist(move.start[:2], center)
        if radius > 0.2:
            centers.append((center, radius))
    return centers


def section_tool_diameter_hint(program: Program, section: str) -> float | None:
    text = " ".join(program.tool_comments.get(section, []))
    match = re.search(r"(?<!\d)(\d+(?:\.\d+)?)\s*MM\b", text)
    if match:
        return float(match.group(1))
    match = re.search(r"(?<!\d)(\d+(?:\.\d+)?)\s*(?:IN|INCH)\b", text)
    return float(match.group(1)) * 25.4 if match else None


def low_rapid_is_safe(program: Program) -> bool:
    for move in program.moves:
        changed_xy = not point_close(move.start[:2], move.end[:2], 1.0e-6)
        if changed_xy and move.code == 0 and min(move.start[2], move.end[2]) < 0.5:
            return False
        if changed_xy and move.code in {1, 2, 3} and (not move.spindle or move.feed is None or move.feed <= 0):
            return False
    return True


def validate_nc(path: Path) -> bool:
    try:
        if not path.is_file() or not 500 <= path.stat().st_size <= 2_000_000:
            return False
        data = path.read_bytes()
        if b"\x00" in data:
            return False
        source = data.decode("latin-1")
        if sum(char in "\t\r\n" or 32 <= ord(char) <= 126 for char in source) / len(source) < 0.98:
            return False
        program = parse_program(source)
    except Exception:
        return False

    if len(program.units) != 1 or 90 not in program.distance_modes:
        return False
    if len(program.tools) < 3 or not {3, 6, 30} <= program.m_codes or not program.has_g43:
        return False
    if program.axes & {"A", "B", "C", "U", "V", "W"}:
        return False
    if program.m30_line is None or program.last_word_line != program.m30_line:
        return False
    if not low_rapid_is_safe(program):
        return False

    center_sections = section_cycles(program, re.compile(r"CENTER\s+DRILL\s*\d+", re.I))
    spot_options: list[tuple[str, list[Cycle], list[tuple[float, float]]]] = []
    for section, cycles in center_sections.items():
        points = unique_points([(cycle.x, cycle.y) for cycle in cycles])
        if rectangle_80_by_40(points) and all(-3.0 <= cycle.z <= -0.25 for cycle in cycles):
            spot_options.append((section, cycles, points))
    if not spot_options:
        return False
    spot_section, spot_cycles, through_points = spot_options[0]

    drill_sections = section_cycles(program, re.compile(r"DRILL\s*\d+", re.I))
    through_options: list[tuple[str, list[Cycle]]] = []
    lower_options: list[tuple[str, list[Cycle]]] = []
    for section, cycles in drill_sections.items():
        points = unique_points([(cycle.x, cycle.y) for cycle in cycles])
        if rectangle_80_by_40(points) and all(cycle.z <= -18.7 for cycle in cycles):
            through_options.append((section, cycles))
        if len(points) == 2 and all(close(cycle.z, -9.0, Z_TOL) for cycle in cycles):
            lower_options.append((section, cycles))
    if not through_options or not lower_options:
        return False
    through_section, through_cycles = through_options[0]
    lower_section, lower_cycles = lower_options[0]
    through_actual = unique_points([(cycle.x, cycle.y) for cycle in through_cycles])
    stepped_points = unique_points([(cycle.x, cycle.y) for cycle in lower_cycles])
    if not all(any(point_close(point, expected) for expected in through_points) for point in through_actual):
        return False
    if not stepped_relation(through_points, stepped_points):
        return False
    if max(cycle.line for cycle in spot_cycles) >= min(cycle.line for cycle in through_cycles):
        return False

    stepped_sections = [section for _line, section in program.sections if STEPPED_OPERATION_RE.fullmatch(section)]
    upper_ok = False
    for section in stepped_sections:
        diameter = section_tool_diameter_hint(program, section)
        if diameter is not None and not 2.0 <= diameter <= 12.0:
            continue
        centers = arc_centers(program, section, -5.0)
        matched = unique_points([center for center, radius in centers if 3.5 <= radius <= 6.5])
        if len(matched) >= 2 and all(any(point_close(step, center, 1.25) for center in matched) for step in stepped_points):
            upper_ok = True
            break
        bore_cycles = [cycle for cycle in program.cycles if cycle.section == section and close(cycle.z, -5.0, Z_TOL)]
        bore_points = unique_points([(cycle.x, cycle.y) for cycle in bore_cycles])
        if len(bore_points) >= 2 and all(any(point_close(step, point) for point in bore_points) for step in stepped_points):
            upper_ok = True
            break
    if not upper_ok:
        return False

    # The output must retain native operation and tool comments rather than relying
    # on free-form labels. Each recognized operation needs a separate tool comment.
    used_sections = {spot_section, through_section, lower_section} | set(stepped_sections)
    if any(not program.tool_comments.get(section) for section in used_sections):
        return False
    return True


def evaluate() -> bool:
    return TARGET.is_dir() and validate_nc(TARGET / OUTPUT_NAME)


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print("True" if ok else "False")
