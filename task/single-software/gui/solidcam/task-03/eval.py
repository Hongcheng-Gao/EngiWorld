from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_TARGET = r"C:\Users\User\Desktop"
TARGET = Path(os.environ.get("EVAL_TARGET_DIR", os.environ.get("OUTPUT_ROOT", DEFAULT_TARGET)))
NC_NAME = "task-3.nc"

EXPECTED_POINTS = ((-25.0, 15.0), (-25.0, -15.0), (25.0, -15.0), (25.0, 15.0))
POINT_TOLERANCE_MM = 0.35
SPOT_DEPTH_RANGE_MM = (0.20, 6.00)
DRILL_DEPTH_RANGE_MM = (12.75, 13.50)
MIN_SAFE_Z_MM = 1.0

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
    section: int | None
    motion: int
    start: dict[str, float | None]
    end: dict[str, float | None]
    explicit: dict[str, float]
    tool: int | None
    wcs: str | None
    spindle_on: bool
    cycle_depth: float | None = None
    cycle_r: float | None = None


@dataclass
class Program:
    source: str
    code_lines: list[str] = field(default_factory=list)
    comments: list[tuple[int, str]] = field(default_factory=list)
    records: list[Record] = field(default_factory=list)
    tool_changes: list[tuple[int, int, int]] = field(default_factory=list)
    axes_seen: set[str] = field(default_factory=set)
    units_seen: set[int] = field(default_factory=set)
    distance_modes_seen: set[int] = field(default_factory=set)
    m30_lines: list[int] = field(default_factory=list)


def close(a: float, b: float, tolerance: float = POINT_TOLERANCE_MM) -> bool:
    return abs(float(a) - float(b)) <= tolerance


def split_line(raw: str) -> tuple[str, list[str]]:
    upper = raw.upper()
    comments = [item.strip() for item in PAREN_COMMENT_RE.findall(upper) if item.strip()]
    code = PAREN_COMMENT_RE.sub(" ", upper)
    if ";" in code:
        code, semicolon_comment = code.split(";", 1)
        if semicolon_comment.strip():
            comments.append(semicolon_comment.strip())
    return code, comments


def parse_program(source: str) -> Program:
    program = Program(source=source)
    position: dict[str, float | None] = {"x": None, "y": None, "z": None}
    unit_scale: float | None = None
    absolute = True
    wcs: str | None = None
    pending_tool: int | None = None
    current_tool: int | None = None
    current_section: int | None = None
    spindle_on = False
    modal_motion: int | None = None
    active_cycle: int | None = None
    cycle_depth: float | None = None
    cycle_r: float | None = None

    for line_number, raw in enumerate(source.splitlines()):
        code, comments = split_line(raw)
        program.code_lines.append(code)
        program.comments.extend((line_number, comment) for comment in comments)
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
        for value in g_codes:
            if 54 <= value <= 59:
                wcs = f"G{value}"

        for letter, value in words:
            if letter == "T":
                pending_tool = int(round(value))
            if letter in {"X", "Y", "Z", "A", "B", "C", "U", "V", "W"}:
                program.axes_seen.add(letter)

        if 6 in m_codes:
            if pending_tool is None or pending_tool <= 0:
                raise ValueError("M6 without a valid selected tool")
            current_tool = pending_tool
            current_section = len(program.tool_changes)
            program.tool_changes.append((line_number, current_tool, current_section))
            spindle_on = False
        if 3 in m_codes or 4 in m_codes:
            spindle_on = True
        if 5 in m_codes:
            spindle_on = False
        if 30 in m_codes:
            program.m30_lines.append(line_number)

        if 80 in g_codes:
            active_cycle = None
            cycle_depth = None
            cycle_r = None
            modal_motion = None

        explicit_cycle = next((value for value in g_codes if value in {73, 81, 82, 83}), None)
        explicit_motion = next((value for value in g_codes if value in {0, 1, 2, 3}), None)
        if explicit_cycle is not None:
            active_cycle = explicit_cycle
            modal_motion = explicit_cycle
        elif explicit_motion is not None:
            modal_motion = explicit_motion
            active_cycle = None

        if unit_scale is None:
            converted = {}
        else:
            converted = {
                letter.lower(): value * unit_scale
                for letter, value in words
                if letter in {"X", "Y", "Z", "I", "J", "K", "R", "Q", "F"}
            }

        if active_cycle is not None:
            if "z" in converted:
                cycle_depth = converted["z"] if absolute else (
                    None if position["z"] is None else position["z"] + converted["z"]
                )
            if "r" in converted:
                cycle_r = converted["r"] if absolute else (
                    None if position["z"] is None else position["z"] + converted["r"]
                )

        # G28/G30 coordinates are intermediate/reference-return values, not work coordinates.
        machine_reference_return = 28 in g_codes or 30 in g_codes
        start = dict(position)
        if not machine_reference_return and unit_scale is not None:
            for axis in ("x", "y", "z"):
                if axis not in converted:
                    continue
                if absolute:
                    position[axis] = converted[axis]
                elif position[axis] is not None:
                    position[axis] = position[axis] + converted[axis]

        if machine_reference_return or current_section is None or modal_motion is None:
            continue

        is_cycle_visit = active_cycle is not None and (
            explicit_cycle is not None or "x" in converted or "y" in converted
        )
        is_regular_move = active_cycle is None and any(axis in converted for axis in ("x", "y", "z"))
        if not is_cycle_visit and not is_regular_move:
            continue
        program.records.append(
            Record(
                line=line_number,
                section=current_section,
                motion=active_cycle if active_cycle is not None else modal_motion,
                start=start,
                end=dict(position),
                explicit=converted,
                tool=current_tool,
                wcs=wcs,
                spindle_on=spindle_on,
                cycle_depth=cycle_depth if active_cycle is not None else None,
                cycle_r=cycle_r if active_cycle is not None else None,
            )
        )
    return program


