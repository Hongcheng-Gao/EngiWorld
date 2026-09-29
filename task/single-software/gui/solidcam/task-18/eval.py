from __future__ import annotations

import os
import re
from pathlib import Path


DEFAULT_TARGET = r"C:\Users\User\Desktop"
TARGET = Path(os.environ.get("EVAL_TARGET_DIR", os.environ.get("OUTPUT_ROOT", DEFAULT_TARGET)))
EXPECTED_POINTS = ((-30.0, -15.0), (-30.0, 15.0), (0.0, -15.0), (0.0, 15.0), (30.0, -15.0), (30.0, 15.0))
XY_TOL = 0.75
DEPTH_TOL = 0.75
FORBIDDEN_EXTENSIONS = {
    ".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".ps1", ".vbs", ".js", ".mjs", ".ts", ".rb", ".lua", ".tcl",
    ".ahk", ".scr",
}


def check_no_gui_bypass(root: Path) -> bool:
    try:
        if not root.exists():
            return True
        return not any(
            path.is_file() and path.name != "eval.py" and path.suffix.lower() in FORBIDDEN_EXTENSIONS
            for path in root.rglob("*")
        )
    except Exception:
        return False


def close(left: float, right: float, tolerance: float) -> bool:
    return abs(float(left) - float(right)) <= tolerance


def comments(line: str) -> list[str]:
    return [text.strip().upper() for text in re.findall(r"\(([^)]*)\)", line)]


def strip_code(line: str) -> str:
    return re.sub(r"\([^)]*\)", " ", line).split(";", 1)[0].upper()


def parse_program(source: str):
    records = []
    tool_comments: dict[int, str] = {}
    pending_comments: list[str] = []
    state = {
        "x": None,
        "y": None,
        "z": None,
        "tool": None,
        "motion": None,
        "spindle": None,
        "feed": None,
    }
    terminated = False
    clean_lines = []
    for index, raw in enumerate(source.splitlines()):
        pending_comments.extend(comments(raw))
        code = strip_code(raw)
        if not code.strip():
            continue
        clean_lines.append(code)
        if re.search(r"\bM0*30\b", code):
            terminated = True
            break
        tool_match = re.search(r"\bT0*(\d+)\b", code)
        if tool_match:
            state["tool"] = int(tool_match.group(1))
            tool_comments[state["tool"]] = " ".join(pending_comments[-3:])
            pending_comments.clear()
        spindle_match = re.search(r"\bS([+-]?\d+(?:\.\d+)?)", code)
        if spindle_match:
            state["spindle"] = float(spindle_match.group(1))
        feed_match = re.search(r"\bF([+-]?\d+(?:\.\d+)?)", code)
        if feed_match:
            state["feed"] = float(feed_match.group(1))
        g_codes = [int(value) for value in re.findall(r"\bG0*(\d+)\b", code)]
        if 80 in g_codes:
            state["motion"] = None
        explicit_motion = next((value for value in g_codes if value in {0, 1, 2, 3, 81, 82, 83, 84}), None)
        if explicit_motion is not None:
            state["motion"] = explicit_motion
        for axis in "XYZ":
            match = re.search(rf"\b{axis}([+-]?\d+(?:\.\d+)?)", code)
            if match:
                state[axis.lower()] = float(match.group(1))
        if state["motion"] in {81, 82, 83, 84} and state["x"] is not None and state["y"] is not None and state["z"] is not None:
            records.append(
                {
                    "index": index,
                    "code": state["motion"],
                    "x": state["x"],
                    "y": state["y"],
                    "z": state["z"],
                    "tool": state["tool"],
                    "spindle": state["spindle"],
                    "feed": state["feed"],
                }
            )
    return records, tool_comments, "\n".join(clean_lines), terminated


def point_matches(point, expected) -> bool:
    return close(point[0], expected[0], XY_TOL) and close(point[1], expected[1], XY_TOL)


def covers_exact_six(records) -> bool:
    points = [(record["x"], record["y"]) for record in records]
    if not all(any(point_matches(point, expected) for point in points) for expected in EXPECTED_POINTS):
        return False
    return all(any(point_matches(point, expected) for expected in EXPECTED_POINTS) for point in points)


def suitable_m8_drill(comment: str) -> bool:
    if "DRILL" not in comment or "SPOT" in comment or "CENTER" in comment:
        return False
    diameters = [float(value) for value in re.findall(r"(?<!\d)(\d+(?:\.\d+)?)\s*MM\b", comment)]
    return any(6.5 <= diameter <= 7.0 for diameter in diameters)


def suitable_m8_tap(comment: str) -> bool:
    if "TAP" not in comment:
        return False
    return bool(
        re.search(r"\bM\s*8(?:\.0+)?\b", comment)
        or re.search(r"\b8(?:\.0+)?\s*(?:MM\b|[Xx])", comment)
    )


def tapping_feed_is_plausible(records) -> bool:
    for record in records:
        feed = record["feed"]
        spindle = record["spindle"]
        if feed is None:
            continue
        if 0.7 <= feed <= 1.5:
            return True
        if spindle and spindle > 0 and 0.7 <= feed / spindle <= 1.5:
            return True
    return False


def validate_file(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 300:
        return False
    source = path.read_text(encoding="utf-8", errors="ignore").upper()
    records, tool_comments, clean_program, terminated = parse_program(source)
    if not terminated or "G21" not in clean_program or "G90" not in clean_program:
        return False
    if re.search(r"\b[ABC][+-]?\d", clean_program):
        return False
    if re.search(r"\bG0*[23]\b", clean_program):
        return False

    pilot_tools = {
        tool
        for tool, comment in tool_comments.items()
        if suitable_m8_drill(comment)
    }
    tap_tools = {
        tool
        for tool, comment in tool_comments.items()
        if suitable_m8_tap(comment)
    }
    if not pilot_tools or not tap_tools or pilot_tools & tap_tools:
        return False

    pilot_ok = False
    for tool in pilot_tools:
        pilot = [
            record for record in records
            if record["tool"] == tool and record["code"] in {81, 83} and record["z"] <= -18.0 + DEPTH_TOL
        ]
        if covers_exact_six(pilot):
            pilot_ok = True
            break
    if not pilot_ok:
        return False

    tap_ok = False
    for tool in tap_tools:
        tapped = [
            record for record in records
            if record["tool"] == tool and record["code"] == 84 and close(record["z"], -18.0, DEPTH_TOL)
        ]
        if covers_exact_six(tapped) and tapping_feed_is_plausible(tapped):
            tap_ok = True
            break
    return tap_ok


def evaluate() -> bool:
    return check_no_gui_bypass(TARGET) and validate_file(TARGET / "task-18.nc")


if __name__ == "__main__":
    try:
        result = evaluate()
    except Exception:
        result = False
    print("True" if result else "False")
