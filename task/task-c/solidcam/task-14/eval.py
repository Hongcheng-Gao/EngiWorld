from __future__ import annotations

import os
import re
import math
from pathlib import Path


TARGET = Path(os.environ.get("EVAL_TARGET_DIR", r"C:\Users\User\Desktop"))
OUTPUT = "task-14.nc"
TOL = 0.75
FORBIDDEN_EXTENSIONS = {
    ".py", ".pyw", ".ipynb", ".sh", ".bat", ".cmd", ".ps1", ".vbs",
    ".js", ".mjs", ".ts", ".rb", ".lua", ".tcl", ".ahk", ".scr",
}


def strip_comments(line: str) -> str:
    line = re.sub(r"\([^)]*\)", " ", line)
    return line.split(";", 1)[0].strip().upper()


def no_bypass_files(root: Path) -> bool:
    try:
        return not any(
            path.is_file()
            and path.name.lower() != "eval.py"
            and path.suffix.lower() in FORBIDDEN_EXTENSIONS
            for path in root.rglob("*")
        )
    except Exception:
        return False


def close(a: float, b: float, tol: float = TOL) -> bool:
    return abs(float(a) - float(b)) <= tol


def parse_program(src: str):
    raw_lines = src.upper().splitlines()
    executable = []
    for index, raw in enumerate(raw_lines):
        code = strip_comments(raw)
        if code and code != "%":
            executable.append((index, code))
    if not executable:
        raise ValueError("empty program")

    m30_positions = [pos for pos, (_, code) in enumerate(executable) if re.search(r"\bM0*30\b", code)]
    if len(m30_positions) != 1 or m30_positions[0] != len(executable) - 1:
        raise ValueError("M30 must be the final executable block")

    program_words = [int(value) for _, code in executable for value in re.findall(r"\bO0*(\d+)\b", code)]
    if program_words != [2034]:
        raise ValueError("expected exactly O2034")
    if any(re.search(r"\bG0*20\b", code) for _, code in executable):
        raise ValueError("inch mode is forbidden")
    if not any(re.search(r"\bG0*21\b", code) for _, code in executable):
        raise ValueError("metric mode is required")

    numbered = []
    for _, code in executable:
        if re.search(r"\bO0*2034\b", code) and not re.match(r"^N\d+\b", code):
            continue
        match = re.match(r"^N(\d+)\b", code)
        if match is None:
            raise ValueError("every executable block after O2034 must be numbered")
        numbered.append(int(match.group(1)))
    if len(numbered) < 30 or numbered[0] != 1:
        raise ValueError("sequence must start at N1")
    if any(right - left != 1 for left, right in zip(numbered, numbered[1:])):
        raise ValueError("sequence increment must be 1")

    state = {"x": None, "y": None, "z": None, "motion": None, "tool": None}
    pending_tool = None
    tool_order = []
    records = []
    flags = {"g90": False, "wcs": False, "g43": False, "spindle": False}
    for index, code in executable:
        tool_match = re.search(r"\bT0*(\d+)\b", code)
        if tool_match:
            pending_tool = int(tool_match.group(1))
        if re.search(r"\bM0*6\b", code):
            if pending_tool is None:
                raise ValueError("M6 without a selected tool")
            state["tool"] = pending_tool
            if pending_tool not in tool_order:
                tool_order.append(pending_tool)
        if re.search(r"\bG0*90\b", code):
            flags["g90"] = True
        if re.search(r"\bG5[4-9]\b", code):
            flags["wcs"] = True
        if re.search(r"\bG0*43\b", code) and re.search(r"\bH\d+\b", code):
            flags["g43"] = True
        if re.search(r"\bM0*[34]\b", code) and re.search(r"\bS\d+(?:\.\d+)?\b", code):
            flags["spindle"] = True

        g_codes = [int(value) for value in re.findall(r"\bG0*(\d+)\b", code)]
        if 80 in g_codes:
            state["motion"] = None
        explicit_motion = next((value for value in g_codes if value in {0, 1, 2, 3, 81, 82, 83}), None)
        if explicit_motion is not None:
            state["motion"] = explicit_motion
        explicit = {}
        for axis in "XYZQRF":
            match = re.search(rf"\b{axis}([+-]?\d+(?:\.\d+)?)", code)
            if match:
                explicit[axis.lower()] = float(match.group(1))
        if state["motion"] is None or not any(axis in explicit for axis in ("x", "y", "z")):
            continue
        start = {axis: state[axis] for axis in ("x", "y", "z")}
        for axis in ("x", "y", "z"):
            if axis in explicit:
                state[axis] = explicit[axis]
        records.append(
            {
                "index": index,
                "code": state["motion"],
                "tool": state["tool"],
                "start": start,
                "end": {axis: state[axis] for axis in ("x", "y", "z")},
                "explicit": explicit,
            }
        )
    return raw_lines, tool_order, records, flags


