from __future__ import annotations

import os
import re
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


def validate(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 500:
        return False
    src = path.read_text(encoding="utf-8", errors="ignore")
    _raw_lines, tools, records, flags = parse_program(src)
    if len(tools) < 2 or not all(flags.values()):
        return False

    pocket_tools = []
    for tool in tools:
        pocket_cuts = [
            record
            for record in records
            if record["tool"] == tool
            and record["code"] in {1, 2, 3}
            and xy_changed(record)
            and record["end"]["z"] is not None
        ]
        deep = [record for record in pocket_cuts if record["end"]["z"] <= -8.25]
        if len(deep) < 10:
            continue
        xs = [record["end"]["x"] for record in deep]
        ys = [record["end"]["y"] for record in deep]
        if max(xs) - min(xs) < 30.0 or max(ys) - min(ys) < 12.0:
            continue
        if any(abs(x) > 21.5 or abs(y) > 12.5 for x, y in zip(xs, ys)):
            continue
        if not all(
            any((x >= 0) == x_positive and (y >= 0) == y_positive for x, y in zip(xs, ys))
            for x_positive in (False, True)
            for y_positive in (False, True)
        ):
            continue
        minimum_z = min(record["end"]["z"] for record in pocket_cuts)
        if minimum_z < -9.75:
            continue
        pocket_tools.append(tool)
    if not pocket_tools:
        return False

    drill_records = []
    for record in records:
        if record["tool"] in pocket_tools or record["code"] not in {81, 83}:
            continue
        end = record["end"]
        if None in (end["x"], end["y"], end["z"]):
            continue
        if record["code"] == 83 and "q" in record["explicit"] and record["explicit"]["q"] <= 0:
            return False
        if end["z"] <= -16.25:
            drill_records.append(record)
    expected = [(-25.0, -15.0), (-25.0, 15.0), (25.0, -15.0), (25.0, 15.0)]
    actual = [(record["end"]["x"], record["end"]["y"]) for record in drill_records]
    if not all(any(close(x, ex) and close(y, ey) for x, y in actual) for ex, ey in expected):
        return False
    unique = []
    for point in actual:
        if not any(close(point[0], old[0]) and close(point[1], old[1]) for old in unique):
            unique.append(point)
    if len(unique) != 4:
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