def comments_by_section(program: Program) -> dict[int, list[str]]:
    assigned = {section: [] for _, _, section in program.tool_changes}
    if not program.tool_changes:
        return assigned
    for comment_line, comment in program.comments:
        nearest = min(program.tool_changes, key=lambda item: (abs(comment_line - item[0]), item[0]))
        assigned[nearest[2]].append(comment)
    return assigned


def section_line_bounds(program: Program, section: int) -> tuple[int, int]:
    start = program.tool_changes[section][0]
    end = program.tool_changes[section + 1][0] if section + 1 < len(program.tool_changes) else len(program.code_lines)
    return start, end


def section_records(program: Program, section: int) -> list[Record]:
    return [record for record in program.records if record.section == section]


def semantic_hints(comments: list[str]) -> tuple[bool, bool]:
    normalized = [re.sub(r"[^A-Z0-9]+", " ", item.upper()).strip() for item in comments]
    spot = any(
        "CENTER DRILL" in item or "CENTERDRILL" in item or "SPOT DRILL" in item or "SPOTDRILL" in item
        for item in normalized
    )
    plain_drill = any("DRILL" in item and "CENTER" not in item and "SPOT" not in item for item in normalized)
    return spot, plain_drill


def record_depth(record: Record) -> float | None:
    if record.motion in {73, 81, 82, 83}:
        return record.cycle_depth
    start_z = record.start["z"]
    end_z = record.end["z"]
    if record.motion == 1 and start_z is not None and end_z is not None and end_z < start_z - 0.10:
        return end_z
    return None


def drilling_visits(records: list[Record]) -> list[tuple[float, float, float, Record]]:
    visits = []
    for record in records:
        depth = record_depth(record)
        x, y = record.end["x"], record.end["y"]
        if depth is None or x is None or y is None:
            continue
        visits.append((x, y, depth, record))
    return visits


def consolidate_visits(visits: list[tuple[float, float, float, Record]]) -> list[tuple[float, float, float]]:
    unique: list[tuple[float, float, float]] = []
    for x, y, depth, _record in visits:
        for index, (old_x, old_y, old_depth) in enumerate(unique):
            if close(x, old_x) and close(y, old_y):
                unique[index] = (old_x, old_y, min(old_depth, depth))
                break
        else:
            unique.append((x, y, depth))
    return unique


def has_exact_hole_set(points: list[tuple[float, float, float]]) -> bool:
    if len(points) != len(EXPECTED_POINTS):
        return False
    for x, y, _depth in points:
        if not any(close(x, expected_x) and close(y, expected_y) for expected_x, expected_y in EXPECTED_POINTS):
            return False
    return all(
        any(close(x, expected_x) and close(y, expected_y) for x, y, _depth in points)
        for expected_x, expected_y in EXPECTED_POINTS
    )


