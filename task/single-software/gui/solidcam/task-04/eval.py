from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_TARGET = r"C:\Users\User\Desktop"
TARGET = Path(os.environ.get("EVAL_TARGET_DIR", os.environ.get("OUTPUT_ROOT", DEFAULT_TARGET)))
NC_NAME = "task-4.nc"

COORD_TOL_MM = 0.40
LEVEL_TOL_MM = 0.035
STOCK_TOL_MM = 0.035
MAX_STEPDOWN_MM = 2.05
SAFE_CLEARANCE_MM = 0.50
FLOOR_CANDIDATES_MM = (-10.0, 8.0)
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
    operation: str | None
    motion: int
    start: dict[str, float | None]
    end: dict[str, float | None]
    explicit: dict[str, float]
    tool: int | None
    wcs: str | None
    spindle_on: bool


@dataclass
class Program:
    code_lines: list[str] = field(default_factory=list)
    comments: list[tuple[int, str]] = field(default_factory=list)
    records: list[Record] = field(default_factory=list)
    tools: list[int] = field(default_factory=list)
    units_seen: set[int] = field(default_factory=set)
    distance_modes_seen: set[int] = field(default_factory=set)
    axes_seen: set[str] = field(default_factory=set)
    m30_lines: list[int] = field(default_factory=list)


def close(a: float, b: float, tolerance: float = COORD_TOL_MM) -> bool:
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


def operation_hint(comments: list[str]) -> str | None:
    normalized = " ".join(re.sub(r"[^A-Z0-9]+", " ", item.upper()) for item in comments)
    if "CONTOUR" in normalized or "FINISH" in normalized or "PROFILE" in normalized:
        return "finish"
    if "ROUGH" in normalized or "POCKET" in normalized or "CAVITY" in normalized:
        return "rough"
    return None


def parse_program(source: str) -> Program:
    program = Program()
    position: dict[str, float | None] = {"x": None, "y": None, "z": None}
    unit_scale: float | None = None
    absolute = True
    wcs: str | None = None
    pending_tool: int | None = None
    current_tool: int | None = None
    spindle_on = False
    modal_motion: int | None = None
    current_operation: str | None = None

    for line_number, raw in enumerate(source.splitlines()):
        code, comments = split_line(raw)
        program.code_lines.append(code)
        program.comments.extend((line_number, comment) for comment in comments)
        hint = operation_hint(comments)
        if hint is not None:
            current_operation = hint
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
                raise ValueError("M6 without a valid tool")
            current_tool = pending_tool
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
        converted = {} if unit_scale is None else {
            letter.lower(): value * unit_scale
            for letter, value in words
            if letter in {"X", "Y", "Z", "I", "J", "K", "R", "F"}
        }
        machine_reference_return = 28 in g_codes or 30 in g_codes
        start = dict(position)
        if not machine_reference_return and unit_scale is not None:
            for axis in ("x", "y", "z"):
                if axis not in converted:
                    continue
                if absolute:
                    position[axis] = converted[axis]
                elif position[axis] is not None:
                    position[axis] += converted[axis]
        if machine_reference_return or current_tool is None or modal_motion is None:
            continue
        if not any(axis in converted for axis in ("x", "y", "z")):
            continue
        program.records.append(Record(
            line=line_number,
            operation=current_operation,
            motion=modal_motion,
            start=start,
            end=dict(position),
            explicit=converted,
            tool=current_tool,
            wcs=wcs,
            spindle_on=spindle_on,
        ))
    return program


def xy_changed(record: Record) -> bool:
    start, end = record.start, record.end
    return (
        None not in (start["x"], start["y"], end["x"], end["y"])
        and (not close(start["x"], end["x"], 1.0e-6) or not close(start["y"], end["y"], 1.0e-6))
    )


def cutting_xy(program: Program, operation: str) -> list[Record]:
    return [
        record for record in program.records
        if record.operation == operation and record.motion in {1, 2, 3} and xy_changed(record)
    ]


def distinct_levels(records: list[Record]) -> list[float]:
    values: list[float] = []
    for record in records:
        value = record.end["z"]
        if value is None:
            continue
        if not any(close(value, old, LEVEL_TOL_MM) for old in values):
            values.append(value)
    return values


def bounds(records: list[Record]) -> tuple[float, float, float, float] | None:
    points = []
    for record in records:
        for point in (record.start, record.end):
            if point["x"] is not None and point["y"] is not None:
                points.append((point["x"], point["y"]))
    if not points:
        return None
    xs, ys = [point[0] for point in points], [point[1] for point in points]
    return min(xs), max(xs), min(ys), max(ys)


def adequate_centered_pocket(records: list[Record], minimum_moves: int) -> bool:
    if len(records) < minimum_moves:
        return False
    result = bounds(records)
    if result is None:
        return False
    xmin, xmax, ymin, ymax = result
    xspan, yspan = xmax - xmin, ymax - ymin
    return (
        43.5 <= xspan <= 51.0
        and 23.5 <= yspan <= 31.0
        and abs((xmin + xmax) / 2.0) <= 0.75
        and abs((ymin + ymax) / 2.0) <= 0.75
    )


def safe_traverses(program: Program, highest_cut_z: float) -> bool:
    for record in program.records:
        if record.motion != 0 or not xy_changed(record):
            continue
        start_z, end_z = record.start["z"], record.end["z"]
        if start_z is None or end_z is None:
            return False
        if min(start_z, end_z) < highest_cut_z + SAFE_CLEARANCE_MM:
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
        if not path.is_file() or not 300 <= path.stat().st_size <= 2_000_000:
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
    if len(program.units_seen) != 1 or 90 not in program.distance_modes_seen:
        return False
    if not program.tools or program.axes_seen & {"A", "B", "C", "U", "V", "W"}:
        return False
    if not program.m30_lines or any(WORD_RE.search(line) for line in program.code_lines[program.m30_lines[-1] + 1:]):
        return False

    rough = cutting_xy(program, "rough")
    finish = cutting_xy(program, "finish")
    if not rough or not finish:
        return False
    if any(not record.spindle_on or record.wcs is None for record in rough + finish):
        return False
    rough_levels = distinct_levels(rough)
    if len(rough_levels) < 5:
        return False
    if any(rough_levels[index] >= rough_levels[index - 1] - LEVEL_TOL_MM for index in range(1, len(rough_levels))):
        return False
    if any(rough_levels[index - 1] - rough_levels[index] > MAX_STEPDOWN_MM for index in range(1, len(rough_levels))):
        return False
    if not adequate_centered_pocket(rough, 20):
        return False

    floor = next((candidate for candidate in FLOOR_CANDIDATES_MM if any(close(record.end["z"], candidate, LEVEL_TOL_MM) for record in finish)), None)
    if floor is None:
        return False
    floor_finish = [record for record in finish if record.end["z"] is not None and close(record.end["z"], floor, LEVEL_TOL_MM)]
    if not adequate_centered_pocket(floor_finish, 10):
        return False
    rough_floor = min(rough_levels)
    if not close(rough_floor - floor, 0.10, STOCK_TOL_MM):
        return False
    if max(record.line for record in rough) >= min(record.line for record in floor_finish):
        return False
    highest_cut_z = max(record.end["z"] for record in rough + finish if record.end["z"] is not None)
    if not safe_traverses(program, highest_cut_z):
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