def xy_changed(record) -> bool:
    start, end = record["start"], record["end"]
    return (
        None not in (start["x"], start["y"], end["x"], end["y"])
        and (not close(start["x"], end["x"], 1e-6) or not close(start["y"], end["y"], 1e-6))
    )


def _unique_points(records) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for record in records:
        end = record["end"]
        if end["x"] is None or end["y"] is None:
            continue
        point = (float(end["x"]), float(end["y"]))
        if not any(close(point[0], old[0]) and close(point[1], old[1]) for old in points):
            points.append(point)
    return points


def _drill_frame(points: list[tuple[float, float]]):
    """Return the center and local long/short axes of a 50 x 30 hole rectangle."""
    if len(points) != 4:
        return None
    center = (
        sum(point[0] for point in points) / 4.0,
        sum(point[1] for point in points) / 4.0,
    )
    if any(
        not any(
            close(other[0], 2 * center[0] - point[0])
            and close(other[1], 2 * center[1] - point[1])
            for other in points
        )
        for point in points
    ):
        return None

    origin = points[0]
    vectors = []
    for point in points[1:]:
        dx, dy = point[0] - origin[0], point[1] - origin[1]
        vectors.append((math.hypot(dx, dy), dx, dy))
    vectors.sort()
    short, long, diagonal = vectors
    if not (
        close(short[0], 30.0)
        and close(long[0], 50.0)
        and close(diagonal[0], math.hypot(30.0, 50.0))
    ):
        return None
    dot = short[1] * long[1] + short[2] * long[2]
    if abs(dot) > 30.0 * 50.0 * 0.02:
        return None
    long_axis = (long[1] / long[0], long[2] / long[0])
    short_axis = (short[1] / short[0], short[2] / short[0])
    return center, long_axis, short_axis


def _project(point, center, long_axis, short_axis):
    dx, dy = point[0] - center[0], point[1] - center[1]
    return (
        dx * long_axis[0] + dy * long_axis[1],
        dx * short_axis[0] + dy * short_axis[1],
    )


def _vertical_plunge(record) -> bool:
    if record["code"] != 1:
        return False
    start, end = record["start"], record["end"]
    return (
        None not in (start["x"], start["y"], start["z"], end["x"], end["y"], end["z"])
        and close(start["x"], end["x"])
        and close(start["y"], end["y"])
        and float(end["z"]) < float(start["z"]) - 0.5
    )


def validate(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 500:
        return False
    src = path.read_text(encoding="utf-8", errors="ignore")
    _raw_lines, tools, records, flags = parse_program(src)
    if len(tools) < 2 or not all(flags.values()):
        return False

    drill_candidates = []
    for tool in tools:
        visits = [
            record
            for record in records
            if record["tool"] == tool
            and record["end"]["z"] is not None
            and (record["code"] in {81, 83} or _vertical_plunge(record))
        ]
        points = _unique_points(visits)
        frame = _drill_frame(points)
        if frame is not None:
            drill_candidates.append((min(float(record["end"]["z"]) for record in visits), tool, visits, frame))
    if not drill_candidates:
        return False
    drill_z, drill_tool, drill_records, frame = min(drill_candidates)
    center, long_axis, short_axis = frame

    pocket_tools = []
    for tool in tools:
        if tool == drill_tool:
            continue
        pocket_cuts = [
            record
            for record in records
            if record["tool"] == tool
            and record["code"] in {1, 2, 3}
            and xy_changed(record)
            and record["end"]["z"] is not None
        ]
        if not pocket_cuts:
            continue
        pocket_z = min(float(record["end"]["z"]) for record in pocket_cuts)
        deep = [record for record in pocket_cuts if close(record["end"]["z"], pocket_z)]
        if len(deep) < 10:
            continue
        projected = [
            _project(
                (float(record["end"]["x"]), float(record["end"]["y"])),
                center,
                long_axis,
                short_axis,
            )
            for record in deep
        ]
        longs = [point[0] for point in projected]
        shorts = [point[1] for point in projected]
        if max(longs) - min(longs) < 30.0 or max(shorts) - min(shorts) < 12.0:
            continue
        long_tracks = {round(value, 1) for value in longs}
        short_tracks = {round(value, 1) for value in shorts}
        if max(len(long_tracks), len(short_tracks)) < 4:
            continue
        if any(abs(long) > 21.5 or abs(short) > 12.5 for long, short in projected):
            continue
        if not all(
            any(
                (long >= 0) == long_positive and (short >= 0) == short_positive
                for long, short in projected
            )
            for long_positive in (False, True)
            for short_positive in (False, True)
        ):
            continue
        if not 6.0 <= pocket_z - drill_z <= 11.0:
            continue
        pocket_tools.append(tool)
    if not pocket_tools:
        return False
    if any(
        record["code"] == 83
        and "q" in record["explicit"]
        and record["explicit"]["q"] <= 0
        for record in drill_records
    ):
        return False
    return True


def main() -> bool:
    return no_bypass_files(TARGET) and validate(TARGET / OUTPUT)


if __name__ == "__main__":
    try:
        result = main()
    except Exception:
        result = False
    print("True" if result else "False")