def section_has_safe_motion(program: Program, section: int, visits: list[tuple[float, float, float, Record]]) -> bool:
    if not visits:
        return False
    first_line = min(item[3].line for item in visits)
    last_line = max(item[3].line for item in visits)
    records = section_records(program, section)
    unsafe_xy_traverse = any(
        record.motion in {0, 1}
        and record.start["x"] is not None
        and record.start["y"] is not None
        and record.end["x"] is not None
        and record.end["y"] is not None
        and (not close(record.start["x"], record.end["x"], 1.0e-6)
             or not close(record.start["y"], record.end["y"], 1.0e-6))
        and record.end["z"] is not None
        and record.end["z"] < MIN_SAFE_Z_MM
        for record in records
    )
    if unsafe_xy_traverse:
        return False
    safe_before = any(
        record.line < first_line
        and record.motion == 0
        and record.end["z"] is not None
        and record.end["z"] >= MIN_SAFE_Z_MM
        for record in records
    )
    cycle_safe = all(
        record.motion not in {73, 81, 82, 83}
        or (record.cycle_r is not None and record.cycle_r >= MIN_SAFE_Z_MM)
        for _x, _y, _depth, record in visits
    )
    start, end = section_line_bounds(program, section)
    tail = "\n".join(program.code_lines[max(start, last_line + 1):end])
    safe_after = (
        any(
            record.line > last_line
            and record.motion == 0
            and record.end["z"] is not None
            and record.end["z"] >= MIN_SAFE_Z_MM
            for record in records
        )
        or bool(re.search(r"\bG0*28\b[^\n]*\bZ", tail))
    )
    cycle_cancelled = not any(item[3].motion in {73, 81, 82, 83} for item in visits) or bool(
        re.search(r"\bG0*80\b", tail)
    )
    return safe_before and cycle_safe and safe_after and cycle_cancelled


def candidate_section(program: Program, section: int, kind: str, comments: dict[int, list[str]]) -> bool:
    records = section_records(program, section)
    visits = drilling_visits(records)
    points = consolidate_visits(visits)
    if not has_exact_hole_set(points):
        return False
    if any(not item[3].spindle_on or item[3].wcs is None for item in visits):
        return False
    if not section_has_safe_motion(program, section, visits):
        return False
    spot_hint, drill_hint = semantic_hints(comments.get(section, []))
    depths = [-depth for _x, _y, depth in points]
    if kind == "spot":
        if not spot_hint:
            return False
        low, high = SPOT_DEPTH_RANGE_MM
    else:
        if not drill_hint:
            return False
        low, high = DRILL_DEPTH_RANGE_MM
    return all(low <= depth <= high for depth in depths)


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
        size = path.stat().st_size
        if not path.is_file() or size < 100 or size > 2_000_000:
            return None
        data = path.read_bytes()
        if b"\x00" in data:
            return None
        text = data.decode("latin-1")
        printable = sum(character in "\t\r\n" or 32 <= ord(character) <= 126 for character in text)
        if printable / max(1, len(text)) < 0.98:
            return None
        return text
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
    if len(program.units_seen) != 1:
        return False
    if 90 not in program.distance_modes_seen:
        return False
    if len(program.tool_changes) < 2:
        return False
    if len({tool for _line, tool, _section in program.tool_changes}) < 2:
        return False
    if program.axes_seen & {"A", "B", "C", "U", "V", "W"}:
        return False
    if not program.m30_lines:
        return False
    if any(WORD_RE.search(line) for line in program.code_lines[program.m30_lines[-1] + 1:]):
        return False
    comments = comments_by_section(program)
    spot_sections = [
        section for _line, _tool, section in program.tool_changes
        if candidate_section(program, section, "spot", comments)
    ]
    drill_sections = [
        section for _line, _tool, section in program.tool_changes
        if candidate_section(program, section, "drill", comments)
    ]
    return any(
        spot_section < drill_section
        and program.tool_changes[spot_section][1] != program.tool_changes[drill_section][1]
        and program.m30_lines[-1] > program.tool_changes[drill_section][0]
        for spot_section in spot_sections
        for drill_section in drill_sections
    )


def evaluate() -> bool:
    return check_no_bypass(TARGET) and validate_nc(TARGET / NC_NAME)


if __name__ == "__main__":
    try:
        result = evaluate()
    except Exception:
        result = False
    print("True" if result else "False")
